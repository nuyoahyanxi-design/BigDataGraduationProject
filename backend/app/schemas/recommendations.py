from datetime import datetime, timezone
from typing import Annotated, Literal
from pydantic import BaseModel, Field, field_validator
from app.schemas.resources import ResourceSummary

Algorithm = Literal['content_v1', 'popular_v1']
Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]


def utc(value: datetime):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class Publication(BaseModel):
    scope_rule: str | None = None
    status: Literal['completed']
    mysql_publication: Literal['passed']
    batch_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    profile_batch_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    generated_at: datetime
    as_of_utc: datetime
    normalize_time = field_validator('generated_at', 'as_of_utc')(utc)


class EventCounts(BaseModel):
    resource_view: int = Field(ge=0)
    learning_start: int = Field(ge=0)
    learning_complete: int = Field(ge=0)
    favorite_add: int = Field(ge=0)
    favorite_remove: int = Field(ge=0)


class ChapterActivity(BaseModel):
    chapter_views: int = Field(ge=0)
    video_plays: int = Field(ge=0)
    viewed_chapters: int = Field(ge=0)
    played_chapters: int = Field(ge=0)
    completed_chapters: int = Field(ge=0)


class ProfileSummary(BaseModel):
    scope_label: str | None = None
    chapter_activity: ChapterActivity | None = None
    batch_id: str
    generated_at: datetime
    as_of_utc: datetime
    interest_weights: dict[str, Nonnegative]
    evidence: Literal['observed', 'explicit_only', 'no_evidence']
    event_counts: EventCounts
    active_days: int = Field(ge=0)
    started_resources: int = Field(ge=0)
    completed_resources: int = Field(ge=0)
    completion_rate: float | None = Field(ge=0, le=1)
    normalize_time = field_validator('generated_at', 'as_of_utc')(utc)


class RecommendationItem(BaseModel):
    resource_id: int
    resource: ResourceSummary
    algorithm: Algorithm
    score: str
    rank: int
    reason: str


class RecommendationsResponse(BaseModel):
    batch_id: str | None
    generated_at: datetime | None
    as_of_utc: datetime | None
    algorithm: Algorithm
    items: list[RecommendationItem]
    profile: ProfileSummary | None
    explicit_interest_tags: list[str]
    message: str | None
