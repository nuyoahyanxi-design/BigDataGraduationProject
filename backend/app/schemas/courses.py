from typing import Literal
from pydantic import Field, UUID4, field_validator
from app.schemas.users import InputModel

def local_asset(value, folder):
    if value is None: return value
    if folder=='videos' and value=='/demo/video.mp4': return value
    import re
    extensions='mp4|webm' if folder=='videos' else 'png|jpg|jpeg|webp'
    if not re.fullmatch(r'/' + folder + r'/[a-zA-Z0-9_/-]+\.(' + extensions + ')', value) or '..' in value:
        raise ValueError('Only local static assets are supported')
    return value

class ChapterWrite(InputModel):
    title: str = Field(min_length=1,max_length=200)
    position: int = Field(ge=1,le=1000)
    content: str = Field(min_length=1,max_length=100000)
    knowledge_tags: list[str] = Field(max_length=20)
    learning_objectives: list[str] = Field(default_factory=list,max_length=8)
    example_code: str | None = Field(default=None,max_length=10000)
    exercises: list[str] = Field(default_factory=list,max_length=8)
    video_name: str | None = Field(default=None,max_length=200)
    video_url: str | None = Field(default=None,max_length=500)
    video_cover: str | None = Field(default=None,max_length=500)
    video_duration_seconds: int | None = Field(default=None,ge=1,le=86400)
    video_position: int = Field(default=1,ge=1,le=1000)
    @field_validator('title','content')
    @classmethod
    def nonblank(cls,value):
        if not value.strip(): raise ValueError('Text cannot be empty')
        return value.strip()
    @field_validator('knowledge_tags')
    @classmethod
    def tags(cls,value):
        if any(not tag.strip() or len(tag)>50 for tag in value) or len(set(value))!=len(value):
            raise ValueError('Invalid knowledge tags')
        return value
    @field_validator('learning_objectives','exercises')
    @classmethod
    def teaching_items(cls,value):
        if any(not item.strip() or len(item)>1000 for item in value):
            raise ValueError('Teaching items must be nonblank and at most 1000 characters')
        return [item.strip() for item in value]
    @field_validator('video_url')
    @classmethod
    def video(cls,value): return local_asset(value,'videos')
    @field_validator('video_cover')
    @classmethod
    def cover(cls,value): return local_asset(value,'images')

class ChapterAction(InputModel):
    event_uuid: UUID4
    event_type: Literal['chapter_view','video_play','chapter_complete']
    playback_seconds: float | None = Field(default=None,ge=0,le=86400,allow_inf_nan=False)
