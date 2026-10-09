import json
import secrets
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, delete, func
from app.main import app
from app.models import User, Resource
from app.services import admin as service
from conftest import SafeTestContext

@pytest.fixture(scope='module')
def ctx():
    prefix='at_'+secrets.token_hex(6); password=secrets.token_urlsafe(24); identities=[]; resource_ids=[]
    with TestClient(app) as client:
        with app.state.session_factory() as db:
            before={'users':db.scalar(select(func.count()).select_from(User)),'resources':db.scalar(select(func.count()).select_from(Resource))}
        try:
            for suffix in ['admin','learner']:
                result=client.post('/api/auth/register',json={'username':prefix+suffix,'password':password}); assert result.status_code==201
                identities.append(result.json()['id'])
            with app.state.session_factory() as db: db.get(User,identities[0]).role='admin'; db.commit()
            headers=[]
            for suffix in ['admin','learner']:
                result=client.post('/api/auth/login',json={'username':prefix+suffix,'password':password}); assert result.status_code==200
                headers.append({'Authorization':'Bearer '+result.json()['access_token']})
            yield SafeTestContext({'client':client,'headers':headers,'resources':resource_ids,'prefix':prefix,'user_ids':identities})
        finally:
            with app.state.session_factory() as db:
                db.execute(delete(Resource).where(Resource.id.in_(resource_ids)))
                db.execute(delete(User).where(User.id.in_(identities))); db.commit()
                after={'users':db.scalar(select(func.count()).select_from(User)),'resources':db.scalar(select(func.count()).select_from(Resource))}
                assert before==after
            (Path(__file__).resolve().parents[2]/'outputs/admin-fixture-verification.json').write_text(json.dumps({'before':before,'after':after,'temporary_users':len(identities),'temporary_resources':len(resource_ids),'cleanup':'passed'},indent=2)+'\n')

@pytest.mark.parametrize('path',['/api/admin/users','/api/admin/batches'])
def test_admin_read_permissions(ctx,path):
    client=ctx['client']
    assert client.get(path).status_code==401
    assert client.get(path,headers=ctx['headers'][1]).status_code==403
    assert client.get(path,headers=ctx['headers'][0]).status_code==200

def test_user_list_pagination_and_minimal_fields(ctx):
    client=ctx['client']; headers=ctx['headers'][0]
    first=client.get('/api/admin/users',headers=headers,params={'page':1,'page_size':1}).json()
    second=client.get('/api/admin/users',headers=headers,params={'page':2,'page_size':1}).json()
    assert first['total']>=2 and len(first['items'])==1
    assert first['items'][0]['id']!=second['items'][0]['id']
    assert set(first['items'][0])=={'id','username','role','status','created_at'}
    assert client.get('/api/admin/users',headers=headers,params={'page_size':101}).status_code==422
    assert client.get('/api/admin/users',headers=headers,params={'user_id':1}).status_code==422
    assert client.get('/api/admin/users',headers=headers,params={'page':99999}).json()['items']==[]

def test_actual_batch_records(ctx):
    r=ctx['client'].get('/api/admin/batches',headers=ctx['headers'][0]); assert r.status_code==200
    value=r.json(); assert len(value['items'])==4
    outputs=Path(__file__).resolve().parents[2]/'outputs'
    pipe=json.loads((outputs/'spark-data-pipeline-latest.json').read_text())
    quality=json.loads(Path(pipe['quality_report']).read_text())
    profile=json.loads((outputs/'user-profile-latest.json').read_text())
    rec=json.loads((outputs/'recommendation-latest.json').read_text())
    dash=json.loads((outputs/'dashboard-latest.json').read_text())
    assert [row['data_count'] for row in value['items']]==[quality['output_count'],profile['rows'],rec['counts']['output_rows'],len(dash['metrics']['behavior']['daily'])]
    assert [row['batch_id'] for row in value['items']]==[pipe['batch_id'],profile['batch_id'],rec['batch_id'],dash['batch_id']]
    assert all(row['status']=='completed' for row in value['items'])
    assert value['items'][0]['generated_at'] is None
    assert all('/mnt/' not in row['source'] and ':' not in row['source'] for row in value['items'])
    (Path(__file__).resolve().parents[2]/'outputs/admin-batch-api-verification.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def test_missing_bad_and_traversal_batches(ctx,monkeypatch,tmp_path):
    monkeypatch.setattr(service,'OUTPUTS',tmp_path)
    headers=ctx['headers'][0]; client=ctx['client']
    empty=client.get('/api/admin/batches',headers=headers).json()
    assert all(row['status']=='not_available' and row['data_count'] is None for row in empty['items'])
    (tmp_path/'user-profile-latest.json').write_text('{bad')
    (tmp_path/'spark-data-pipeline-latest.json').write_text(json.dumps({'status':'completed','batch_id':'../../private'}))
    invalid=client.get('/api/admin/batches',headers=headers).json()
    assert invalid['items'][0]['status']=='unavailable' and invalid['items'][1]['status']=='unavailable'
    assert all(row['data_count'] is None for row in invalid['items'])
    assert client.get('/api/admin/batches',headers=headers,params={'path':'secret'}).status_code==422

def test_resource_management_flow_and_permissions(ctx):
    client=ctx['client']; admin,learner=ctx['headers']
    payload={'title':ctx['prefix']+' resource','summary':'管理员阶段临时验证','resource_type':'document','category_code':'data-engineering','tags':['spark'],'difficulty':1,'content':'临时测试正文'}
    assert client.post('/api/resources',headers=learner,json=payload).status_code==403
    assert client.post('/api/resources',json=payload).status_code==401
    r=client.post('/api/resources',headers=admin,json=payload); assert r.status_code==201
    resource=r.json(); identity=resource['id']; ctx['resources'].append(identity)
    assert resource['status']=='draft'
    assert client.get('/api/resources',headers=learner,params={'status':'all'}).status_code==403
    listing=client.get('/api/resources',headers=admin,params={'status':'all','q':ctx['prefix']}).json()
    assert listing['total']==1 and listing['items'][0]['id']==identity
    assert client.get(f'/api/resources/{identity}',headers=learner).status_code==404
    payload['title']+=' edited'
    assert client.put(f'/api/resources/{identity}',headers=learner,json=payload).status_code==403
    edited=client.put(f'/api/resources/{identity}',headers=admin,json=payload)
    assert edited.status_code==200 and edited.json()['title']==payload['title']
    assert client.patch(f'/api/resources/{identity}/status',headers=learner,json={'status':'published'}).status_code==403
    assert client.patch(f'/api/resources/{identity}/status',headers=admin,json={'status':'offline'}).status_code==409
    statuses=[]
    for status in ['published','offline','published']:
        changed=client.patch(f'/api/resources/{identity}/status',headers=admin,json={'status':status})
        assert changed.status_code==200 and changed.json()['status']==status; statuses.append(status)
        visible=client.get(f'/api/resources/{identity}',headers=learner)
        assert visible.status_code==(200 if status=='published' else 404)
    assert client.patch(f'/api/resources/{identity}/status',headers=admin,json={'status':'deleted'}).status_code==422
    (Path(__file__).resolve().parents[2]/'outputs/admin-resource-api-verification.json').write_text(json.dumps({'create':'201 draft','edit':'200','learner_mutation':'403','transitions':statuses,'draft_offline':'409','invalid_status':'422','learner_visibility':'published only'},indent=2)+'\n')
