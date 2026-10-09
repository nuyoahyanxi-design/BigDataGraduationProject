import secrets
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, func

from app.main import app
from app.models import User
from app.api.users import require_admin
from app.core.security import hash_password, verify_password
from conftest import SafeTestContext


@pytest.fixture(scope='module')
def context():
    created=[]
    password=secrets.token_urlsafe(24)
    prefix='ut_'+secrets.token_hex(6)
    with TestClient(app) as client:
        try:
            for suffix in ('a','b'):
                response=client.post('/api/auth/register',json={'username':prefix+suffix,'password':password,'interest_tags':['python']})
                assert response.status_code==201
                created.append(response.json()['id'])
            response=client.post('/api/auth/login',json={'username':prefix+'a','password':password})
            assert response.status_code==200
            yield SafeTestContext({'client':client,'ids':created,'prefix':prefix,'password':password,
                   'headers':{'Authorization':'Bearer '+response.json()['access_token']}})
        finally:
            with app.state.session_factory() as db:
                if created:
                    db.execute(delete(User).where(User.id.in_(created)))
                    db.commit()
                assert db.scalar(select(func.count()).select_from(User).where(User.username.like(prefix+'%')))==0


def test_registration_and_hash(context):
    with app.state.session_factory() as db:
        user=db.get(User,context['ids'][0])
        assert user.role=='learner' and user.status=='active'
        assert user.password_hash!=context['password']
        assert verify_password(context['password'],user.password_hash)
        assert hash_password(context['password'])!=user.password_hash


def test_duplicate_normalized_username(context):
    response=context['client'].post('/api/auth/register',json={'username':' '+(context['prefix']+'a').upper()+' ','password':context['password']})
    assert response.status_code==409


def test_login_success(context):
    response=context['client'].post('/api/auth/login',json={'username':context['prefix']+'a','password':context['password']})
    assert response.status_code==200
    body=response.json()
    assert set(body)=={'access_token','token_type','expires_in'}
    assert body['token_type']=='bearer' and body['expires_in']==1800


@pytest.mark.parametrize('unknown',[False,True])
def test_wrong_credentials(context,unknown):
    response=context['client'].post('/api/auth/login',json={'username':context['prefix']+('missing' if unknown else 'a'),'password':secrets.token_urlsafe(24)})
    assert response.status_code==401
    assert response.json()['detail']=='Invalid credentials'


def test_authenticated_identity_isolation(context):
    response=context['client'].get('/api/users/me',headers=context['headers'],params={'user_id':context['ids'][1]})
    assert response.status_code==200
    assert response.json()['id']==context['ids'][0]
    assert set(response.json())=={'id','username','nickname','role','status','interest_tags','created_at','updated_at'}
    assert context['client'].get('/api/users/'+str(context['ids'][1]),headers=context['headers']).status_code==404


@pytest.mark.parametrize('path,method',[('/api/users/me','get'),('/api/users/interests','put')])
def test_missing_token(context,path,method):
    kwargs={'json':{'interest_tags':['spark']}} if method=='put' else {}
    assert getattr(context['client'],method)(path,**kwargs).status_code==401


def test_interests_persist_and_only_self(context):
    response=context['client'].put('/api/users/interests',headers=context['headers'],json={'interest_tags':['spark','sql']})
    assert response.status_code==200 and response.json()['interest_tags']==['spark','sql']
    with app.state.session_factory() as db:
        assert db.get(User,context['ids'][0]).interest_tags==['spark','sql']
        assert db.get(User,context['ids'][1]).interest_tags==['python']
    assert context['client'].put('/api/users/interests',headers=context['headers'],json={'interest_tags':[]}).status_code==200


@pytest.mark.parametrize('tags',[['unknown'],['python','python'],[1],[{'tag':'python'}],'python',['python']*11])
def test_invalid_interests(context,tags):
    assert context['client'].put('/api/users/interests',headers=context['headers'],json={'interest_tags':tags}).status_code==422


@pytest.mark.parametrize('extra',[{'role':'admin'},{'status':'active'},{'user_id':1}])
def test_registration_rejects_privilege_fields(context,extra):
    response=context['client'].post('/api/auth/register',json={'username':context['prefix']+'c','password':context['password'],**extra})
    assert response.status_code==422
    assert context['password'] not in response.text


def test_interest_target_rejected(context):
    response=context['client'].put('/api/users/interests',headers=context['headers'],json={'interest_tags':['java'],'user_id':context['ids'][1]})
    assert response.status_code==422


def test_validation_does_not_echo_password(context):
    invalid=secrets.token_urlsafe(200)
    response=context['client'].post('/api/auth/login',json={'username':'bad!','password':invalid})
    assert response.status_code==422 and invalid not in response.text
    assert all('input' not in e for e in response.json()['detail'])


@pytest.mark.parametrize('kind',['expired','wrong_key','wrong_audience','missing_claim','invalid_subject','wrong_algorithm'])
def test_reject_invalid_tokens(context,kind):
    settings=app.state.auth_settings
    stamp=datetime.now(timezone.utc)
    payload={'sub':str(context['ids'][0]),'role':'learner','iat':stamp-timedelta(minutes=2),
             'nbf':stamp-timedelta(minutes=2),'exp':stamp+timedelta(minutes=5),
             'iss':settings.issuer,'aud':settings.audience,'jti':secrets.token_hex(16),'type':'access'}
    key=settings.secret
    algorithm='HS256'
    if kind=='expired':payload['exp']=stamp-timedelta(seconds=1)
    elif kind=='wrong_key':key=secrets.token_urlsafe(48)
    elif kind=='wrong_audience':payload['aud']='other-app'
    elif kind=='missing_claim':del payload['exp']
    elif kind=='invalid_subject':payload['sub']='0'
    elif kind=='wrong_algorithm':algorithm='HS384'
    token=jwt.encode(payload,key,algorithm=algorithm)
    assert context['client'].get('/api/users/me',headers={'Authorization':'Bearer '+token}).status_code==401


def test_disabled_identity_and_login(context):
    with app.state.session_factory() as db:
        db.get(User,context['ids'][0]).status='disabled';db.commit()
    try:
        assert context['client'].get('/api/users/me',headers=context['headers']).status_code==401
        assert context['client'].post('/api/auth/login',json={'username':context['prefix']+'a','password':context['password']}).status_code==401
    finally:
        with app.state.session_factory() as db:
            db.get(User,context['ids'][0]).status='active';db.commit()


def test_roles_use_current_database_state(context):
    with app.state.session_factory() as db:
        user=db.get(User,context['ids'][0])
        with pytest.raises(HTTPException) as error:require_admin(user)
        assert error.value.status_code==403
        user.role='admin';db.commit()
    try:
        response=context['client'].get('/api/users/me',headers=context['headers'])
        assert response.status_code==200 and response.json()['role']=='admin'
        with app.state.session_factory() as db:
            assert require_admin(db.get(User,context['ids'][0])).role=='admin'
    finally:
        with app.state.session_factory() as db:
            db.get(User,context['ids'][0]).role='learner';db.commit()


def test_concurrent_registration(context):
    payload={'username':context['prefix']+'race','password':context['password']}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:context['client'].post('/api/auth/register',json=payload),range(2)))
    for response in results:
        if response.status_code==201:context['ids'].append(response.json()['id'])
    assert sorted(r.status_code for r in results)==[201,409]
