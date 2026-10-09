"""Read mappings for the already migrated Spark result tables; no DDL."""
from sqlalchemy import Column, Index, ForeignKeyConstraint, CheckConstraint, PrimaryKeyConstraint
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, VARCHAR, JSON, DATETIME, DECIMAL
from app.database.base import Base


class UserProfile(Base):
    __tablename__ = 'user_profiles'
    user_id = Column(BIGINT(unsigned=True), primary_key=True, nullable=False)
    batch_id = Column(VARCHAR(64, charset='ascii', collation='ascii_bin'), primary_key=True, nullable=False)
    generated_at = Column(DATETIME(fsp=3), nullable=False)
    interest_profile = Column(JSON(), nullable=False)
    activity_profile = Column(JSON(), nullable=False)
    learning_preference = Column(JSON(), nullable=False)
    metric_explanations = Column(JSON(), nullable=False)
    __table_args__ = (
        Index('idx_profiles_batch', 'batch_id'),
        ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_profiles_user', ondelete='RESTRICT', onupdate='RESTRICT'),
        CheckConstraint("JSON_TYPE(interest_profile)='OBJECT'", name='chk_profiles_interest'),
        CheckConstraint("JSON_TYPE(activity_profile)='OBJECT'", name='chk_profiles_activity'),
        CheckConstraint("JSON_TYPE(learning_preference)='OBJECT'", name='chk_profiles_preference'),
        CheckConstraint("JSON_TYPE(metric_explanations)='OBJECT'", name='chk_profiles_explanations'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )


class RecommendationResult(Base):
    __tablename__ = 'recommendation_results'
    user_id = Column(BIGINT(unsigned=True), primary_key=True, nullable=False)
    resource_id = Column(BIGINT(unsigned=True), primary_key=True, nullable=False)
    batch_id = Column(VARCHAR(64, charset='ascii', collation='ascii_bin'), primary_key=True, nullable=False)
    algorithm = Column(VARCHAR(32, charset='ascii', collation='ascii_bin'), primary_key=True, nullable=False)
    score = Column(DECIMAL(24, 12), nullable=False)
    rank = Column(INTEGER(unsigned=True), nullable=False)
    reason = Column(VARCHAR(1000), nullable=False)
    __table_args__ = (
        PrimaryKeyConstraint('user_id', 'batch_id', 'algorithm', 'resource_id'),
        Index('uq_recommendation_rank', 'user_id', 'batch_id', 'algorithm', 'rank', unique=True),
        Index('idx_recommendation_batch', 'batch_id'),
        Index('fk_recommendation_resource', 'resource_id'),
        ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_recommendation_user', ondelete='RESTRICT', onupdate='RESTRICT'),
        ForeignKeyConstraint(['resource_id'], ['resources.id'], name='fk_recommendation_resource', ondelete='RESTRICT', onupdate='RESTRICT'),
        CheckConstraint("algorithm IN ('popular_v1','content_v1')", name='chk_recommendation_algorithm'),
        CheckConstraint("score >= 0 AND (algorithm <> 'content_v1' OR score <= 1)", name='chk_recommendation_score'),
        CheckConstraint('`rank` >= 1', name='chk_recommendation_rank'),
        CheckConstraint('CHAR_LENGTH(TRIM(reason)) > 0', name='chk_recommendation_reason'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )
