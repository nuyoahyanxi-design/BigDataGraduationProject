from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
import jwt
import hashlib
import hmac
import secrets
from dataclasses import replace
from sqlalchemy import select
from fastapi.responses import JSONResponse
from app.services.auth_challenges import guard
from app.core.security import token_matches_password, hash_password, verify_password, DUMMY_HASH
from app.services.users import utc_now
from app.models import AuthRecoveryCode
from app.schemas.users import LoginCredentials, RegistrationResponse, PasswordReset, RecoveryEnrollment, RecoveryResponse

from app.core.security import decode_token, issue_token
from app.database.session import get_db
from app.models import User
from app.schemas.users import Register, Interests, UserPublic, TokenResponse
from app.services.users import register_user, authenticate, update_interests

router=APIRouter(prefix='/api',tags=['users'])
bearer=HTTPBearer(auto_error=False)


def current_user(request: Request, credentials: HTTPAuthorizationCredentials | None=Depends(bearer), db: Session=Depends(get_db)):
    failure=HTTPException(401,'Authentication required',headers={'WWW-Authenticate':'Bearer'})
    if credentials is None:
        raise failure
    try:
        user_id=decode_token(credentials.credentials,request.app.state.auth_settings)
    except jwt.InvalidTokenError:
        raise failure from None
    user=db.get(User,user_id)
    if user is None or user.status!='active':
        raise failure
    try:
        if not token_matches_password(credentials.credentials,user,request.app.state.auth_settings):raise failure
    except jwt.InvalidTokenError:
        raise failure from None
    return user


def require_admin(user: User=Depends(current_user)):
    if user.role!='admin':
        raise HTTPException(403,'Administrator role required')
    return user


def no_store(response):
    response.headers['Cache-Control']='no-store'
    response.headers['Pragma']='no-cache'


def protected_attempt(request, payload, operation):
    if not request.app.state.auth_settings.captcha_required:return
    ip=request.client.host if request.client else 'unknown'
    guard.throttle(operation+':ip:'+ip,60)
    guard.throttle(operation+':account:'+payload.username,15)
    if request.app.state.auth_settings.captcha_required:
        guard.verify(payload.captcha_id,payload.captcha_answer)


@router.get('/auth/captcha')
def captcha(request: Request):
    guard.throttle('captcha:'+ (request.client.host if request.client else 'unknown'),60)
    return JSONResponse(guard.create(),headers={'Cache-Control':'no-store','Pragma':'no-cache'})


@router.post('/auth/register',response_model=RegistrationResponse,status_code=201)
def register(payload: Register, request: Request, response: Response, db: Session=Depends(get_db)):
    protected_attempt(request,payload,'register')
    code=secrets.token_urlsafe(32)
    user=register_user(db,payload,recovery_hash=hashlib.sha256(code.encode()).hexdigest())
    no_store(response)
    return RegistrationResponse(**UserPublic.model_validate(user).model_dump(),recovery_code=code)


@router.post('/auth/login',response_model=TokenResponse)
def login(payload: LoginCredentials, request: Request, response: Response, db: Session=Depends(get_db)):
    protected_attempt(request,payload,'login')
    user=authenticate(db,payload)
    settings=request.app.state.auth_settings
    if payload.remember_me:settings=replace(settings,lifetime_seconds=7*24*3600)
    no_store(response)
    return TokenResponse(access_token=issue_token(user,settings),expires_in=settings.lifetime_seconds)


@router.post('/auth/recovery-code',response_model=RecoveryResponse)
def enroll_recovery(payload: RecoveryEnrollment, request: Request, response: Response, user: User=Depends(current_user),db: Session=Depends(get_db)):
    guard.throttle('enroll:'+str(user.id),10)
    locked=db.scalar(select(User).where(User.id==user.id).with_for_update().execution_options(populate_existing=True))
    if locked is None or locked.status!='active' or not verify_password(payload.password.get_secret_value(),locked.password_hash):raise HTTPException(401,'Invalid credentials')
    code=secrets.token_urlsafe(32)
    row=db.get(AuthRecoveryCode,user.id)
    if row is None:db.add(AuthRecoveryCode(user_id=user.id,code_hash=hashlib.sha256(code.encode()).hexdigest()))
    else:row.code_hash=hashlib.sha256(code.encode()).hexdigest()
    db.commit();no_store(response)
    return RecoveryResponse(recovery_code=code,message='Save this recovery code offline; the old code is invalid.')


@router.post('/auth/reset-password',response_model=RecoveryResponse)
def reset_password(payload: PasswordReset,request: Request,response: Response,db: Session=Depends(get_db)):
    protected_attempt(request,payload,'reset')
    user=db.scalar(select(User).where(User.username==payload.username).with_for_update().execution_options(populate_existing=True))
    row=db.get(AuthRecoveryCode,user.id) if user else None
    candidate=hashlib.sha256(payload.recovery_code.get_secret_value().strip().encode()).hexdigest()
    if not user or user.status!='active' or not row or not hmac.compare_digest(row.code_hash,candidate):
        # Comparable password hashing work without disclosing which input failed.
        verify_password(payload.password.get_secret_value(),DUMMY_HASH)
        raise HTTPException(400,'Recovery information invalid')
    code=secrets.token_urlsafe(32)
    user.password_hash=hash_password(payload.password.get_secret_value());user.updated_at=utc_now()
    row.code_hash=hashlib.sha256(code.encode()).hexdigest()
    db.commit();no_store(response)
    return RecoveryResponse(recovery_code=code,message='Password reset. Save the new recovery code and sign in again.')


@router.get('/users/me',response_model=UserPublic)
def me(user: User=Depends(current_user)):
    return user


@router.put('/users/interests',response_model=UserPublic)
def interests(payload: Interests,user: User=Depends(current_user),db: Session=Depends(get_db)):
    return update_interests(db,user,payload.interest_tags)
