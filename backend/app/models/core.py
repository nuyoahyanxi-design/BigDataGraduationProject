"""Explicit mapping of migration 001. Never call create_all from application startup."""
from sqlalchemy import Column, Index, ForeignKeyConstraint, CheckConstraint, text
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, SMALLINT, TINYINT, VARCHAR, CHAR, JSON, DATETIME, LONGTEXT
from app.database.base import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(BIGINT(unsigned=True), primary_key=True, nullable=False, autoincrement=True)
    username = Column(VARCHAR(50, charset='ascii', collation='ascii_bin'), primary_key=False, nullable=False)
    password_hash = Column(VARCHAR(255), primary_key=False, nullable=False)
    nickname = Column(VARCHAR(50), primary_key=False, nullable=True)
    role = Column(VARCHAR(20, charset='ascii', collation='ascii_bin'), primary_key=False, nullable=False, server_default=text("'learner'"))
    status = Column(VARCHAR(20, charset='ascii', collation='ascii_bin'), primary_key=False, nullable=False, server_default=text("'active'"))
    interest_tags = Column(JSON(), primary_key=False, nullable=False)
    created_at = Column(DATETIME(fsp=3), primary_key=False, nullable=False)
    updated_at = Column(DATETIME(fsp=3), primary_key=False, nullable=False)
    __table_args__ = (
        Index('uk_users_username', 'username', unique=True),
        Index('idx_users_status_role_id', 'status', 'role', 'id'),
        CheckConstraint("role IN ('learner','admin')", name='ck_users_role'),
        CheckConstraint("status IN ('active','disabled','deleted')", name='ck_users_status'),
        CheckConstraint('CHAR_LENGTH(TRIM(username)) > 0 AND BINARY username = BINARY LOWER(username)', name='ck_users_username'),
        CheckConstraint('updated_at >= created_at', name='ck_users_time'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )

class Resource(Base):
    __tablename__ = 'resources'
    id = Column(BIGINT(unsigned=True), primary_key=True, nullable=False, autoincrement=True)
    title = Column(VARCHAR(200), primary_key=False, nullable=False)
    resource_type = Column(VARCHAR(20, charset='ascii', collation='ascii_bin'), primary_key=False, nullable=False)
    category_code = Column(VARCHAR(40, charset='ascii', collation='ascii_bin'), primary_key=False, nullable=False)
    tags = Column(JSON(), primary_key=False, nullable=False)
    difficulty = Column(TINYINT(unsigned=True), primary_key=False, nullable=False, server_default=text('1'))
    summary = Column(VARCHAR(1000), primary_key=False, nullable=False)
    content = Column(LONGTEXT(), primary_key=False, nullable=True)
    content_url = Column(VARCHAR(1000), primary_key=False, nullable=True)
    source_name = Column(VARCHAR(255), primary_key=False, nullable=True)
    license_note = Column(VARCHAR(500), primary_key=False, nullable=True)
    status = Column(VARCHAR(20, charset='ascii', collation='ascii_bin'), primary_key=False, nullable=False, server_default=text("'draft'"))
    version_no = Column(INTEGER(unsigned=True), primary_key=False, nullable=False, server_default=text('1'))
    created_by = Column(BIGINT(unsigned=True), primary_key=False, nullable=False)
    published_at = Column(DATETIME(fsp=3), primary_key=False, nullable=True)
    created_at = Column(DATETIME(fsp=3), primary_key=False, nullable=False)
    updated_at = Column(DATETIME(fsp=3), primary_key=False, nullable=False)
    __table_args__ = (
        Index('idx_resources_status_category_id', 'status', 'category_code', 'id'),
        Index('idx_resources_status_id', 'status', 'id'),
        Index('idx_resources_updated_id', 'updated_at', 'id'),
        Index('idx_resources_created_by', 'created_by'),
        ForeignKeyConstraint(['created_by'], ['users.id'], name='fk_resources_creator', ondelete="RESTRICT", onupdate="RESTRICT"),
        CheckConstraint("resource_type IN ('document','course','exercise')", name='ck_resources_type'),
        CheckConstraint("status IN ('draft','published','offline','deleted')", name='ck_resources_status'),
        CheckConstraint('difficulty BETWEEN 1 AND 3', name='ck_resources_difficulty'),
        CheckConstraint('version_no >= 1', name='ck_resources_version'),
        CheckConstraint('CHAR_LENGTH(TRIM(title)) > 0 AND CHAR_LENGTH(TRIM(summary)) > 0', name='ck_resources_text'),
        CheckConstraint('updated_at >= created_at', name='ck_resources_time'),
        CheckConstraint("status <> 'published' OR (published_at IS NOT NULL AND JSON_TYPE(tags) = 'ARRAY' AND JSON_LENGTH(tags) > 0 AND (COALESCE(CHAR_LENGTH(TRIM(content)),0) > 0 OR COALESCE(CHAR_LENGTH(TRIM(content_url)),0) > 0))", name='ck_resources_published'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )

class LearningProgress(Base):
    __tablename__ = 'learning_progress'
    user_id = Column(BIGINT(unsigned=True), primary_key=True, nullable=False, autoincrement=False)
    resource_id = Column(BIGINT(unsigned=True), primary_key=True, nullable=False, autoincrement=False)
    status = Column(VARCHAR(20, charset='ascii', collation='ascii_bin'), primary_key=False, nullable=False, server_default=text("'in_progress'"))
    first_started_at = Column(DATETIME(fsp=3), primary_key=False, nullable=False)
    completed_at = Column(DATETIME(fsp=3), primary_key=False, nullable=True)
    updated_at = Column(DATETIME(fsp=3), primary_key=False, nullable=False)
    __table_args__ = (
        Index('idx_progress_user_status_updated', 'user_id', 'status', 'updated_at', 'resource_id'),
        Index('idx_progress_resource_user', 'resource_id', 'user_id'),
        ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_progress_user', ondelete="RESTRICT", onupdate="RESTRICT"),
        ForeignKeyConstraint(['resource_id'], ['resources.id'], name='fk_progress_resource', ondelete="RESTRICT", onupdate="RESTRICT"),
        CheckConstraint("status IN ('in_progress','completed')", name='ck_progress_status'),
        CheckConstraint("(status = 'in_progress' AND completed_at IS NULL) OR (status = 'completed' AND completed_at IS NOT NULL AND completed_at >= first_started_at)", name='ck_progress_completion'),
        CheckConstraint('updated_at >= first_started_at', name='ck_progress_time'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )

class Favorite(Base):
    __tablename__ = 'favorites'
    user_id = Column(BIGINT(unsigned=True), primary_key=True, nullable=False, autoincrement=False)
    resource_id = Column(BIGINT(unsigned=True), primary_key=True, nullable=False, autoincrement=False)
    created_at = Column(DATETIME(fsp=3), primary_key=False, nullable=False)
    __table_args__ = (
        Index('idx_favorites_user_created', 'user_id', 'created_at', 'resource_id'),
        Index('idx_favorites_resource_user', 'resource_id', 'user_id'),
        ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_favorites_user', ondelete="RESTRICT", onupdate="RESTRICT"),
        ForeignKeyConstraint(['resource_id'], ['resources.id'], name='fk_favorites_resource', ondelete="RESTRICT", onupdate="RESTRICT"),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )

class LearningEvent(Base):
    __tablename__ = 'learning_events'
    id = Column(BIGINT(unsigned=True), primary_key=True, nullable=False, autoincrement=True)
    event_uuid = Column(CHAR(36, charset='ascii', collation='ascii_bin'), primary_key=False, nullable=False)
    user_id = Column(BIGINT(unsigned=True), primary_key=False, nullable=False)
    resource_id = Column(BIGINT(unsigned=True), primary_key=False, nullable=False)
    event_type = Column(VARCHAR(32, charset='ascii', collation='ascii_bin'), primary_key=False, nullable=False)
    event_source = Column(VARCHAR(16, charset='ascii', collation='ascii_bin'), primary_key=False, nullable=False)
    schema_version = Column(SMALLINT(unsigned=True), primary_key=False, nullable=False, server_default=text('1'))
    resource_version = Column(INTEGER(unsigned=True), primary_key=False, nullable=False)
    session_id = Column(CHAR(36, charset='ascii', collation='ascii_bin'), primary_key=False, nullable=True)
    occurred_at = Column(DATETIME(fsp=3), primary_key=False, nullable=False)
    received_at = Column(DATETIME(fsp=3), primary_key=False, nullable=False)
    client_occurred_at = Column(DATETIME(fsp=3), primary_key=False, nullable=True)
    is_effective = Column(TINYINT(unsigned=True), primary_key=False, nullable=False)
    state_before = Column(VARCHAR(20, charset='ascii', collation='ascii_bin'), primary_key=False, nullable=True)
    state_after = Column(VARCHAR(20, charset='ascii', collation='ascii_bin'), primary_key=False, nullable=True)
    request_fingerprint = Column(CHAR(64, charset='ascii', collation='ascii_bin'), primary_key=False, nullable=False)
    __table_args__ = (
        Index('uk_events_uuid', 'event_uuid', unique=True),
        Index('idx_events_user_resource_time', 'user_id', 'resource_id', 'occurred_at', 'id'),
        Index('idx_events_user_time', 'user_id', 'occurred_at', 'id'),
        Index('idx_events_resource_time', 'resource_id', 'occurred_at', 'id'),
        Index('idx_events_received_id', 'received_at', 'id'),
        ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_events_user', ondelete="RESTRICT", onupdate="RESTRICT"),
        ForeignKeyConstraint(['resource_id'], ['resources.id'], name='fk_events_resource', ondelete="RESTRICT", onupdate="RESTRICT"),
        CheckConstraint("event_type IN ('resource_view','learning_start','learning_complete','favorite_add','favorite_remove')", name='ck_events_type'),
        CheckConstraint("event_source IN ('client','server')", name='ck_events_source'),
        CheckConstraint('schema_version >= 1 AND resource_version >= 1', name='ck_events_versions'),
        CheckConstraint('is_effective IN (0,1)', name='ck_events_effective'),
        CheckConstraint('occurred_at >= received_at', name='ck_events_time'),
        CheckConstraint("(event_type = 'resource_view' AND event_source = 'client' AND is_effective = 1 AND session_id IS NOT NULL AND state_before IS NULL AND state_after IS NULL) OR (event_source = 'server' AND client_occurred_at IS NULL AND state_before IS NOT NULL AND state_after IS NOT NULL AND ( (event_type = 'learning_start' AND ((is_effective = 1 AND state_before = 'not_started' AND state_after = 'in_progress') OR (is_effective = 0 AND state_before = state_after AND state_before IN ('in_progress','completed')))) OR (event_type = 'learning_complete' AND ((is_effective = 1 AND state_before = 'in_progress' AND state_after = 'completed') OR (is_effective = 0 AND state_before = 'completed' AND state_after = 'completed'))) OR (event_type = 'favorite_add' AND ((is_effective = 1 AND state_before = 'not_favorited' AND state_after = 'favorited') OR (is_effective = 0 AND state_before = 'favorited' AND state_after = 'favorited'))) OR (event_type = 'favorite_remove' AND ((is_effective = 1 AND state_before = 'favorited' AND state_after = 'not_favorited') OR (is_effective = 0 AND state_before = 'not_favorited' AND state_after = 'not_favorited'))) ))", name='ck_events_semantics'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )

