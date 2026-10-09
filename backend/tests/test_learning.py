import json
import secrets
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4, uuid1

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, delete, func, event
from sqlalchemy.exc import OperationalError

from app.main import app
from app.models import User,Resource,LearningProgress,Favorite,LearningEvent
from app.services import learning
from conftest import SafeTestContext


@pytest.fixture(scope='module')
def ctx():
    users=[];resources=[];prefix='lt_'+secrets.token_hex(6)
    password=secrets.token_urlsafe(24)
    with TestClient(app) as client:
        with app.state.session_factory() as db:
            before={m.__tablename__:db.scalar(select(func.count()).select_from(m)) for m in [User,Resource,LearningProgress,Favorite,LearningEvent]}
        try:
            for suffix in ('admin','a','b'):
                r=client.post('/api/auth/register',json={'username':prefix+suffix,'password':password})
                assert r.status_code==201
                users.append(r.json()['id'])
            with app.state.session_factory() as db:db.get(User,users[0]).role='admin';db.commit()
            headers=[]
            for suffix in ('admin','a','b'):
                r=client.post('/api/auth/login',json={'username':prefix+suffix,'password':password})
                assert r.status_code==200
                headers.append({'Authorization':'Bearer '+r.json()['access_token']})
            def create(published=True):
                r=client.post('/api/resources',headers=headers[0],json={'title':prefix+'资源','resource_type':'document',
                  'category_code':'data-engineering','tags':['spark'],'summary':'行为采集验收','content':'测试正文'})
                assert r.status_code==201
                id=r.json()['id'];resources.append(id)
                if published:
                    assert client.patch(f'/api/resources/{id}/status',headers=headers[0],json={'status':'published'}).status_code==200
                return id
            yield SafeTestContext({'client':client,'users':users,'resources':resources,'create':create,
                                  'admin':headers[0],'a':headers[1],'b':headers[2]})
        finally:
            with app.state.session_factory() as db:
                event_count=db.scalar(select(func.count()).select_from(LearningEvent).where(LearningEvent.user_id.in_(users)))
                effective_count=db.scalar(select(func.count()).select_from(LearningEvent).where(LearningEvent.user_id.in_(users),LearningEvent.is_effective==1))
                for model in [LearningEvent,Favorite,LearningProgress]:
                    db.execute(delete(model).where(model.user_id.in_(users)))
                if resources:db.execute(delete(Resource).where(Resource.id.in_(resources)))
                if users:db.execute(delete(User).where(User.id.in_(users)))
                db.commit()
                after={m.__tablename__:db.scalar(select(func.count()).select_from(m)) for m in [User,Resource,LearningProgress,Favorite,LearningEvent]}
                assert after==before
                evidence={'created_test_users':len(users),'created_test_resources':len(resources),
                          'retained_before_cleanup_test_events':event_count,'effective_test_events':effective_count,
                          'noop_test_receipts':event_count-effective_count,'before':before,'after':after,'cleanup':'passed'}
                (Path(__file__).resolve().parents[2]/'outputs/learning-event-module-fixture-verification.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def payload(view=False,**extra):
    result={'event_uuid':str(uuid4())}
    if view:result['session_id']=str(uuid4())
    return {**result,**extra}


def send(ctx,id,action,body=None,actor='a'):
    body=payload(action=='view') if body is None else body
    method='DELETE' if action=='unfavorite' else 'POST'
    suffix='favorite' if action=='unfavorite' else action
    return ctx['client'].request(method,f'/api/resources/{id}/{suffix}',headers=ctx[actor],json=body)


def state(ctx,id):
    with app.state.session_factory() as db:
        p=db.get(LearningProgress,(ctx['users'][1],id));f=db.get(Favorite,(ctx['users'][1],id))
        return {'progress':None if p is None else (p.status,p.first_started_at,p.completed_at,p.updated_at),
                'favorite':None if f is None else f.created_at,
                'events':db.scalar(select(func.count()).select_from(LearningEvent).where(LearningEvent.user_id==ctx['users'][1],LearningEvent.resource_id==id))}


def test_five_event_types_and_state(ctx):
    id=ctx['create']()
    for action,code in [('view','RESOURCE_VIEW'),('start','LEARNING_START'),('complete','LEARNING_COMPLETE'),('favorite','FAVORITE_ADD'),('unfavorite','FAVORITE_REMOVE')]:
        response=send(ctx,id,action)
        assert response.status_code==200
        result=response.json();assert result['event_type']==code and result['is_effective']==1
        assert result['resource_version']==2 and result['occurred_at']>=result['received_at']
        assert result['event_source']==('client' if action=='view' else 'server')
    current=state(ctx,id)
    assert current['events']==5 and current['progress'][0]=='completed' and current['favorite'] is None
    with app.state.session_factory() as db:
        events=db.scalars(select(LearningEvent).where(LearningEvent.resource_id==id)).all()
        assert {e.event_type for e in events}=={'resource_view','learning_start','learning_complete','favorite_add','favorite_remove'}
        for e in events:assert e.request_fingerprint==learning.fingerprint(e.user_id,e.resource_id,e.event_type)
        progress=db.get(LearningProgress,(ctx['users'][1],id))
        assert progress.first_started_at==next(e.occurred_at for e in events if e.event_type=='learning_start')
        assert progress.completed_at==next(e.occurred_at for e in events if e.event_type=='learning_complete')


@pytest.mark.parametrize('action',['view','start','complete','favorite','unfavorite'])
def test_same_uuid_exact_receipt(ctx,action):
    id=ctx['create']()
    if action=='complete':assert send(ctx,id,'start').status_code==200
    if action=='unfavorite':assert send(ctx,id,'favorite').status_code==200
    body=payload(action=='view')
    first=send(ctx,id,action,body);assert first.status_code==200
    before=state(ctx,id)
    second=send(ctx,id,action,body);assert second.status_code==200
    assert second.json()==first.json() and state(ctx,id)==before


@pytest.mark.parametrize('conflict',['user','resource','type'])
def test_semantic_conflict(ctx,conflict):
    id=ctx['create']();other=ctx['create']();body=payload()
    assert send(ctx,id,'start',body).status_code==200
    r=send(ctx,other if conflict=='resource' else id,'favorite' if conflict=='type' else 'start',body,actor='b' if conflict=='user' else 'a')
    assert r.status_code==409 and r.json()['detail']=='Event UUID conflicts with request semantics'
    assert 'user_id' not in r.json() and state(ctx,id)['events']==1


def test_new_uuid_noops_and_first_times(ctx):
    id=ctx['create']()
    first=send(ctx,id,'start');assert first.status_code==200
    before=state(ctx,id)['progress']
    assert send(ctx,id,'start').json()['is_effective']==0
    assert state(ctx,id)['progress']==before
    assert send(ctx,id,'complete').json()['is_effective']==1
    completed=state(ctx,id)['progress']
    assert send(ctx,id,'complete').json()['is_effective']==0
    assert send(ctx,id,'start').json()['state_after']=='completed'
    assert state(ctx,id)['progress']==completed
    assert send(ctx,id,'favorite').json()['is_effective']==1
    favorite_time=state(ctx,id)['favorite']
    assert send(ctx,id,'favorite').json()['is_effective']==0 and state(ctx,id)['favorite']==favorite_time
    assert send(ctx,id,'unfavorite').json()['is_effective']==1
    assert send(ctx,id,'unfavorite').json()['is_effective']==0


def test_old_noop_cancel_does_not_delete_new_favorite(ctx):
    id=ctx['create']();old=payload()
    first=send(ctx,id,'unfavorite',old);assert first.status_code==200 and first.json()['is_effective']==0
    assert send(ctx,id,'favorite').status_code==200
    before=state(ctx,id)
    repeat=send(ctx,id,'unfavorite',old)
    assert repeat.status_code==200 and repeat.json()==first.json() and state(ctx,id)==before


def test_complete_without_start_rejected(ctx):
    id=ctx['create']();assert send(ctx,id,'complete').status_code==409
    assert state(ctx,id)=={'progress':None,'favorite':None,'events':0}


@pytest.mark.parametrize('action',['start','complete','favorite','unfavorite'])
def test_state_and_event_failure_whole_rollback(ctx,action):
    id=ctx['create']()
    if action=='complete':assert send(ctx,id,'start').status_code==200
    if action=='unfavorite':assert send(ctx,id,'favorite').status_code==200
    before=state(ctx,id);body=payload()
    def invalid_event(_mapper,_connection,target):target.event_source='invalid'
    event.listen(LearningEvent,'before_insert',invalid_event)
    try:
        failed=send(ctx,id,action,body)
    finally:
        event.remove(LearningEvent,'before_insert',invalid_event)
    assert failed.status_code==503 and failed.json()['detail']=='Database operation unavailable'
    assert state(ctx,id)==before
    with app.state.session_factory() as db:
        assert db.scalar(select(LearningEvent.id).where(LearningEvent.event_uuid==body['event_uuid'])) is None
    assert send(ctx,id,action,body).status_code==200


def test_resource_down_replay_and_cancel(ctx):
    id=ctx['create']();body=payload()
    first=send(ctx,id,'favorite',body);assert first.status_code==200
    assert ctx['client'].patch(f'/api/resources/{id}/status',headers=ctx['admin'],json={'status':'offline'}).status_code==200
    assert send(ctx,id,'favorite',body).json()==first.json()
    for action in ('view','start','complete','favorite'):assert send(ctx,id,action).status_code==404
    assert send(ctx,id,'unfavorite').status_code==200 and state(ctx,id)['favorite'] is None


def test_draft_and_missing_resource_permissions(ctx):
    draft=ctx['create'](False)
    for action in ('view','start','complete','favorite','unfavorite'):
        assert send(ctx,draft,action).status_code==404
    assert send(ctx,draft,'view',actor='admin').status_code==404
    assert send(ctx,18446744073709551615,'start').status_code==404


@pytest.mark.parametrize('path',['/api/users/me/progress','/api/users/me/favorites','/api/users/me/events'])
def test_personal_query_auth(ctx,path):
    assert ctx['client'].get(path).status_code==401


def test_write_auth_and_extra_fields(ctx):
    id=ctx['create']()
    assert ctx['client'].post(f'/api/resources/{id}/start',json=payload()).status_code==401
    assert send(ctx,id,'start',payload(user_id=ctx['users'][2])).status_code==422
    assert send(ctx,id,'start',payload(is_effective=1)).status_code==422
    assert send(ctx,id,'view',payload()).status_code==422


@pytest.mark.parametrize('value',['not-a-uuid',str(uuid1()),None])
def test_invalid_uuid(ctx,value):
    id=ctx['create']();assert send(ctx,id,'start',{'event_uuid':value}).status_code==422


def test_view_diagnostic_time_and_retry_semantics(ctx):
    id=ctx['create']();body=payload(True,client_occurred_at='2001-01-01T08:00:00+08:00')
    first=send(ctx,id,'view',body);assert first.status_code==200
    assert first.json()['client_occurred_at'].startswith('2001-01-01T00:00:00')
    assert first.json()['occurred_at'].startswith(str(datetime.now(timezone.utc).year))
    body['session_id']=str(uuid4());body['client_occurred_at']='2030-01-01T00:00:00Z'
    assert send(ctx,id,'view',body).json()==first.json()
    assert send(ctx,id,'view',payload(True,client_occurred_at='2020-01-01T00:00:00')).status_code==422


def test_personal_lists_filters_and_not_started(ctx):
    id=ctx['create']()
    initial=ctx['client'].get('/api/users/me/progress',headers=ctx['a'],params={'resource_id':id}).json()
    assert initial['total']==1 and initial['items'][0]['status']=='not_started'
    assert state(ctx,id)['progress'] is None
    assert send(ctx,id,'start').status_code==200
    assert send(ctx,id,'favorite').status_code==200
    events=ctx['client'].get('/api/users/me/events',headers=ctx['a'],params={'resource_id':id,'page_size':1}).json()
    assert events['total']==2 and len(events['items'])==1
    assert 'request_fingerprint' not in events['items'][0]
    filtered=ctx['client'].get('/api/users/me/events',headers=ctx['a'],params={'resource_id':id,'event_type':'FAVORITE_ADD','is_effective':1}).json()
    assert filtered['total']==1
    assert ctx['client'].get('/api/users/me/progress',headers=ctx['a'],params={'resource_id':id,'status':'in_progress'}).json()['total']==1
    favorites=ctx['client'].get('/api/users/me/favorites',headers=ctx['a']).json()
    assert id in {item['resource_id'] for item in favorites['items']}
    assert ctx['client'].get('/api/users/me/events',headers=ctx['b'],params={'resource_id':id,'user_id':ctx['users'][1]}).json()['total']==0
    assert ctx['client'].get('/api/users/me/progress',headers=ctx['b']).json()['total']==0
    assert ctx['client'].get('/api/users/me/favorites',headers=ctx['b']).json()['total']==0


def test_concurrent_same_uuid_with_old_auth_snapshot(ctx,monkeypatch):
    id=ctx['create']();body=payload();barrier=threading.Barrier(2);local=threading.local()
    original=learning.existing_receipt
    def lookup(*args):
        value=original(*args)
        if not getattr(local,'entered',False):
            local.entered=True;barrier.wait(timeout=5)
        return value
    monkeypatch.setattr(learning,'existing_receipt',lookup)
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:send(ctx,id,'start',body),range(2)))
    assert all(r.status_code==200 for r in responses)
    assert responses[0].json()==responses[1].json() and state(ctx,id)['events']==1


def test_concurrent_new_uuid_favorites(ctx):
    id=ctx['create']()
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:send(ctx,id,'favorite'),range(2)))
    assert all(r.status_code==200 for r in responses)
    assert sorted(r.json()['is_effective'] for r in responses)==[0,1]
    assert state(ctx,id)['events']==2 and state(ctx,id)['favorite'] is not None


def test_concurrent_cross_user_uuid_unique_conflict(ctx,monkeypatch):
    id=ctx['create']();body=payload(True)
    barrier=threading.Barrier(2);original=learning._append_event;errors=[]
    def append(db,**values):
        barrier.wait(timeout=5)
        return original(db,**values)
    def capture_error(context):
        errors.append(context.original_exception.args[0])
    monkeypatch.setattr(learning,'_append_event',append)
    event.listen(app.state.engine,'handle_error',capture_error)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda actor:send(ctx,id,'view',body,actor),['a','b']))
    finally:
        event.remove(app.state.engine,'handle_error',capture_error)
    assert sorted(r.status_code for r in responses)==[200,409]
    assert 1062 in errors
    with app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(LearningEvent).where(LearningEvent.event_uuid==body['event_uuid']))==1


@pytest.mark.parametrize('code',[1205,1213])
def test_bounded_retry_with_same_uuid(ctx,monkeypatch,code):
    id=ctx['create']();body=payload();original=learning._append_event;calls=[]
    def transient(db,**values):
        calls.append(values['event_uuid'])
        if len(calls)==1:raise OperationalError('injected transient',{},Exception(code,'injected'))
        return original(db,**values)
    monkeypatch.setattr(learning,'_append_event',transient)
    assert send(ctx,id,'favorite',body).status_code==200
    assert calls==[body['event_uuid']]*2 and state(ctx,id)['events']==1


