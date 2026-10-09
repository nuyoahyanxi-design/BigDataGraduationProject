from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, UUID4, field_validator
from app.schemas.users import InputModel

EventType=Literal['RESOURCE_VIEW','LEARNING_START','LEARNING_COMPLETE','FAVORITE_ADD','FAVORITE_REMOVE']
ProgressStatus=Literal['not_started','in_progress','completed']


class BehaviorRequest(InputModel):
    event_uuid: UUID4
    session_id: UUID4 | None = None


class ViewRequest(BehaviorRequest):
    session_id: UUID4
    client_occurred_at: datetime | None = None

    @field_validator('client_occurred_at')
    @classmethod
    def utc_client_time(cls,value):
        if value is not None:
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError('Client time requires a timezone')
            value=value.astimezone(timezone.utc).replace(tzinfo=None)
            value=value.replace(microsecond=value.microsecond//1000*1000)
        return value


class EventReceipt(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: int
    event_uuid: str
    user_id: int
    resource_id: int
    event_type: EventType
    event_source: Literal['client','server']
    schema_version: int
    resource_version: int
    session_id: str | None
    occurred_at: datetime
    received_at: datetime
    client_occurred_at: datetime | None
    is_effective: Literal[0,1]
    state_before: str | None
    state_after: str | None

    @field_validator('event_type',mode='before')
    @classmethod
    def public_event_name(cls,value):
        return value.upper() if isinstance(value,str) else value


class ProgressItem(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    resource_id: int
    status: ProgressStatus
    first_started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime | None


class FavoriteItem(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    resource_id: int
    created_at: datetime


class Page(BaseModel):
    total: int
    page: int
    page_size: int


class ProgressPage(Page):
    items: list[ProgressItem]


class FavoritePage(Page):
    items: list[FavoriteItem]


class EventPage(Page):
    items: list[EventReceipt]
