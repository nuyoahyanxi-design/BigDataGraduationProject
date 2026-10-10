"""Real API/JDBC/Parquet verification without business batch publication."""
import hashlib
import json
import os
import re
import secrets
import time
from pathlib import Path
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, delete
from pyspark.sql import functions as F

from app.main import app
from app.models import (User, Resource, CourseChapter, ChapterProgress,
                        ChapterEvent, LearningProgress, LearningEvent, Favorite)
from spark.jobs import extract as extract_job, clean as clean_job
from spark.utils import cleaning
from spark.utils.profiles import compute_profiles, canonical
from spark.utils.recommendations import compute_recommendations
from spark.utils.session import build_spark
from spark.utils.files import write_json
from conftest import persistent_summary, PROJECT_ROOT


def protection_summary():
    summary=persistent_summary()
    with app.state.session_factory() as db:
        chapters=db.scalars(select(CourseChapter).order_by(CourseChapter.id)).all()
        rows=[{col.name:getattr(row,col.name) for col in CourseChapter.__table__.columns} for row in chapters]
        summary['course_chapters_sha256']=hashlib.sha256(json.dumps(rows,default=str,sort_keys=True).encode()).hexdigest()
        # Schema hashes only: never read passwords or AI message bodies.
        from sqlalchemy import text
        names=db.execute(text('SHOW TABLES')).scalars().all()
        summary['schema']={name:hashlib.sha256(re.sub(r' AUTO_INCREMENT=\d+', '',
            str(db.execute(text('SHOW CREATE TABLE `'+name+'`')).first()[1])).encode()).hexdigest() for name in names}
    return summary


