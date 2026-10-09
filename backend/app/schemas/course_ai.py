from pydantic import Field, UUID4, field_validator
from app.schemas.users import InputModel
from app.schemas.ai_assistant import Question, Record
from typing import Literal


class CourseQuestion(InputModel):
    request_uuid: UUID4
    question: str = Field(min_length=1, max_length=2000)
    chapter_id: int | None = Field(default=None, ge=1, le=18446744073709551615)
    consent_version: Literal['agnes-external-v1']

    @field_validator('question')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('Blank question')
        return value.strip()

    def existing_question(self, course_id):
        return Question(request_uuid=self.request_uuid, question=self.question, mode='resource',
                        resource_id=course_id, consent_version=self.consent_version)


class Reference(InputModel):
    course_name: str
    chapter_name: str
    chapter_id: int
    position: int


class CourseRecord(Record):
    course_id: int
    course_title: str | None
    references: list[Reference]
    retrieval_version: str


class CourseHistory(InputModel):
    items: list[CourseRecord]
    total: int
    page: int
    page_size: int
