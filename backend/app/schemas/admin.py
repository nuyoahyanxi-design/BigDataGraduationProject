from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict


class AdminUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: Literal['admin','learner']
    status: Literal['active','disabled','deleted']
    created_at: datetime


class AdminUsers(BaseModel):
    items: list[AdminUser]
    total: int
    page: int
    page_size: int


class BatchInfo(BaseModel):
    stage: str
    batch_id: str | None = None
    status: str
    generated_at: str | None = None
    as_of_utc: str | None = None
    data_count: int | None = None
    count_label: str
    source: str
    message: str | None = None


class BatchList(BaseModel):
    items: list[BatchInfo]
    scope: str = '各阶段最近发布批次；不是完整运行历史'


from pydantic import Field
from app.schemas.resources import ResourceSummary

class AdminCourseSummary(ResourceSummary):
    chapter_count: int = Field(ge=0)

class AdminCourses(BaseModel):
    items: list[AdminCourseSummary]
    total: int
    page: int
    page_size: int