def test_real_chapter_events_to_isolated_ods_dwd_ads(monkeypatch, isolated_spark_workspace):
    evidence=PROJECT_ROOT/'outputs/learning-behavior-stability'/('isolated-'+uuid4().hex[:12])
    evidence.mkdir(parents=True)
    root=evidence/'workspace'
    ids=[];rids=[];snapshots=[];spark=None
    os.environ.setdefault('JWT_SECRET',secrets.token_urlsafe(48))
    password=secrets.token_urlsafe(24)
    prefix='uuidfix_'+secrets.token_hex(5)
    with TestClient(app) as client:
        before=protection_summary()
        try:
            headers=[]
            for suffix in ['admin','learner','observer']:
                response=client.post('/api/auth/register',json={'username':prefix+suffix,'password':password})
                assert response.status_code==201
                ids.append(response.json()['id'])
            with app.state.session_factory() as db:
                db.get(User,ids[0]).role='admin';db.commit()
            for suffix in ['admin','learner','observer']:
                response=client.post('/api/auth/login',json={'username':prefix+suffix,'password':password})
                assert response.status_code==200
                headers.append({'Authorization':'Bearer '+response.json()['access_token']})
            for title,tags in [('bridge-course',['spark']),('other-course',['python'])]:
                response=client.post('/api/resources',headers=headers[0],json={
                    'title':prefix+title,'summary':'Isolated UUID compatibility verification',
                    'resource_type':'course','category_code':'data-engineering','tags':tags,'content':'Test teaching material',
                    'source_name':'Isolated stability verification','license_note':'Self-authored test material'})
                assert response.status_code==201
                rid=response.json()['id'];rids.append(rid)
                assert client.patch(f'/api/resources/{rid}/status',headers=headers[0],json={'status':'published'}).status_code==200
            chapters=[]
            for position in [1,2]:
                response=client.post(f'/api/resources/{rids[0]}/chapters',headers=headers[0],json={
                    'title':f'Chapter {position}','position':position,'content':'Spark learning', 'knowledge_tags':['Spark']})
                assert response.status_code==201;chapters.append(response.json()['id'])
            spark=build_spark('isolated-course-uuid-stability')
            monkeypatch.setattr(extract_job,'ROOT',root)
            monkeypatch.setattr(clean_job,'ROOT',root)

            def act(chapter,kind):
                source=str(uuid4())
                payload={'event_uuid':source,'event_type':kind}
                url=f'/api/resources/{rids[0]}/chapters/{chapter}/events'
                first=client.post(url,headers=headers[1],json=payload)
                assert first.status_code==200
                assert client.post(url,headers=headers[1],json=payload).json()==first.json()
                return source

            def snapshot(stage,expected_start,expected_complete,expected_heat):
                # MySQL and API clocks can differ slightly. Wait for a valid
                # cutoff instead of weakening production future-time validation.
                from sqlalchemy import text, func
                with app.state.session_factory() as db:
                    latest_event=db.scalar(select(func.max(LearningEvent.occurred_at)).where(LearningEvent.user_id.in_(ids)))
                deadline=time.monotonic()+15
                while True:
                    with app.state.engine.connect() as connection:
                        database_now=connection.execute(text('SELECT UTC_TIMESTAMP(3)')).scalar_one()
                    if database_now>=latest_event:break
                    assert time.monotonic()<deadline,'Database/API clock skew exceeds isolated test allowance'
                    time.sleep(0.1)
                batch,manifest=extract_job.extract(spark)
                report=clean_job.clean(spark,batch)
                ods=root/'data/ods'/('batch_id='+batch)
                dwd=root/'data/dwd'/('batch_id='+batch)
                users=spark.read.parquet(str(ods/'users')).filter(F.col('id').isin(ids))
                resources=spark.read.parquet(str(ods/'resources')).filter(F.col('id').isin(rids))
                events=spark.read.parquet(str(dwd/'learning_events')).filter(F.col('user_id').isin(ids))
                raw=spark.read.parquet(str(ods/'learning_events')).filter(F.col('user_id').isin(ids))
                progress=spark.read.parquet(str(ods/'learning_progress')).filter(F.col('user_id').isin(ids))
                expected_count=expected_start+expected_complete
                assert raw.count()==events.count()==expected_count
                assert all(UUID(row.event_uuid).version==5 for row in raw.select('event_uuid').collect())
                rejected=spark.read.parquet(str(dwd/'learning_events_rejected')).filter(F.col('user_id').isin(ids))
                assert rejected.count()==0
                # Exercise the old v4-only boundary on exactly the same immutable input.
                with monkeypatch.context() as old:
                    old.setattr(cleaning,'BRIDGE_UUID_PATTERN',r'(?!)')
                    old_events,old_rejected,old_report=cleaning.clean_events(raw,users,resources,manifest['snapshot_at'])
                try:
                    assert old_events.count()==0
                    assert old_report['primary_reasons']=={'invalid_event_uuid':expected_count}
                    old_profiles=compute_profiles(spark,old_events,users,resources,manifest['snapshot_at'])
                    old_learner=next(row for row in old_profiles if row['user_id']==ids[1])
                    assert old_learner['learning_preference']['started_resources']==0
                    assert old_learner['learning_preference']['completed_resources']==0
                    assert old_learner['interest_profile']['evidence']=='no_evidence'
                    old_frame=spark.createDataFrame([(p['user_id'],canonical(p['interest_profile'])) for p in old_profiles],
                        'user_id long,interest_profile string')
                    old_parameters=json.loads((PROJECT_ROOT/'spark/configs/recommendation.json').read_text())
                    old_recommendations,_=compute_recommendations(old_frame,users,resources,old_events,progress,
                        manifest['snapshot_at'],old_parameters)
                    assert all(float(row['score'])==0 for row in old_recommendations)
                finally:
                    old_events.unpersist();old_rejected.unpersist()
                profiles=compute_profiles(spark,events,users,resources,manifest['snapshot_at'])
                learner=next(row for row in profiles if row['user_id']==ids[1])
                assert learner['activity_profile']['event_counts']['learning_start']==expected_start
                assert learner['activity_profile']['event_counts']['learning_complete']==expected_complete
                assert learner['learning_preference']['started_resources']==1
                assert learner['learning_preference']['completed_resources']==expected_complete
                assert learner['learning_preference']['completion_rate']==float(expected_complete)
                assert learner['interest_profile']['weights']=={'spark':1.0}
                frame=spark.createDataFrame([(p['user_id'],canonical(p['interest_profile']),canonical(p['activity_profile']),
                    canonical(p['learning_preference'])) for p in profiles],
                    'user_id long,interest_profile string,activity_profile string,learning_preference string')
                parameters=json.loads((PROJECT_ROOT/'spark/configs/recommendation.json').read_text())
                recommendations,counts=compute_recommendations(frame,users,resources,events,progress,manifest['snapshot_at'],parameters)
                popular=next(row for row in recommendations if row['user_id']==ids[2] and row['algorithm']=='popular_v1' and row['resource_id']==rids[0])
                assert float(popular['score'])==expected_heat
                personal=[row for row in recommendations if row['user_id']==ids[1] and row['resource_id']==rids[0]]
                if expected_complete:
                    assert personal==[]
                else:
                    assert float(next(row for row in personal if row['algorithm']=='content_v1')['score'])==1.0
                ads=root/'data/ads'/stage
                frame.write.parquet(str(ads/'profiles'))
                rec_frame=spark.createDataFrame([(r['user_id'],r['resource_id'],r['algorithm'],r['score'],r['rank'],r['reason']) for r in recommendations],
                    'user_id long,resource_id long,algorithm string,score string,rank int,reason string')
                rec_frame.write.parquet(str(ads/'recommendations'))
                for actual,path in [(frame,ads/'profiles'),(rec_frame,ads/'recommendations')]:
                    reread=spark.read.parquet(str(path))
                    assert actual.count()==reread.count()
                    assert actual.exceptAll(reread).count()==reread.exceptAll(actual).count()==0
                snapshots.append({'stage':stage,'batch_id':batch,'cutoff':manifest['snapshot_at'],
                    'database_clock_before_extract':str(database_now),'latest_fixture_event_time':str(latest_event),
                    'isolated_ods_events':raw.count(),'old_dwd_events':0,'new_dwd_events':events.count(),
                    'old_rejections':old_report['primary_reasons'],'isolated_new_rejections':0,
                    'profile':learner,'observer_popularity':popular['score'],'recommendations':recommendations,
                    'old_profile':old_learner,'old_recommendations':old_recommendations,
                    'full_readonly_snapshot_quality':report,'ads_round_trip':'passed','counts':counts})

            start=act(chapters[0],'chapter_view')
            snapshot('started',1,0,2)
            act(chapters[0],'chapter_complete')
            snapshot('partial',1,0,2)
            act(chapters[1],'chapter_view')
            complete=act(chapters[1],'chapter_complete')
            snapshot('completed',1,1,5)
            with app.state.session_factory() as db:
                rows=db.scalars(select(LearningEvent).where(LearningEvent.user_id==ids[1],LearningEvent.resource_id==rids[0])).all()
                assert len(rows)==2
                assert {row.event_type:row.event_uuid for row in rows}=={
                    kind:str(uuid5(NAMESPACE_URL,f'course:{source}:{kind}'))
                    for kind,source in [('learning_start',start),('learning_complete',complete)]}
            write_json(evidence/'chain-evidence.json',{'status':'passed','transport':'FastAPI TestClient, real MySQL and Spark JDBC',
                'formal_publication_performed':False,'snapshots':snapshots})
        finally:
            if spark is not None:spark.stop()
            with app.state.session_factory() as db:
                for model in [ChapterEvent,ChapterProgress,LearningEvent,Favorite,LearningProgress]:
                    if ids:db.execute(delete(model).where(model.user_id.in_(ids)))
                if rids:
                    db.execute(delete(CourseChapter).where(CourseChapter.resource_id.in_(rids)))
                    db.execute(delete(Resource).where(Resource.id.in_(rids)))
                if ids:db.execute(delete(User).where(User.id.in_(ids)))
                db.commit()
            after=protection_summary()
            write_json(evidence/'protection.json',{'status':'passed' if before==after else 'failed',
                'before':before,'after':after,'only_exact_fixture_ids_cleaned':True,
                'auto_increment_may_advance':True,'formal_publication_performed':False})
            assert before==after,'Persistent rows, schema, historical artifacts or pointers changed'


def test_existing_bridge_uuid_readonly_audit():
    os.environ.setdefault('JWT_SECRET',secrets.token_urlsafe(48))
    with TestClient(app):
        before=protection_summary()
        with app.state.session_factory() as db:
            legacy=db.scalars(select(LearningEvent)).all()
            chapter_events=db.scalars(select(ChapterEvent)).all()
            bridge_ids={str(uuid5(NAMESPACE_URL,f'course:{row.event_uuid}:{kind}')):
                        (row.user_id,row.resource_id,kind)
                        for row in chapter_events for kind in ['learning_start','learning_complete']}
            v5=[row for row in legacy if UUID(row.event_uuid).version==5]
            matched=sum(bridge_ids.get(row.event_uuid)==(row.user_id,row.resource_id,row.event_type) for row in v5)
            assert matched==len(v5)
            write_json(PROJECT_ROOT/'outputs/learning-behavior-stability/historical-uuid-audit.json',
                {'read_only':True,'v5_events':len(v5),'matched_existing_chapter_derivations':matched,'unmatched':len(v5)-matched})
        assert protection_summary()==before
