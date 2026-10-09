from sqlalchemy import Column, ForeignKey, CheckConstraint
from sqlalchemy.dialects.mysql import BIGINT, VARCHAR, JSON, CHAR, DATETIME
from app.database.base import Base


class AICourseContext(Base):
    __tablename__ = 'ai_course_contexts'
    qa_record_id = Column(BIGINT(unsigned=True), ForeignKey('ai_qa_records.id', ondelete='RESTRICT', onupdate='RESTRICT'), primary_key=True, autoincrement=False)
    course_title = Column(VARCHAR(200), nullable=False)
    references = Column(JSON, nullable=False)
    context_hash = Column(CHAR(64, charset='ascii', collation='ascii_bin'), nullable=False)
    retrieval_version = Column(VARCHAR(30), nullable=False)
    created_at = Column(DATETIME(fsp=3), nullable=False)
    __table_args__ = (CheckConstraint("JSON_TYPE(`references`) = 'ARRAY' AND JSON_LENGTH(`references`) <= 3", name='ck_ai_course_references'),
                      {'mysql_engine':'InnoDB','mysql_charset':'utf8mb4','mysql_collate':'utf8mb4_unicode_ci'})
