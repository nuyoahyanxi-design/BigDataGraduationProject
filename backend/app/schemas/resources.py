import ipaddress
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.users import InputModel, Tag, INTEREST_TAGS

CATEGORIES=frozenset({'python-basics','java-basics','databases','data-engineering',
                      'machine-learning','web-development','algorithms'})
ResourceType=Literal['document','course','exercise']


class ResourceWrite(InputModel):
    title: str = Field(min_length=1,max_length=200,strict=True)
    resource_type: ResourceType
    category_code: str = Field(max_length=40,strict=True)
    tags: list[Tag] = Field(default_factory=list,max_length=10,strict=True)
    difficulty: int = Field(default=1,ge=1,le=3,strict=True)
    summary: str = Field(min_length=1,max_length=1000,strict=True)
    content: str | None = Field(default=None,max_length=100000,strict=True)
    content_url: str | None = Field(default=None,max_length=1000,strict=True)
    source_name: str | None = Field(default=None,max_length=255,strict=True)
    license_note: str | None = Field(default=None,max_length=500,strict=True)

    @field_validator('title','summary',mode='before')
    @classmethod
    def required_text(cls,value):
        if not isinstance(value,str) or not value.strip():
            raise ValueError('Text cannot be blank')
        return value.strip()

    @field_validator('category_code')
    @classmethod
    def category(cls,value):
        if value not in CATEGORIES:
            raise ValueError('Unsupported category')
        return value

    @field_validator('tags')
    @classmethod
    def valid_tags(cls,value):
        if len(set(value))!=len(value) or any(tag not in INTEREST_TAGS for tag in value):
            raise ValueError('Tags must be unique supported codes')
        return value

    @field_validator('content_url')
    @classmethod
    def external_url(cls,value):
        if value is None:
            return None
        if any(c.isspace() or ord(c)<32 for c in value) or '\\' in value:
            raise ValueError('Invalid URL')
        try:
            url=urlsplit(value)
            host=url.hostname
            _=url.port
            if url.scheme not in ('http','https') or not host or url.username is not None or url.password is not None or url.fragment:
                raise ValueError('Invalid public HTTP URL')
            if host.lower().rstrip('.')=='localhost' or host.lower().endswith(('.localhost','.local')):
                raise ValueError('Local URL not permitted')
            try:
                address=ipaddress.ip_address(host)
            except ValueError:
                address=None
            if address is not None and not address.is_global:
                raise ValueError('Private URL not permitted')
        except ValueError:
            raise ValueError('Invalid public HTTP URL') from None
        return value


class ResourceStatus(InputModel):
    status: Literal['published','offline']


class ResourceSummary(BaseModel):
    display_type: ResourceType | None = None
    model_config=ConfigDict(from_attributes=True)
    id: int
    title: str
    resource_type: ResourceType
    category_code: str
    tags: list[str]
    difficulty: int
    summary: str
    source_name: str | None
    license_note: str | None
    status: Literal['draft','published','offline','deleted']
    version_no: int
    created_by: int
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ResourceDetail(ResourceSummary):
    content: str | None
    content_url: str | None


class ResourceList(BaseModel):
    items: list[ResourceSummary]
    total: int
    page: int
    page_size: int