def test_retry_exhaustion_rolls_back(ctx,monkeypatch):
    id=ctx['create']();calls=[]
    def unavailable(db,**values):
        calls.append(1);raise OperationalError('injected timeout',{},Exception(1205,'injected'))
    monkeypatch.setattr(learning,'_append_event',unavailable)
    assert send(ctx,id,'favorite').status_code==503 and len(calls)==3
    assert state(ctx,id)=={'progress':None,'favorite':None,'events':0}


@pytest.mark.parametrize('params',[{'page':0},{'page_size':101},{'event_type':'learning_start'},{'is_effective':2}])
def test_query_validation(ctx,params):
    assert ctx['client'].get('/api/users/me/events',headers=ctx['a'],params=params).status_code==422


def test_old_successful_favorite_replay_does_not_recreate(ctx):
    id=ctx['create']();body=payload()
    first=send(ctx,id,'favorite',body);assert first.status_code==200
    assert send(ctx,id,'unfavorite').status_code==200
    before=state(ctx,id)
    assert send(ctx,id,'favorite',body).json()==first.json()
    assert state(ctx,id)==before and before['favorite'] is None


def test_uppercase_uuid_normalized(ctx):
    id=ctx['create']();body=payload();body['event_uuid']=body['event_uuid'].upper()
    first=send(ctx,id,'start',body);assert first.status_code==200
    assert first.json()['event_uuid']==body['event_uuid'].lower()
    body['event_uuid']=body['event_uuid'].lower()
    assert send(ctx,id,'start',body).json()==first.json()


def test_soft_deleted_resource_can_remove_own_favorite(ctx):
    id=ctx['create']();assert send(ctx,id,'favorite').status_code==200
    with app.state.session_factory() as db:
        db.get(Resource,id).status='deleted';db.commit()
    assert send(ctx,id,'unfavorite').status_code==200
    assert state(ctx,id)['favorite'] is None


def test_disabled_actor_cannot_write(ctx):
    id=ctx['create']()
    with app.state.session_factory() as db:
        db.get(User,ctx['users'][1]).status='disabled';db.commit()
    try:
        assert send(ctx,id,'start').status_code==401
        assert state(ctx,id)['events']==0
    finally:
        with app.state.session_factory() as db:
            db.get(User,ctx['users'][1]).status='active';db.commit()
