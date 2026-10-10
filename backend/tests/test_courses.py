import secrets
from uuid import uuid4, uuid5, UUID, NAMESPACE_URL
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,delete,func
from app.main import app
from app.models import User,Resource,LearningProgress,LearningEvent,CourseChapter,ChapterProgress,ChapterEvent
from app.services import courses
from conftest import SafeTestContext

@pytest.fixture(scope='module')
def ctx():
    ids=[];rids=[];prefix='ch_'+secrets.token_hex(6);password=secrets.token_urlsafe(24)
    models=(User,Resource,LearningProgress,LearningEvent,CourseChapter,ChapterProgress,ChapterEvent)
    with TestClient(app) as client:
        with app.state.session_factory() as db:
            before={m.__tablename__:db.scalar(select(func.count()).select_from(m)) for m in models}
        try:
            headers=[]
            for suffix in ('admin','learner','other'):
                response=client.post('/api/auth/register',json={'username':prefix+suffix,'password':password})
                assert response.status_code==201;ids.append(response.json()['id'])
            with app.state.session_factory() as db:db.get(User,ids[0]).role='admin';db.commit()
            for suffix in ('admin','learner','other'):
                response=client.post('/api/auth/login',json={'username':prefix+suffix,'password':password})
                headers.append({'Authorization':'Bearer '+response.json()['access_token']})
            yield SafeTestContext(client=client,ids=ids,rids=rids,admin=headers[0],learner=headers[1],other=headers[2])
        finally:
            with app.state.session_factory() as db:
                for model in (ChapterEvent,ChapterProgress,LearningEvent,LearningProgress):db.execute(delete(model).where(model.user_id.in_(ids)))
                db.execute(delete(CourseChapter).where(CourseChapter.resource_id.in_(rids)))
                db.execute(delete(Resource).where(Resource.id.in_(rids)))
                db.execute(delete(User).where(User.id.in_(ids)));db.commit()
                after={m.__tablename__:db.scalar(select(func.count()).select_from(m)) for m in models}
                assert after==before
                (Path(__file__).resolve().parents[2]/'outputs/course-learning-test-cleanup.json').write_text(json.dumps({'before':before,'after':after,'only_isolated_fixture_cleanup':True}),encoding='utf-8')

def chapter(position=1):return {'title':'章节'+str(position),'position':position,'content':'# RDD\n安全学习内容','knowledge_tags':['Spark','RDD'],'video_url':'/videos/demo.mp4'}
def setup(ctx,count=2):
    c=ctx['client'];r=c.post('/api/resources',headers=ctx['admin'],json={'title':'课程验收','summary':'章节测试','resource_type':'course','category_code':'data-engineering','tags':['spark'],'content':'课程'})
    assert r.status_code==201;rid=r.json()['id'];ctx['rids'].append(rid)
    assert c.patch(f'/api/resources/{rid}/status',headers=ctx['admin'],json={'status':'published'}).status_code==200
    chapters=[]
    for i in range(count):
        response=c.post(f'/api/resources/{rid}/chapters',headers=ctx['admin'],json=chapter(i+1))
        assert response.status_code==201;chapters.append(response.json()['id'])
    return rid,chapters
def action(ctx,rid,cid,kind='chapter_view',uuid=None,actor='learner',**extra):
    return ctx['client'].post(f'/api/resources/{rid}/chapters/{cid}/events',headers=ctx[actor],json={'event_uuid':uuid or str(uuid4()),'event_type':kind,**extra})
def snapshot(ctx,rid):
    with app.state.session_factory() as db:
        progress=db.get(LearningProgress,(ctx['ids'][1],rid))
        return {'status':progress.status if progress else None,
            'legacy':db.scalar(select(func.count()).select_from(LearningEvent).where(LearningEvent.resource_id==rid)),
            'chapter_events':db.scalar(select(func.count()).select_from(ChapterEvent).where(ChapterEvent.resource_id==rid)),
            'completed':db.scalar(select(func.count()).select_from(ChapterProgress).join(CourseChapter).where(CourseChapter.resource_id==rid,ChapterProgress.completed_at.is_not(None)))}

def test_full_chapter_flow_and_legacy_bridge(ctx):
    rid,cids=setup(ctx)
    assert ctx['client'].get(f'/api/resources/{rid}/course',headers=ctx['learner']).json()['course_status']=='not_started'
    assert action(ctx,rid,cids[0]).json()['course_status']=='not_started'
    assert action(ctx,rid,cids[0],'video_play',playback_seconds=1.25).status_code==200
    assert action(ctx,rid,cids[0],'chapter_complete').json()['course_status']=='in_progress'
    assert action(ctx,rid,cids[1]).status_code==200
    assert action(ctx,rid,cids[1],'chapter_complete').json()['course_status']=='completed'
    assert snapshot(ctx,rid)=={'status':'completed','legacy':2,'chapter_events':5,'completed':2}
    with app.state.session_factory() as db:
        assert set(db.scalars(select(LearningEvent.event_type).where(LearningEvent.resource_id==rid)))=={'learning_start','learning_complete'}
    history=ctx['client'].get('/api/users/me/chapter-events',headers=ctx['learner']).json()
    assert any(e['chapter_id']==cids[0] and e['playback_seconds']==1.25 for e in history['items'])
    other=ctx['client'].get('/api/users/me/chapter-events',headers=ctx['other']).json()
    assert not any(e['resource_id']==rid for e in other['items'])

