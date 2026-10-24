import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, StringConstraints, field_validator

INTEREST_TAGS = frozenset({'python','java','sql','mysql','spark','big-data','data-analysis',
                           'machine-learning','web-development','algorithms',
                           'rdd','pyspark','hadoop','hdfs','ml','大数据','数据库'})
Tag = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=40)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Credentials(InputModel):
    username: str = Field(min_length=3, max_length=50, strict=True)
    password: SecretStr = Field(min_length=8, max_length=128)

    @field_validator('username', mode='before')
    @classmethod
    def normalize_username(cls, value):
        if not isinstance(value,str):
            raise ValueError('username must be a string')
        value=value.strip().lower()
        if not re.fullmatch(r'[a-z0-9_]{3,50}',value):
            raise ValueError('username must contain 3-50 ASCII letters, digits or underscores')
        return value


class ChallengeInput(InputModel):
    captcha_id: str | None = Field(default=None, max_length=100)
    captcha_answer: SecretStr | None = Field(default=None, max_length=20)


class LoginCredentials(Credentials, ChallengeInput):
    remember_me: bool = Field(default=False, strict=True)


class Interests(InputModel):
    interest_tags: list[Tag] = Field(max_length=10, strict=True)

    @field_validator('interest_tags')
    @classmethod
    def validate_tags(cls, values):
        if len(values)!=len(set(values)) or any(v not in INTEREST_TAGS for v in values):
            raise ValueError('interest_tags must be unique supported codes')
        return values


class Register(Credentials, Interests, ChallengeInput):
    nickname: str | None = Field(default=None, max_length=50)
    interest_tags: list[Tag] = Field(default_factory=list, max_length=10, strict=True)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    nickname: str | None
    role: Literal['learner','admin']
    status: Literal['active','disabled','deleted']
    interest_tags: list[str]
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal['bearer'] = 'bearer'
    expires_in: int


class RegistrationResponse(UserPublic):
    recovery_code: str


class PasswordReset(Credentials, ChallengeInput):
    recovery_code: SecretStr = Field(min_length=20, max_length=100)


class RecoveryEnrollment(InputModel):
    password: SecretStr = Field(min_length=8, max_length=128)


class RecoveryResponse(BaseModel):
    recovery_code: str
    message: str
