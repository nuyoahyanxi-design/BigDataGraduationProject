"""Presentation visibility and chapter-derived status; no stored data mutation."""
from sqlalchemy import select, func, case, and_,not_
from app.models import Resource, CourseChapter, ChapterProgress, LearningProgress

from app.core.resource_scope import HIDDEN_IDS,VALIDATION_SOURCE,VALIDATION_LICENSE
HIDDEN_LEARNER_RESOURCE_IDS = HIDDEN_IDS

def visible_resource_clause():
    validation=func.coalesce(and_(Resource.source_name==VALIDATION_SOURCE,Resource.license_note==VALIDATION_LICENSE),False)
    return and_(Resource.id.not_in(HIDDEN_LEARNER_RESOURCE_IDS),not_(validation))

def formal_course_clause():
    chapters=select(CourseChapter.id).where(CourseChapter.resource_id==Resource.id).exists()
    return and_(Resource.status=='published',visible_resource_clause(),chapters)

def chapter_status(completed, total, started=0):
    return 'completed' if total and completed == total else 'in_progress' if started or completed else 'not_started'

def effective_progress_status(user_id):
    total = select(func.count()).select_from(CourseChapter).where(
        CourseChapter.resource_id == LearningProgress.resource_id).correlate(LearningProgress).scalar_subquery()
    completed = select(func.count()).select_from(ChapterProgress).join(CourseChapter).where(
        CourseChapter.resource_id == LearningProgress.resource_id,
        ChapterProgress.user_id == user_id, ChapterProgress.completed_at.is_not(None)
    ).correlate(LearningProgress).scalar_subquery()
    started = select(func.count()).select_from(ChapterProgress).join(CourseChapter).where(
        CourseChapter.resource_id == LearningProgress.resource_id, ChapterProgress.user_id == user_id
    ).correlate(LearningProgress).scalar_subquery()
    return case((total == 0, LearningProgress.status), (completed == total, 'completed'),
                (started > 0, 'in_progress'), else_='not_started')

def effective_progress_time(user_id, field):
    total=select(func.count()).select_from(CourseChapter).where(CourseChapter.resource_id==LearningProgress.resource_id).correlate(LearningProgress).scalar_subquery()
    col=ChapterProgress.completed_at if field=='completed_at' else ChapterProgress.first_started_at
    aggregate=func.max(func.coalesce(ChapterProgress.completed_at,ChapterProgress.first_started_at)) if field=='updated_at' else func.max(col) if field=='completed_at' else func.min(col)
    value=select(aggregate).select_from(ChapterProgress).join(CourseChapter).where(CourseChapter.resource_id==LearningProgress.resource_id,ChapterProgress.user_id==user_id).correlate(LearningProgress).scalar_subquery()
    if field=='completed_at':
        value=case((effective_progress_status(user_id)=='completed',value),else_=None)
    return case((total==0,getattr(LearningProgress,field)),else_=value)
