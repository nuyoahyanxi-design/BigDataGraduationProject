from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, UUID4, Field, field_validator, model_validator
from app.schemas.users import InputModel

CONSENT_VERSION = 'agnes-external-v1'


class Question(InputModel):
    request_uuid: UUID4
    question: str = Field(min_length=1, max_length=2000)
    mode: Literal['general', 'resource'] = 'general'
    resource_id: int | None = Field(default=None, ge=1, le=18446744073709551615)
    consent_version: Literal['agnes-external-v1']

    @field_validator('question')
    @classmethod
    def nonblank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Blank question')
        return value

    @model_validator(mode='after')
    def mode_matches(self):
        if (self.mode == 'resource') != (self.resource_id is not None):
            raise ValueError('Resource mode requires a resource')
        return self


class Record(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    request_uuid: str
    mode: str
    resource_id: int | None
    resource_version: int | None
    question: str
    answer: str | None
    status: Literal['pending', 'succeeded', 'failed', 'unknown']
    model: str
    created_at: datetime
    finished_at: datetime | None
    error_code: str | None
    source: str


class History(BaseModel):
    items: list[Record]
    total: int
    page: int
    page_size: int
