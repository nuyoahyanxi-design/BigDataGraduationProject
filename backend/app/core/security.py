import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return f'scrypt:16384:8:1${salt.hex()}${digest.hex()}'


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, salt, expected = encoded.split('$')
        if scheme != 'scrypt:16384:8:1' or len(salt) != 32 or len(expected) != 128:
            return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
        return hmac.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


DUMMY_HASH = hash_password(secrets.token_urlsafe(32))


@dataclass(frozen=True)
class AuthSettings:
    secret: str = field(repr=False)
    lifetime_seconds: int = 1800
    issuer: str = 'spark-learning-backend'
    audience: str = 'spark-learning-users'

    @classmethod
    def from_environment(cls):
        secret = os.environ.get('JWT_SECRET', '')
        if len(secret.encode()) < 32:
            raise RuntimeError('JWT_SECRET requires at least 32 bytes')
        return cls(secret)


def issue_token(user, settings: AuthSettings) -> str:
    stamp = datetime.now(timezone.utc)
    return jwt.encode({'sub':str(user.id), 'role':user.role, 'iat':stamp, 'nbf':stamp,
                       'exp':stamp+timedelta(seconds=settings.lifetime_seconds),
                       'iss':settings.issuer, 'aud':settings.audience,
                       'jti':str(uuid4()), 'type':'access'}, settings.secret, algorithm='HS256')


def decode_token(token: str, settings: AuthSettings) -> int:
    claims = jwt.decode(token, settings.secret, algorithms=['HS256'],
                        issuer=settings.issuer, audience=settings.audience,
                        options={'require':['sub','role','iat','nbf','exp','iss','aud','jti','type']})
    subject = claims['sub']
    if not isinstance(subject,str) or not subject.isascii() or not subject.isdecimal() or len(subject)>20:
        raise jwt.InvalidTokenError('Invalid subject')
    user_id = int(subject)
    if not 0 < user_id <= 18446744073709551615 or claims['type']!='access' or claims['role'] not in ('learner','admin'):
        raise jwt.InvalidTokenError('Invalid identity')
    return user_id