def test_uuid_replay_and_conflict(ctx):
    rid,cids=setup(ctx);uuid=str(uuid4())
    original=action(ctx,rid,cids[0],uuid=uuid).json()
    action(ctx,rid,cids[0],'chapter_complete')
    assert action(ctx,rid,cids[0],uuid=uuid).json()==original
    assert action(ctx,rid,cids[1],uuid=uuid).status_code==409
    assert action(ctx,rid,cids[0],uuid=uuid,actor='other').status_code==409


def test_bridge_uuid_identity_and_client_v4_boundary(ctx):
    rid,cids=setup(ctx,1)
    start_uuid,complete_uuid=str(uuid4()),str(uuid4())
    first=action(ctx,rid,cids[0],uuid=start_uuid)
    assert first.status_code==200
    last=action(ctx,rid,cids[0],'chapter_complete',uuid=complete_uuid)
    assert last.status_code==200
    assert action(ctx,rid,cids[0],uuid=start_uuid).json()==first.json()
    assert action(ctx,rid,cids[0],'chapter_complete',uuid=complete_uuid).json()==last.json()
    with app.state.session_factory() as db:
        rows=db.scalars(select(LearningEvent).where(LearningEvent.resource_id==rid)).all()
        actual={row.event_type:row.event_uuid for row in rows}
    assert len(rows)==2
    assert actual=={kind:str(uuid5(NAMESPACE_URL,f'course:{source}:{kind}'))
                   for kind,source in [('learning_start',start_uuid),('learning_complete',complete_uuid)]}
    assert all(UUID(value).version==5 for value in actual.values())
    assert len(set(actual.values()))==2
    assert action(ctx,rid,cids[0],uuid=str(uuid5(NAMESPACE_URL,'client'))).status_code==422

def test_completion_noop_and_legacy_bypass_rejected(ctx):
    rid,cids=setup(ctx)
    action(ctx,rid,cids[0]);action(ctx,rid,cids[0],'chapter_complete')
    assert action(ctx,rid,cids[0],'chapter_complete').json()['is_effective']==0
    response=ctx['client'].post(f'/api/resources/{rid}/complete',headers=ctx['learner'],json={'event_uuid':str(uuid4())})
    assert response.status_code==409 and snapshot(ctx,rid)['status']=='in_progress'

def test_last_chapter_transaction_rolls_back(ctx,monkeypatch):
    rid,cids=setup(ctx,1);action(ctx,rid,cids[0]);before=snapshot(ctx,rid)
    def fail(*args,**kwargs):raise RuntimeError('injected failure')
    with monkeypatch.context() as patch:
        patch.setattr(courses.learning,'_append_event',fail)
        with pytest.raises(RuntimeError):action(ctx,rid,cids[0],'chapter_complete')
    assert snapshot(ctx,rid)==before
    assert action(ctx,rid,cids[0],'chapter_complete').json()['course_status']=='completed'

def test_chapter_event_failure_rolls_back_start(ctx,monkeypatch):
    rid,cids=setup(ctx,1);before=snapshot(ctx,rid)
    def fail(*args,**kwargs):raise RuntimeError('injected event failure')
    with monkeypatch.context() as patch:
        patch.setattr(courses,'append_chapter_event',fail)
        with pytest.raises(RuntimeError):action(ctx,rid,cids[0])
    assert snapshot(ctx,rid)==before

def test_parallel_last_chapters_complete_once(ctx):
    rid,cids=setup(ctx)
    for cid in cids:action(ctx,rid,cid)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results=list(executor.map(lambda cid:action(ctx,rid,cid,'chapter_complete'),cids))
    assert all(r.status_code==200 for r in results)
    assert snapshot(ctx,rid)['legacy']==2 and snapshot(ctx,rid)['status']=='completed'

def test_permissions_ownership_and_offline(ctx):
    rid,cids=setup(ctx,1);other_rid,_=setup(ctx,0)
    assert ctx['client'].get(f'/api/resources/{rid}/course').status_code==401
    assert ctx['client'].post(f'/api/resources/{rid}/chapters',headers=ctx['learner'],json=chapter(2)).status_code==403
    assert action(ctx,other_rid,cids[0]).status_code==404
    assert action(ctx,rid,cids[0],'chapter_complete').status_code==409
    assert ctx['client'].patch(f'/api/resources/{rid}/status',headers=ctx['admin'],json={'status':'offline'}).status_code==200
    assert ctx['client'].get(f'/api/resources/{rid}/course',headers=ctx['learner']).status_code==404
    assert action(ctx,rid,cids[0]).status_code==404

