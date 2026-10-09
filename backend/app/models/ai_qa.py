from sqlalchemy import Column, Index, ForeignKeyConstraint, CheckConstraint, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, VARCHAR, CHAR, TEXT, MEDIUMTEXT, DATETIME
from app.database.base import Base


class AIQARecord(Base):
    __tablename__ = 'ai_qa_records'
    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    request_uuid = Column(CHAR(36, charset='ascii', collation='ascii_bin'), nullable=False)
    user_id = Column(BIGINT(unsigned=True), nullable=False)
    mode = Column(VARCHAR(20), nullable=False)
    resource_id = Column(BIGINT(unsigned=True), nullable=True)
    resource_version = Column(INTEGER(unsigned=True), nullable=True)
    request_fingerprint = Column(CHAR(64, charset='ascii', collation='ascii_bin'), nullable=False)
    question = Column(TEXT(), nullable=False)
    answer = Column(MEDIUMTEXT(), nullable=True)
    status = Column(VARCHAR(20), nullable=False, server_default=text("'pending'"))
    provider = Column(VARCHAR(30), nullable=False)
    model = Column(VARCHAR(100), nullable=False)
    prompt_version = Column(VARCHAR(30), nullable=False)
    consent_version = Column(VARCHAR(30), nullable=False)
    provider_request_id = Column(VARCHAR(200), nullable=True)
    input_tokens = Column(INTEGER(unsigned=True), nullable=True)
    output_tokens = Column(INTEGER(unsigned=True), nullable=True)
    latency_ms = Column(INTEGER(unsigned=True), nullable=True)
    error_code = Column(VARCHAR(50), nullable=True)
    created_at = Column(DATETIME(fsp=3), nullable=False)
    finished_at = Column(DATETIME(fsp=3), nullable=True)
    __table_args__ = (
        Index('uk_ai_qa_request_uuid', 'request_uuid', unique=True),
        Index('idx_ai_qa_user_time', 'user_id', 'created_at', 'id'),
        Index('idx_ai_qa_status_time', 'status', 'created_at'),
        Index('fk_ai_qa_resource', 'resource_id'),
        ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_ai_qa_user', ondelete='RESTRICT', onupdate='RESTRICT'),
        ForeignKeyConstraint(['resource_id'], ['resources.id'], name='fk_ai_qa_resource', ondelete='RESTRICT', onupdate='RESTRICT'),
        CheckConstraint("(mode='general' AND resource_id IS NULL AND resource_version IS NULL) OR (mode='resource' AND resource_id IS NOT NULL AND resource_version >= 1)", name='chk_ai_qa_mode'),
        CheckConstraint("status IN ('pending','succeeded','failed','unknown')", name='chk_ai_qa_status'),
        CheckConstraint("status <> 'succeeded' OR (answer IS NOT NULL AND CHAR_LENGTH(TRIM(answer)) > 0)", name='chk_ai_qa_answer'),
        CheckConstraint('CHAR_LENGTH(TRIM(question)) BETWEEN 1 AND 2000', name='chk_ai_qa_question'),
        {'mysql_engine':'InnoDB','mysql_charset':'utf8mb4','mysql_collate':'utf8mb4_unicode_ci'},
    )
