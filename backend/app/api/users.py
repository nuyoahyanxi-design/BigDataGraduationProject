from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
import jwt

from app.core.security import decode_token, issue_token
from app.database.session import get_db
from app.models import User
from app.schemas.users import Register, Credentials, Interests, UserPublic, TokenResponse
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
    return user


def require_admin(user: User=Depends(current_user)):
    if user.role!='admin':
        raise HTTPException(403,'Administrator role required')
    return user


@router.post('/auth/register',response_model=UserPublic,status_code=201)
def register(payload: Register, db: Session=Depends(get_db)):
    return register_user(db,payload)


@router.post('/auth/login',response_model=TokenResponse)
def login(payload: Credentials, request: Request, db: Session=Depends(get_db)):
    user=authenticate(db,payload)
    settings=request.app.state.auth_settings
    return TokenResponse(access_token=issue_token(user,settings),expires_in=settings.lifetime_seconds)


@router.get('/users/me',response_model=UserPublic)
def me(user: User=Depends(current_user)):
    return user


@router.put('/users/interests',response_model=UserPublic)
def interests(payload: Interests,user: User=Depends(current_user),db: Session=Depends(get_db)):
    return update_interests(db,user,payload.interest_tags)
