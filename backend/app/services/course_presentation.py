"""Presentation visibility and chapter-derived status; no stored data mutation."""
from sqlalchemy import select, func, case
from app.models import Resource, CourseChapter, ChapterProgress, LearningProgress

HIDDEN_LEARNER_RESOURCE_IDS = frozenset({406})

def visible_resource_clause():
    return Resource.id.not_in(HIDDEN_LEARNER_RESOURCE_IDS)

def chapter_status(completed, total):
    return 'completed' if total and completed == total else 'in_progress' if completed else 'not_started'

def effective_progress_status(user_id):
    total = select(func.count()).select_from(CourseChapter).where(
        CourseChapter.resource_id == LearningProgress.resource_id).correlate(LearningProgress).scalar_subquery()
    completed = select(func.count()).select_from(ChapterProgress).join(CourseChapter).where(
        CourseChapter.resource_id == LearningProgress.resource_id,
        ChapterProgress.user_id == user_id, ChapterProgress.completed_at.is_not(None)
    ).correlate(LearningProgress).scalar_subquery()
    return case((total == 0, LearningProgress.status), (completed == 0, 'not_started'),
                (completed == total, 'completed'), else_='in_progress')