@pytest.mark.parametrize('field,value',[('video_url','https://example.com/x.mp4'),('video_url','/videos/../x.mp4'),('video_url','/videos/x.png'),('video_cover','javascript:alert(1)'),('title',' '),('knowledge_tags',['RDD','RDD'])])
def test_chapter_validation(ctx,field,value):
    rid,_=setup(ctx,0)
    assert ctx['client'].post(f'/api/resources/{rid}/chapters',headers=ctx['admin'],json={**chapter(),field:value}).status_code==422

def test_historical_completion_preserved_and_syllabus_frozen(ctx):
    rid,_=setup(ctx,0)
    for suffix in ('start','complete'):
        assert ctx['client'].post(f'/api/resources/{rid}/{suffix}',headers=ctx['learner'],json={'event_uuid':str(uuid4())}).status_code==200
    response=ctx['client'].post(f'/api/resources/{rid}/chapters',headers=ctx['admin'],json=chapter())
    cid=response.json()['id']
    assert action(ctx,rid,cid).json()['course_status']=='not_started'
    assert ctx['client'].get(f'/api/resources/{rid}/course',headers=ctx['learner']).json()['course_status']=='not_started'
    assert ctx['client'].get('/api/users/me/progress',headers=ctx['learner'],params={'resource_id':rid}).json()['items'][0]['status']=='not_started'
    assert snapshot(ctx,rid)['legacy']==2
    assert ctx['client'].post(f'/api/resources/{rid}/chapters',headers=ctx['admin'],json=chapter(2)).status_code==409

def test_chapter_derived_status_all_stages_and_user_isolation(ctx):
    rid,cids=setup(ctx,5)
    c=ctx['client']
    def read():
        course=c.get(f'/api/resources/{rid}/course',headers=ctx['learner']).json()
        state=c.get('/api/users/me/progress',headers=ctx['learner'],params={'resource_id':rid}).json()['items'][0]['status']
        return course,state
    assert read()[0]['course_status']==read()[1]=='not_started'
    for index,cid in enumerate(cids):
        assert action(ctx,rid,cid).status_code==200
        result=action(ctx,rid,cid,'chapter_complete').json()
        expected='completed' if index==4 else 'in_progress'
        course,state=read()
        assert result['course_status']==course['course_status']==state==expected
        assert sum(ch['completed'] for ch in course['chapters'])==index+1
        filtered=c.get('/api/users/me/progress',headers=ctx['learner'],params={'resource_id':rid,'status':expected}).json()
        assert filtered['total']==1
    assert c.get(f'/api/resources/{rid}/course',headers=ctx['other']).json()['course_status']=='not_started'


def test_hidden_course_list_search_detail_and_admin_preserved(ctx,monkeypatch):
    from app.services import course_presentation
    rid,_=setup(ctx,1)
    monkeypatch.setattr(course_presentation,'HIDDEN_LEARNER_RESOURCE_IDS',frozenset({rid}))
    # Courses imports the same configured IDs; patch the isolated fixture only.
    monkeypatch.setattr(courses,'HIDDEN_LEARNER_RESOURCE_IDS',frozenset({rid}))
    c=ctx['client']
    normal=c.get('/api/resources',headers=ctx['learner'],params={'q':'课程验收','page_size':100}).json()
    assert rid not in {r['id'] for r in normal['items']}
    admin=c.get('/api/resources',headers=ctx['admin'],params={'q':'课程验收','page_size':100}).json()
    assert rid in {r['id'] for r in admin['items']}
    assert admin['total']==normal['total']+1
    assert c.get(f'/api/resources/{rid}',headers=ctx['learner']).status_code==404
    assert c.get(f'/api/resources/{rid}/course',headers=ctx['learner']).status_code==404
    assert c.get(f'/api/resources/{rid}',headers=ctx['admin']).status_code==200


def test_real_demo_is_hidden_without_data_mutation(ctx):
    c=ctx['client']
    admin=c.get('/api/resources/406',headers=ctx['admin'])
    assert admin.status_code==200
    assert c.get('/api/resources/406',headers=ctx['learner']).status_code==404
    result=c.get('/api/resources',headers=ctx['learner'],params={'q':admin.json()['title']}).json()
    assert result['total']==0 and result['items']==[]


def test_dashboard_resource_count_excludes_hidden_fixture(ctx,monkeypatch):
    from app.services import course_presentation
    rid,_=setup(ctx,0)
    c=ctx['client']
    before=c.get('/api/dashboard/overview',headers=ctx['admin']).json()
    monkeypatch.setattr(course_presentation,'HIDDEN_LEARNER_RESOURCE_IDS',frozenset({406,rid}))
    after=c.get('/api/dashboard/overview',headers=ctx['admin']).json()
    assert after['data']['metrics']['resources']['total']==before['data']['metrics']['resources']['total']-1
    assert after['data']['metrics']['resources']['published']==before['data']['metrics']['resources']['published']-1
    assert 'current MySQL' in after['data']['source']
