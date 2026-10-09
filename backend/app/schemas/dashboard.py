from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator
from app.schemas.recommendations import utc

class DailyMetric(BaseModel):
    day: str
    resource_view: int = Field(ge=0)
    learning_start: int = Field(ge=0)
    learning_complete: int = Field(ge=0)
    favorite_add: int = Field(ge=0)
    favorite_remove: int = Field(ge=0)

class UsersMetric(BaseModel):
    total: int = Field(ge=0)
    active_learners: int = Field(ge=0)
    admins: int = Field(ge=0)

class ResourcesMetric(BaseModel):
    total: int = Field(ge=0)
    published: int = Field(ge=0)

class CategoryMetric(BaseModel):
    category: str
    count: int = Field(ge=0)

class BehaviorMetric(BaseModel):
    total_effective_events: int = Field(ge=0)
    window_events: int = Field(ge=0)
    daily: list[DailyMetric]
    timezone: Literal['Asia/Shanghai']
    window_days: Literal[30]

class LearningMetric(BaseModel):
    started_pairs: int = Field(ge=0)
    in_progress: int = Field(ge=0)
    completed: int = Field(ge=0)
    completion_rate: float | None = Field(ge=0, le=1)

class Metrics(BaseModel):
    users: UsersMetric
    resources: ResourcesMetric
    resource_categories: list[CategoryMetric]
    behavior: BehaviorMetric
    learning: LearningMetric

class PairedPublication(BaseModel):
    batch_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    profile_batch_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    generated_at: datetime
    as_of_utc: datetime
    normalize = field_validator('generated_at','as_of_utc')(utc)

class DashboardArtifact(BaseModel):
    status: Literal['completed']
    batch_id: str
    source_batch_id: str
    generated_at: datetime
    as_of_utc: datetime
    source: str
    dataset_origin: str
    spark_version: str
    metrics: Metrics
    quality: dict[str, int]
    recommendation_publication: PairedPublication | None
    normalize = field_validator('generated_at','as_of_utc')(utc)

class ProfilesMetric(BaseModel):
    source: str = 'MySQL user_profiles, matched Spark batch'
    batch_id: str | None
    users: int
    evidence: dict[str, int]

class RecommendationMetric(BaseModel):
    algorithm: str
    rows: int
    users: int
    resources: int

class RecommendationStats(BaseModel):
    source: str = 'MySQL recommendation_results, matched published batch'
    batch_id: str | None
    generated_at: datetime | None
    rows: int
    algorithms: list[RecommendationMetric]

class DashboardResponse(BaseModel):
    available: bool
    data: DashboardArtifact | None
    profiles: ProfilesMetric | None
    recommendations: RecommendationStats | None
    message: str | None
