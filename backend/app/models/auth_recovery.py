"""Additive credential recovery storage, unrelated to learning/analytics."""
from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.mysql import BIGINT
from app.database.base import Base

class AuthRecoveryCode(Base):
    __tablename__='auth_recovery_codes'
    user_id=Column(BIGINT(unsigned=True),ForeignKey('users.id',ondelete='CASCADE'),primary_key=True)
    code_hash=Column(String(64),nullable=False)
