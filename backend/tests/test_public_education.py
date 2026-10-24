import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app.api.dashboard import router
from app.api.users import current_user
from app.services import public_education as service
ROOT=Path(__file__).resolve().parents[2]

@pytest.fixture
def publication(tmp_path,monkeypatch):
    pointer={'batch_id':'fixture','summary':'analysis/fixture/ads/summary.json'}
    payload={'schema_version':1,'source_dataset':'OULAD','source_kind':'external_anonymised_education_data','source_doi':'10.24432/C5KK69','source_url':'https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset','license':'CC BY 4.0','citation':'Synthetic fixture, not real results','source_period':'2013–2014','generated_at':'2026-10-23T00:00:00Z','batch_id':'fixture','archive_sha256':'0'*64,'spark_version':'3.5.7','spark_master':'local[2]','metrics':{'unique_students':1,'enrolments':2,'modules':1,'presentations':1,'interaction_rows':1,'total_clicks':3},'daily_clicks':[{'date':-1,'clicks':3}],'outcomes':[{'final_result':'Pass','count':2}],'activity_clicks':[{'activity_type':'resource','clicks':3}],'module_clicks':[{'code_module':'AAA','clicks':3}],'quality':{'input_rows':1,'output_rows':1,'invalid_rows':0,'orphan_interactions':0,'audit_reconciled':True,'source_counts':{'studentVle':1}},'definitions':{'scope':'Test only'}}
    target=tmp_path/pointer['summary'];target.parent.mkdir(parents=True);target.write_text(json.dumps(payload),encoding='utf-8')
    latest=tmp_path/'analysis/latest.json';latest.write_text(json.dumps(pointer))
    monkeypatch.setattr(service,'BASE',tmp_path)
    return latest,target

def test_unpublished_is_clear(tmp_path,monkeypatch):
    monkeypatch.setattr(service,'BASE',tmp_path)
    assert service.published_education()=={'available':False,'data':None,'message':'公开教育数据尚未发布'}

def test_read_published_aggregates(publication):
    result=service.published_education();assert result['available']
    data=result['data'];assert data.metrics.unique_students==1
    assert sum(x.clicks for x in data.daily_clicks)==data.metrics.total_clicks==3
    assert sum(x.count for x in data.outcomes)==data.metrics.enrolments==2
    assert not hasattr(data,'id_student') and data.spark_master=='local[2]'

def test_path_escape_rejected(publication):
    latest,_=publication;latest.write_text(json.dumps({'batch_id':'bad','summary':'../../outside/summary.json'}))
    with pytest.raises(HTTPException) as exc:service.published_education()
    assert exc.value.status_code==503

def test_corrupt_publication_rejected(publication):
    _,target=publication;target.write_text('{broken')
    with pytest.raises(HTTPException) as exc:service.published_education()
    assert exc.value.status_code==503

def test_wrong_batch_rejected(publication):
    latest,_=publication;value=json.loads(latest.read_text());value['batch_id']='wrong';latest.write_text(json.dumps(value))
    with pytest.raises(HTTPException):service.published_education()

def test_admin_endpoint_and_learner_denial(publication):
    app=FastAPI();app.include_router(router)
    app.dependency_overrides[current_user]=lambda:SimpleNamespace(role='admin')
    with TestClient(app) as client:
        assert client.get('/api/dashboard/public-education').status_code==200
        assert client.get('/api/dashboard/public-education?execute=true').status_code==422
        app.dependency_overrides[current_user]=lambda:SimpleNamespace(role='learner')
        assert client.get('/api/dashboard/public-education').status_code==403

def test_authentication_required():
    from app.database.session import get_db
    app=FastAPI();app.include_router(router)
    app.dependency_overrides[get_db]=lambda:None
    with TestClient(app) as client:assert client.get('/api/dashboard/public-education').status_code==401
