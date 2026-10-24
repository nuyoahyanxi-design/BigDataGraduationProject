"""Isolated SQLite/Spark fixtures; no production completion events."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4
import pytest
from sqlalchemy import create_engine,text,select
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models import LearningProgress
from app.services.course_presentation import effective_progress_status,effective_progress_time,chapter_status
from app.services.learning import _perform
from spark.utils.session import build_spark
from spark.utils.progress import derive_progress

def test_online_status_and_timestamps():
    engine=create_engine('sqlite://')
    with engine.begin() as c:
        c.execute(text('CREATE TABLE learning_progress(user_id INTEGER,resource_id INTEGER,status TEXT,first_started_at DATETIME,completed_at DATETIME,updated_at DATETIME)'))
        c.execute(text('CREATE TABLE course_chapters(id INTEGER,resource_id INTEGER)'))
        c.execute(text('CREATE TABLE chapter_progress(user_id INTEGER,chapter_id INTEGER,first_started_at DATETIME,completed_at DATETIME)'))
        for r in [10,20,30,40]:c.execute(text("INSERT INTO learning_progress VALUES(1,:r,'completed','2026-01-01','2026-01-01','2026-01-01')"),{'r':r})
        c.execute(text('INSERT INTO course_chapters VALUES(1,10),(2,10),(3,20),(4,30)'))
        c.execute(text("INSERT INTO chapter_progress VALUES(1,1,'2026-01-02',NULL),(1,3,'2026-01-02','2026-01-03')"))
    with Session(engine) as db:
        rows=db.execute(select(LearningProgress.resource_id,effective_progress_status(1),effective_progress_time(1,'completed_at'))).all()
        states={r:(s,t) for r,s,t in rows}
        assert states[10]==('in_progress',None)
        assert states[20][0]=='completed' and str(states[20][1]).startswith('2026-01-03')
        assert states[30]==('not_started',None)
        assert states[40][0]=='completed'
        assert db.execute(text('SELECT status FROM learning_progress WHERE resource_id=10')).scalar_one()=='completed'
    assert chapter_status(0,5,4)=='in_progress' and chapter_status(0,5,0)=='not_started'

def test_legacy_completed_cannot_bypass_chapters():
    db=MagicMock()
    db.scalar.side_effect=[SimpleNamespace(status='active'),None,SimpleNamespace(id=10,status='published'),5,0]
    db.get.return_value=SimpleNamespace(status='completed',updated_at=datetime(2026,1,1))
    with pytest.raises(HTTPException) as err:
        _perform(db,1,10,'learning_complete',SimpleNamespace(event_uuid=uuid4()),datetime(2026,1,2),'test')
    assert err.value.status_code==409
    db.commit.assert_not_called()

@pytest.fixture(scope='module')
def spark():
    session=build_spark('unified-progress-test')
    yield session
    session.stop()

def frames(s):
    p=s.createDataFrame([(1,r,'completed','2026-01-01','2026-01-01','2026-01-01') for r in [10,20,30,40]],'user_id long,resource_id long,status string,first_started_at string,completed_at string,updated_at string')
    ch=s.createDataFrame([(1,10),(2,10),(3,20),(4,30)],'id long,resource_id long')
    cp=s.createDataFrame([(1,1,'2026-01-02',None),(1,3,'2026-01-02','2026-01-03')],'user_id long,chapter_id long,first_started_at string,completed_at string')
    users=s.createDataFrame([(1,)],'id long')
    return p,ch,cp,users

def test_snapshot_progress_matches_online(spark):
    p,ch,cp,u=frames(spark)
    canonical=derive_progress(p,ch,cp,u,'2026-01-04')
    result={r.resource_id:r for r in canonical.collect()}
    assert result[10].status=='in_progress' and result[10].completed_at is None
    assert result[20].status=='completed'
    assert result[30].status=='not_started' and result[30].first_started_at is None
    assert result[40].status=='completed'
    assert p.filter("status='completed'").count()==4
    # Historical completions remain countable, but must not exclude unfinished courses.
    import json
    from spark.utils.profiles import compute_profiles
    from spark.utils.recommendations import compute_recommendations
    users=spark.createDataFrame([(1,'learner','active','[]')],'id long,role string,status string,interest_tags string')
    resources=spark.createDataFrame([(r,'course','published','["spark"]') for r in [10,20,30,40]],'id long,resource_type string,status string,tags string')
    events=spark.createDataFrame([(i*2+j,1,r,kind,'2026-01-01',1) for i,r in enumerate([10,20,30,40]) for j,kind in enumerate(['learning_start','learning_complete'])],'id long,user_id long,resource_id long,event_type string,occurred_at string,is_effective int')
    profiles=compute_profiles(spark,events,users,resources,'2026-01-04',effective_progress=canonical)
    assert profiles[0]['activity_profile']['event_counts']['learning_complete']==4
    assert profiles[0]['learning_preference']['started_resources']==3
    assert profiles[0]['learning_preference']['completed_resources']==2
    ps=spark.createDataFrame([(1,json.dumps(profiles[0]['interest_profile']))],'user_id long,interest_profile string')
    params=dict(version='v1',top_n=5,weights=dict(view=1,start=2,complete=3,favorite=2),business_timezone='Asia/Shanghai',max_candidate_pairs=100,max_output_rows=100)
    rows,_=compute_recommendations(ps,users,resources,events,canonical,'2026-01-04',params,progress_is_canonical=True)
    for algorithm in ['popular_v1','content_v1']:
        assert {r['resource_id'] for r in rows if r['algorithm']==algorithm}=={10,30}

def test_snapshot_rejects_invalid_chapter_progress(spark):
    from pyspark.sql import functions as F
    p,ch,cp,u=frames(spark)
    with pytest.raises(RuntimeError,match='timeline'):
        derive_progress(p,ch,cp.withColumn('completed_at',F.lit('bad-date')),u,'2026-01-04')
    with pytest.raises(RuntimeError,match='Orphan'):
        derive_progress(p,ch,cp.withColumn('chapter_id',F.lit(999)),u,'2026-01-04')
