from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Index
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, VARCHAR, LONGTEXT, JSON, DATETIME, CHAR, TINYINT, DECIMAL
from app.database.base import Base

class CourseChapter(Base):
    __tablename__ = 'course_chapters'
    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    resource_id = Column(BIGINT(unsigned=True), ForeignKey('resources.id'), nullable=False)
    title = Column(VARCHAR(200), nullable=False)
    position = Column(INTEGER(unsigned=True), nullable=False)
    content = Column(LONGTEXT, nullable=False)
    learning_objectives = Column(JSON)
    example_code = Column(LONGTEXT)
    exercises = Column(JSON)
    knowledge_tags = Column(JSON, nullable=False)
    video_name = Column(VARCHAR(200))
    video_url = Column(VARCHAR(500))
    video_cover = Column(VARCHAR(500))
    video_duration_seconds = Column(INTEGER(unsigned=True))
    video_position = Column(INTEGER(unsigned=True), nullable=False, default=1)
    created_at = Column(DATETIME(fsp=3), nullable=False)
    __table_args__ = (Index('uk_chapter_position', 'resource_id', 'position', unique=True),
                      Index('uk_chapter_resource', 'id', 'resource_id', unique=True))

class ChapterProgress(Base):
    __tablename__ = 'chapter_progress'
    user_id = Column(BIGINT(unsigned=True), ForeignKey('users.id'), primary_key=True, autoincrement=False)
    chapter_id = Column(BIGINT(unsigned=True), ForeignKey('course_chapters.id'), primary_key=True, autoincrement=False)
    first_started_at = Column(DATETIME(fsp=3), nullable=False)
    completed_at = Column(DATETIME(fsp=3))

class ChapterEvent(Base):
    __tablename__ = 'chapter_events'
    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    event_uuid = Column(CHAR(36, charset='ascii', collation='ascii_bin'), nullable=False, unique=True)
    user_id = Column(BIGINT(unsigned=True), ForeignKey('users.id'), nullable=False)
    resource_id = Column(BIGINT(unsigned=True), nullable=False)
    chapter_id = Column(BIGINT(unsigned=True), nullable=False)
    event_type = Column(VARCHAR(32), nullable=False)
    occurred_at = Column(DATETIME(fsp=3), nullable=False)
    playback_seconds = Column(DECIMAL(10,3))
    is_effective = Column(TINYINT(unsigned=True), nullable=False)
    request_fingerprint = Column(CHAR(64), nullable=False)
    result = Column(JSON, nullable=False)
    __table_args__ = (ForeignKeyConstraint(['chapter_id','resource_id'], ['course_chapters.id','course_chapters.resource_id']),)
