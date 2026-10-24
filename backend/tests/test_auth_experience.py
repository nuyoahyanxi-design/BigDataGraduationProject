"""Isolated HTTP acceptance: SQLite fixture only, never the project MySQL."""
import base64
import hashlib
import secrets
from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.users import router
from app.core.security import AuthSettings, hash_password
from app.database.session import get_db
from app.services import auth_challenges
from app.services.auth_challenges import AuthChallenges

@pytest.fixture
def context(monkeypatch):
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    with engine.begin() as db:
        db.exec_driver_sql('CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username VARCHAR(50) UNIQUE NOT NULL, password_hash VARCHAR(255) NOT NULL, nickname VARCHAR(50), role VARCHAR(20) NOT NULL, status VARCHAR(20) NOT NULL, interest_tags JSON NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)')
        db.exec_driver_sql('CREATE TABLE auth_recovery_codes (user_id INTEGER PRIMARY KEY REFERENCES users(id), code_hash VARCHAR(64) NOT NULL)')
    sessions=sessionmaker(engine,expire_on_commit=False)
    application=FastAPI();application.include_router(router)
    application.state.auth_settings=AuthSettings(secrets.token_urlsafe(48))
    def database():
        with sessions() as db:yield db
    application.dependency_overrides[get_db]=database
    guard=AuthChallenges();monkeypatch.setattr('app.api.users.guard',guard)
    answers={};real=auth_challenges.raster
    def capture(answer):answers['current']=answer;return real(answer)
    monkeypatch.setattr(auth_challenges,'raster',capture)
    with TestClient(application) as client:
        yield SimpleNamespace(client=client,answers=answers,sessions=sessions,settings=application.state.auth_settings,app=application,guard=guard)
    engine.dispose()

def challenge(ctx):
    response=ctx.client.get('/api/auth/captcha');assert response.status_code==200
    assert response.headers['cache-control']=='no-store'
    return {'captcha_id':response.json()['captcha_id'],'captcha_answer':ctx.answers['current']}

def register(ctx,name='sample_user'):
    password=secrets.token_urlsafe(20)
    response=ctx.client.post('/api/auth/register',json={'username':name,'password':password,**challenge(ctx)})
    assert response.status_code==201
    return password,response.json()['recovery_code']

def login(ctx,password,**extra):
    return ctx.client.post('/api/auth/login',json={'username':'sample_user','password':password,**challenge(ctx),**extra})

def test_captcha_png_and_missing_verification(context):
    item=context.client.get('/api/auth/captcha').json()
    assert set(item)=={'captcha_id','image','expires_in'}
    assert base64.b64decode(item['image'].split(',')[1]).startswith(b'\x89PNG')
    assert context.client.post('/api/auth/login',json={'username':'sample_user','password':'invalid-password'}).status_code==400
    assert context.client.post('/api/auth/register',json={'username':'sample_user','password':'invalid-password'}).status_code==400

def test_wrong_captcha_is_consumed(context):
    fields=challenge(context)
    assert context.client.post('/api/auth/login',json={'username':'sample_user','password':'invalid-password',**fields,'captcha_answer':'XXXXX'}).status_code==400
    assert context.client.post('/api/auth/login',json={'username':'sample_user','password':'invalid-password',**fields}).status_code==400

def test_expired_captcha(context):
    fields=challenge(context);entry=context.guard.challenges[fields['captcha_id']]
    context.guard.challenges[fields['captcha_id']]=(entry[0],0)
    with pytest.raises(Exception) as error:context.guard.verify(fields['captcha_id'],SecretStr(fields['captcha_answer']))
    assert error.value.status_code==400

def test_register_hash_and_least_privilege(context):
    password,code=register(context)
    with context.sessions() as db:
        user=db.execute(text('SELECT password_hash, role FROM users')).first()
        digest=db.scalar(text('SELECT code_hash FROM auth_recovery_codes'))
    assert user[0]!=password and user[1]=='learner'
    assert digest==hashlib.sha256(code.encode()).hexdigest() and digest!=code
    response=context.client.post('/api/auth/register',json={'username':'privileged','password':password,'role':'admin',**challenge(context)})
    assert response.status_code==422

def test_normal_and_remember_lifetimes(context):
    password,_=register(context)
    regular=login(context,password);remembered=login(context,password,remember_me=True)
    assert regular.status_code==remembered.status_code==200
    assert regular.json()['expires_in']==1800
    assert remembered.json()['expires_in']==604800
    assert remembered.headers['cache-control']=='no-store'

def test_reset_revokes_tokens_and_rotates_code(context):
    password,code=register(context);token=login(context,password).json()['access_token']
    new_password=secrets.token_urlsafe(24)
    result=context.client.post('/api/auth/reset-password',json={'username':'sample_user','password':new_password,'recovery_code':code,**challenge(context)})
    assert result.status_code==200 and result.json()['recovery_code']!=code
    assert context.client.get('/api/users/me',headers={'Authorization':'Bearer '+token}).status_code==401
    assert login(context,password).status_code==401
    assert login(context,new_password).status_code==200
    replay=context.client.post('/api/auth/reset-password',json={'username':'sample_user','password':password,'recovery_code':code,**challenge(context)})
    assert replay.status_code==400

def test_invalid_recovery_does_not_change_password(context):
    password,_=register(context)
    result=context.client.post('/api/auth/reset-password',json={'username':'sample_user','password':secrets.token_urlsafe(20),'recovery_code':secrets.token_urlsafe(32),**challenge(context)})
    assert result.status_code==400 and login(context,password).status_code==200

def test_unknown_and_wrong_recovery_same_response(context):
    password,_=register(context)
    responses=[context.client.post('/api/auth/reset-password',json={'username':name,'password':password,'recovery_code':secrets.token_urlsafe(32),**challenge(context)}) for name in ['sample_user','unknown_user']]
    assert responses[0].status_code==responses[1].status_code==400
    assert responses[0].json()==responses[1].json()

def test_enrollment_requires_password_and_invalidates_old_code(context):
    password,old_code=register(context);headers={'Authorization':'Bearer '+login(context,password).json()['access_token']}
    assert context.client.post('/api/auth/recovery-code',headers=headers,json={'password':'wrong-password'}).status_code==401
    result=context.client.post('/api/auth/recovery-code',headers=headers,json={'password':password})
    assert result.status_code==200 and result.json()['recovery_code']!=old_code
    assert context.client.post('/api/auth/reset-password',json={'username':'sample_user','password':password,'recovery_code':old_code,**challenge(context)}).status_code==400

def test_recovery_requires_authentication(context):
    assert context.client.post('/api/auth/recovery-code',json={'password':'wrong-password'}).status_code==401

def test_throttle_and_bounded_challenges(context):
    for _ in range(3):context.guard.throttle('fixture',limit=3)
    with pytest.raises(Exception) as error:context.guard.throttle('fixture',limit=3)
    assert error.value.status_code==429

def test_duplicate_username(context):
    password,_=register(context)
    result=context.client.post('/api/auth/register',json={'username':'sample_user','password':password,**challenge(context)})
    assert result.status_code==409
