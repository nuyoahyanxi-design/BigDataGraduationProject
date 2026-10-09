import secrets
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, delete, func

from app.main import app
from app.models import User, Resource, LearningProgress, Favorite, LearningEvent
from conftest import SafeTestContext


@pytest.fixture(scope='module')
def ctx():
    prefix='rt_'+secrets.token_hex(6)
    users=[];resources=[]
    password=secrets.token_urlsafe(24)
    with TestClient(app) as client:
        with app.state.session_factory() as db:
            original={m.__tablename__:db.scalar(select(func.count()).select_from(m)) for m in [User,Resource,LearningProgress,Favorite,LearningEvent]}
        try:
            for suffix in ['admin','learner']:
                r=client.post('/api/auth/register',json={'username':prefix+suffix,'password':password})
                assert r.status_code==201
                users.append(r.json()['id'])
            with app.state.session_factory() as db:
                db.get(User,users[0]).role='admin';db.commit()
            headers=[]
            for suffix in ['admin','learner']:
                r=client.post('/api/auth/login',json={'username':prefix+suffix,'password':password})
                assert r.status_code==200
                headers.append({'Authorization':'Bearer '+r.json()['access_token']})
            def payload(**changes):
                return {'title':prefix+'资源','resource_type':'document','category_code':'data-engineering',
                        'tags':['spark','python'],'summary':'资源模块验收','content':'自编测试正文',**changes}
            def create(**changes):
                r=client.post('/api/resources',headers=headers[0],json=payload(**changes))
                assert r.status_code==201
                resources.append(r.json()['id'])
                return r.json()
            yield SafeTestContext({'client':client,'admin':headers[0],'learner':headers[1],'users':users,'resources':resources,
                   'prefix':prefix,'payload':payload,'create':create}
            )
        finally:
            with app.state.session_factory() as db:
                if resources:db.execute(delete(Resource).where(Resource.id.in_(resources)))
                if users:db.execute(delete(User).where(User.id.in_(users)))
                db.commit()
                after={m.__tablename__:db.scalar(select(func.count()).select_from(m)) for m in [User,Resource,LearningProgress,Favorite,LearningEvent]}
                assert after==original
                evidence={'created_test_users':len(users),'created_test_resources':len(resources),
                          'before':original,'after':after,'cleanup':'passed',
                          'learning_tables_unchanged':True}
                (Path(__file__).resolve().parents[2]/'outputs/resource-module-fixture-verification.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def change(ctx,id,status):
    return ctx['client'].patch(f'/api/resources/{id}/status',headers=ctx['admin'],json={'status':status})


def test_admin_creation(ctx):
    resource=ctx['create']()
    assert resource['status']=='draft' and resource['version_no']==1
    assert resource['created_by']==ctx['users'][0] and resource['published_at'] is None
    assert len(resource)==17
    with app.state.session_factory() as db:assert db.get(Resource,resource['id']).title==resource['title']


@pytest.mark.parametrize('method',['post_create','put_edit','patch_status'])
def test_learner_writes_denied(ctx,method):
    resource=ctx['create']();id=resource['id']
    if method=='post_create':r=ctx['client'].post('/api/resources',headers=ctx['learner'],json=ctx['payload']())
    elif method=='put_edit':r=ctx['client'].put(f'/api/resources/{id}',headers=ctx['learner'],json=ctx['payload']())
    else:r=ctx['client'].patch(f'/api/resources/{id}/status',headers=ctx['learner'],json={'status':'published'})
    assert r.status_code==403


def test_visibility_and_status_cycle(ctx):
    resource=ctx['create']();id=resource['id'];client=ctx['client']
    assert client.get(f'/api/resources/{id}',headers=ctx['learner']).status_code==404
    assert client.get(f'/api/resources/{id}',headers=ctx['admin']).status_code==200
    assert change(ctx,id,'offline').status_code==409
    published=change(ctx,id,'published');assert published.status_code==200
    first=published.json();assert first['version_no']==2 and first['published_at']
    assert client.get(f'/api/resources/{id}',headers=ctx['learner']).status_code==200
    repeat=change(ctx,id,'published').json()
    assert repeat['version_no']==2 and repeat['updated_at']==first['updated_at']
    assert change(ctx,id,'offline').json()['version_no']==3
    assert client.get(f'/api/resources/{id}',headers=ctx['learner']).status_code==404
    ordinary=client.get('/api/resources',headers=ctx['learner'],params={'q':ctx['prefix']}).json()
    assert id not in {r['id'] for r in ordinary['items']}
    assert client.get('/api/resources',headers=ctx['learner'],params={'status':'all'}).status_code==403
    assert client.get('/api/resources',headers=ctx['admin'],params={'status':'offline','q':ctx['prefix']}).json()['total']>=1
    again=change(ctx,id,'published').json()
    assert again['version_no']==4 and again['published_at']==first['published_at']


def test_list_pagination_filter_and_search(ctx):
    group=ctx['prefix']+'paging'
    for i in range(3):
        id=ctx['create'](title=group+str(i))['id']
        assert change(ctx,id,'published').status_code==200
    r=ctx['client'].get('/api/resources',headers=ctx['learner'],params={'q':group,'page_size':2,'page':1,'category_code':'data-engineering','resource_type':'document'})
    assert r.status_code==200
    result=r.json();assert result['total']==3 and len(result['items'])==2
    assert 'content' not in result['items'][0]
    second=ctx['client'].get('/api/resources',headers=ctx['learner'],params={'q':group,'page_size':2,'page':2}).json()
    assert len(second['items'])==1
    assert result['items'][0]['id']>result['items'][1]['id']>second['items'][0]['id']
    assert ctx['client'].get('/api/resources',headers=ctx['learner'],params={'q':'%'+ctx['prefix']}).json()['total']==0


def test_modification_version_and_integrity(ctx):
    resource=ctx['create']();id=resource['id']
    r=ctx['client'].put(f'/api/resources/{id}',headers=ctx['admin'],json=ctx['payload'](title='修改资源'))
    assert r.status_code==200 and r.json()['version_no']==2
    repeat=ctx['client'].put(f'/api/resources/{id}',headers=ctx['admin'],json=ctx['payload'](title='修改资源')).json()
    assert repeat['version_no']==2
    assert change(ctx,id,'published').status_code==200
    r=ctx['client'].put(f'/api/resources/{id}',headers=ctx['admin'],json=ctx['payload'](title='修改资源',tags=[]))
    assert r.status_code==422
    assert ctx['client'].get(f'/api/resources/{id}',headers=ctx['admin']).json()['version_no']==3


@pytest.mark.parametrize('status',['draft','deleted','invalid',1])
def test_invalid_status_rejected(ctx,status):
    id=ctx['create']()['id'];assert change(ctx,id,status).status_code==422


@pytest.mark.parametrize('changes',[{'title':'   '},{'title':''},{'summary':' '},{'tags':['unknown']},{'tags':['spark','spark']},{'tags':[1]},{'tags':'spark'},{'tags':['spark']*11},{'category_code':'unknown'},{'difficulty':True},{'resource_type':'video'},{'created_by':1},{'status':'published'},{'version_no':9}])
def test_bad_resource_payload(ctx,changes):
    assert ctx['client'].post('/api/resources',headers=ctx['admin'],json=ctx['payload'](**changes)).status_code==422


@pytest.mark.parametrize('changes',[{'tags':[]},{'content':None,'content_url':None}])
def test_incomplete_draft_cannot_publish(ctx,changes):
    resource=ctx['create'](**changes)
    assert change(ctx,resource['id'],'published').status_code==422
    result=ctx['client'].get(f"/api/resources/{resource['id']}",headers=ctx['admin']).json()
    assert result['status']=='draft' and result['version_no']==1 and result['published_at'] is None


@pytest.mark.parametrize('url',['file:///C:/secret','ftp://example.com/x','https://user:pass@example.com/x','http://127.0.0.1/x','http://localhost/x','https://example.com/#private'])
def test_invalid_content_url(ctx,url):
    assert ctx['client'].post('/api/resources',headers=ctx['admin'],json=ctx['payload'](content_url=url)).status_code==422


def test_external_url_resource(ctx):
    resource=ctx['create'](content=None,content_url='https://example.com/learning')
    assert change(ctx,resource['id'],'published').status_code==200


def test_missing_identity_and_unknown_resource(ctx):
    assert ctx['client'].get('/api/resources').status_code==401
    assert ctx['client'].post('/api/resources',json=ctx['payload']()).status_code==401
    assert ctx['client'].get('/api/resources/18446744073709551615',headers=ctx['learner']).status_code==404
    assert ctx['client'].put('/api/resources/18446744073709551615',headers=ctx['admin'],json=ctx['payload']()).status_code==404


@pytest.mark.parametrize('params',[{'page':0},{'page_size':101},{'category_code':'bad'},{'status':'deleted'}])
def test_bad_list_params(ctx,params):
    assert ctx['client'].get('/api/resources',headers=ctx['learner'],params=params).status_code==422


def test_deleted_resource_terminal(ctx):
    id=ctx['create']()['id']
    with app.state.session_factory() as db:db.get(Resource,id).status='deleted';db.commit()
    assert ctx['client'].get(f'/api/resources/{id}',headers=ctx['admin']).status_code==404
    assert change(ctx,id,'published').status_code==404


def test_concurrent_edits_preserve_version(ctx):
    id=ctx['create']()['id']
    def edit(i):return ctx['client'].put(f'/api/resources/{id}',headers=ctx['admin'],json=ctx['payload'](title='并发标题'+str(i)))
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(edit,range(2)))
    assert all(r.status_code==200 for r in responses)
    assert ctx['client'].get(f'/api/resources/{id}',headers=ctx['admin']).json()['version_no']==3
