import json
import os
from pathlib import Path
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from app.models import Resource, LearningProgress, UserProfile, RecommendationResult
from app.schemas.resources import ResourceSummary
from app.schemas.recommendations import Publication, ProfileSummary, RecommendationItem, RecommendationsResponse


from app.services.course_presentation import visible_resource_clause, effective_progress_status

DEFAULT_MANIFEST = Path(__file__).resolve().parents[3] / 'outputs/recommendation-latest.json'


def load_publication():
    path = Path(os.environ.get('RECOMMENDATION_MANIFEST_PATH') or DEFAULT_MANIFEST)
    try:
        # Bound input and read once: Spark atomically replaces the pointer.
        with path.open('rb') as stream:
            raw = stream.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError('Manifest too large')
        publication = Publication.model_validate(json.loads(raw))
        if publication.as_of_utc > publication.generated_at:
            raise ValueError('Invalid batch timeline')
        return publication
    except FileNotFoundError:
        return None
    except (OSError, ValueError, ValidationError):
        raise HTTPException(503, 'Recommendation publication unavailable') from None


def summarize_profile(row, publication):
    try:
        # Use the matched snapshot time rather than a separate profile-latest pointer.
        result = ProfileSummary(
            batch_id=row.batch_id, generated_at=row.generated_at,
            as_of_utc=row.metric_explanations['as_of_utc'],
            interest_weights=row.interest_profile['weights'],
            evidence=row.interest_profile['evidence'],
            event_counts=row.activity_profile['event_counts'],
            active_days=row.activity_profile['active_days'],
            started_resources=row.learning_preference['started_resources'],
            completed_resources=row.learning_preference['completed_resources'],
            completion_rate=row.learning_preference['completion_rate'],
        )
        if result.as_of_utc != publication.as_of_utc:
            raise ValueError('Profile snapshot mismatch')
        return result
    except (KeyError, TypeError, ValueError, ValidationError):
        raise HTTPException(503, 'Recommendation profile unavailable') from None


def recommendations_for_user(db, user, algorithm):
    publication = load_publication()
    if publication is None:
        return RecommendationsResponse(batch_id=None, generated_at=None, as_of_utc=None,
            algorithm=algorithm, items=[], profile=None, explicit_interest_tags=user.interest_tags,
            message='尚无已发布推荐批次，请先浏览学习资源')
    profile_row = db.get(UserProfile, (user.id, publication.profile_batch_id))
    profile = summarize_profile(profile_row, publication) if profile_row is not None else None
    completed = select(LearningProgress.resource_id).where(
        LearningProgress.user_id == user.id, effective_progress_status(user.id) == 'completed')
    query = select(RecommendationResult, Resource).join(Resource, Resource.id == RecommendationResult.resource_id).where(
        RecommendationResult.user_id == user.id,
        RecommendationResult.batch_id == publication.batch_id,
        RecommendationResult.algorithm == algorithm,
        Resource.status == 'published', visible_resource_clause(), Resource.id.not_in(completed)
    ).order_by(RecommendationResult.rank.asc(), RecommendationResult.resource_id.asc())
    items = [RecommendationItem(resource_id=result.resource_id,
        resource=ResourceSummary.model_validate(resource), algorithm=result.algorithm,
        score=format(result.score, 'f'), rank=result.rank, reason=result.reason)
        for result, resource in db.execute(query).all()]
    return RecommendationsResponse(batch_id=publication.batch_id, generated_at=publication.generated_at,
        as_of_utc=publication.as_of_utc, algorithm=algorithm, items=items, profile=profile,
        explicit_interest_tags=user.interest_tags,
        message=None if items else '暂无可展示的推荐，可先浏览学习资源并等待下一批生成')
