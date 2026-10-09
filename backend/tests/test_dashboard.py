import copy
import hashlib
import json
import secrets
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, delete, func
from app.main import app
from app.models import User
from app.services.dashboard import DEFAULT_DASHBOARD
from conftest import SafeTestContext

def publish(path, value):
    record = {k:v for k,v in value.items() if k not in ['status','content_sha256','files','parquet_round_trip']}
    value['content_sha256'] = hashlib.sha256(json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    path.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')

@pytest.fixture(scope='module')
def ctx():
    prefix='dt_'+secrets.token_hex(6); password=secrets.token_urlsafe(24); users=[]
    with TestClient(app) as client:
        with app.state.session_factory() as db: before=db.scalar(select(func.count()).select_from(User))
        try:
            for suffix in ['admin','learner']:
                r=client.post('/api/auth/register',json={'username':prefix+suffix,'password':password}); assert r.status_code==201
                users.append(r.json()['id'])
            with app.state.session_factory() as db: db.get(User,users[0]).role='admin'; db.commit()
            headers=[]
            for suffix in ['admin','learner']:
                r=client.post('/api/auth/login',json={'username':prefix+suffix,'password':password}); assert r.status_code==200
                headers.append({'Authorization':'Bearer '+r.json()['access_token']})
            yield SafeTestContext({'client':client,'headers':headers})
        finally:
            with app.state.session_factory() as db:
                db.execute(delete(User).where(User.id.in_(users))); db.commit()
                after=db.scalar(select(func.count()).select_from(User)); assert after==before
            (Path(__file__).resolve().parents[2]/'outputs/dashboard-fixture-verification.json').write_text(json.dumps({'created_test_users':len(users),'users_before':before,'users_after':after,'created_learning_records':0,'cleanup':'passed'},indent=2)+'\n')

def test_unauthenticated_rejected(ctx):
    assert ctx['client'].get('/api/dashboard/overview').status_code==401

def test_learner_forbidden(ctx):
    assert ctx['client'].get('/api/dashboard/overview',headers=ctx['headers'][1]).status_code==403

def test_admin_reads_actual_spark_statistics(ctx,monkeypatch):
    monkeypatch.delenv('DASHBOARD_MANIFEST_PATH',raising=False)
    r=ctx['client'].get('/api/dashboard/overview',headers=ctx['headers'][0]); assert r.status_code==200
    result=r.json(); assert result['available']
    assert len(result['data']['metrics']['behavior']['daily'])==30
    assert result['data']['spark_version']=='3.5.7'
    artifact=json.loads(DEFAULT_DASHBOARD.read_text())
    assert result['profiles']['users']==sum(result['profiles']['evidence'].values())
    assert result['profiles']['batch_id']==artifact['recommendation_publication']['profile_batch_id']
    assert result['recommendations']['batch_id']==artifact['recommendation_publication']['batch_id']
    assert result['recommendations']['rows']==sum(row['rows'] for row in result['recommendations']['algorithms'])
    assert {row['algorithm'] for row in result['recommendations']['algorithms']}=={'popular_v1','content_v1'}
    assert result['data']['quality']==artifact['quality']
    assert {k:v for k,v in result['data']['metrics'].items() if k not in ('resources','resource_categories')}=={k:v for k,v in artifact['metrics'].items() if k not in ('resources','resource_categories')}
    assert 'current MySQL' in result['data']['source']
    assert result['data']['generated_at'].endswith('Z')
    (Path(__file__).resolve().parents[2]/'outputs/dashboard-api-verification.json').write_text(json.dumps({'http_status':r.status_code,'batch_id':result['data']['batch_id'],'source_batch_id':result['data']['source_batch_id'],'users':result['data']['metrics']['users'],'resources':result['data']['metrics']['resources'],'effective_events':result['data']['metrics']['behavior']['total_effective_events'],'profile_users':result['profiles']['users'],'recommendation_rows':result['recommendations']['rows'],'algorithm_stats':result['recommendations']['algorithms'],'source':'real_Spark_daily_metrics_and_paired_MySQL_results'},indent=2)+'\n')

def test_extra_identity_parameter_rejected(ctx):
    assert ctx['client'].get('/api/dashboard/overview',headers=ctx['headers'][0],params={'user_id':1}).status_code==422

def test_missing_artifact_is_friendly_empty(ctx,monkeypatch,tmp_path):
    monkeypatch.setenv('DASHBOARD_MANIFEST_PATH',str(tmp_path/'none.json'))
    result=ctx['client'].get('/api/dashboard/overview',headers=ctx['headers'][0]).json()
    assert result['available'] is False and result['data'] is None
    assert '尚无' in result['message']

@pytest.mark.parametrize('mode',['tampered','unfinished'])
def test_invalid_artifact_is_503(ctx,monkeypatch,tmp_path,mode):
    value=json.loads(DEFAULT_DASHBOARD.read_text())
    if mode=='tampered': value['metrics']['users']['total']=999999
    else: value['status']='prepared'; publish(tmp_path/'bad.json',value)
    path=tmp_path/'bad.json'; path.write_text(json.dumps(value))
    monkeypatch.setenv('DASHBOARD_MANIFEST_PATH',str(path))
    assert ctx['client'].get('/api/dashboard/overview',headers=ctx['headers'][0]).status_code==503

def test_typed_empty_statistics_not_replaced_by_other_batches(ctx,monkeypatch,tmp_path):
    value=copy.deepcopy(json.loads(DEFAULT_DASHBOARD.read_text()))
    value['recommendation_publication']=None
    value['metrics']['users']={'total':0,'active_learners':0,'admins':0}
    value['metrics']['resources']={'total':0,'published':0}; value['metrics']['resource_categories']=[]
    value['metrics']['behavior']['window_events']=0; value['metrics']['behavior']['total_effective_events']=0
    for row in value['metrics']['behavior']['daily']:
        for key in row:
            if key!='day': row[key]=0
    value['metrics']['learning']={'started_pairs':0,'in_progress':0,'completed':0,'completion_rate':None}
    path=tmp_path/'empty.json'; publish(path,value)
    monkeypatch.setenv('DASHBOARD_MANIFEST_PATH',str(path))
    r=ctx['client'].get('/api/dashboard/overview',headers=ctx['headers'][0]); assert r.status_code==200
    result=r.json(); assert result['recommendations']['rows']==0 and result['profiles']['users']==0
    assert result['data']['metrics']['learning']['completion_rate'] is None
