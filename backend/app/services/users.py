from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import User
from app.core.security import DUMMY_HASH, hash_password, verify_password


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def register_user(db, payload):
    if db.scalar(select(User.id).where(User.username==payload.username)) is not None:
        raise HTTPException(409, 'Username already registered')
    stamp=utc_now()
    user=User(username=payload.username, password_hash=hash_password(payload.password.get_secret_value()),
              nickname=payload.nickname, role='learner', status='active',
              interest_tags=payload.interest_tags, created_at=stamp, updated_at=stamp)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if getattr(exc.orig,'args',())[0:1] == (1062,):
            raise HTTPException(409,'Username already registered') from None
        raise HTTPException(503,'Database operation unavailable') from None
    return user


def authenticate(db, payload):
    user=db.scalar(select(User).where(User.username==payload.username))
    verified=verify_password(payload.password.get_secret_value(),user.password_hash if user else DUMMY_HASH)
    if not user or not verified or user.status!='active':
        raise HTTPException(401,'Invalid credentials',headers={'WWW-Authenticate':'Bearer'})
    return user


def update_interests(db, user, tags):
    user.interest_tags=list(tags)
    user.updated_at=utc_now()
    db.commit()
    return user
