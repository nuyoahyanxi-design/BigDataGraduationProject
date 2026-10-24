import hashlib
import json
import os
from pathlib import Path
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select, func
from app.models import UserProfile, RecommendationResult, Resource
from app.services.course_presentation import visible_resource_clause, HIDDEN_LEARNER_RESOURCE_IDS
from app.schemas.dashboard import DashboardArtifact, DashboardResponse, ProfilesMetric, RecommendationStats, RecommendationMetric

DEFAULT_DASHBOARD = Path(__file__).resolve().parents[3]/'outputs/dashboard-latest.json'


def load_dashboard():
    path = Path(os.environ.get('DASHBOARD_MANIFEST_PATH') or DEFAULT_DASHBOARD)
    try:
        with path.open('rb') as stream: raw = stream.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024: raise ValueError('Artifact too large')
        value = json.loads(raw)
        record = {k:v for k,v in value.items() if k not in ['status','content_sha256','files','parquet_round_trip']}
        canonical = json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
        if hashlib.sha256(canonical.encode()).hexdigest() != value['content_sha256']:
            raise ValueError('Dashboard checksum mismatch')
        artifact = DashboardArtifact.model_validate(value)
        if artifact.recommendation_publication and artifact.recommendation_publication.as_of_utc != artifact.as_of_utc:
            raise ValueError('Paired batch cutoff differs')
        if artifact.generated_at < artifact.as_of_utc: raise ValueError('Invalid batch timeline')
        return artifact
    except FileNotFoundError: return None
    except (OSError, ValueError, KeyError, TypeError, ValidationError):
        raise HTTPException(503,'Dashboard publication unavailable') from None


def overview(db):
    artifact = load_dashboard()
    if artifact is None:
        return DashboardResponse(available=False,data=None,profiles=None,recommendations=None,
            message='尚无已发布的Spark看板统计，请先运行统计任务')
    if artifact.metrics.learning.scope_label is None:
        # Resource visibility is current online presentation; Spark artifacts remain immutable.
        artifact.metrics.resources.total = db.scalar(select(func.count()).select_from(Resource).where(Resource.status!='deleted',visible_resource_clause()))
        artifact.metrics.resources.published = db.scalar(select(func.count()).select_from(Resource).where(Resource.status=='published',visible_resource_clause()))
        from app.schemas.dashboard import CategoryMetric
        artifact.metrics.resource_categories = [CategoryMetric(category=category,count=count) for category,count in db.execute(
            select(Resource.category_code,func.count()).where(Resource.status=='published',visible_resource_clause()).group_by(Resource.category_code).order_by(Resource.category_code))]
        artifact.source += '; resources/categories: current MySQL, excludes demonstration resource 406 (not Spark snapshot)'
    paired = artifact.recommendation_publication
    profiles = ProfilesMetric(batch_id=None, users=0, evidence={})
    recommendations = RecommendationStats(batch_id=None,generated_at=None,rows=0,algorithms=[])
    if paired:
        profiles.batch_id = paired.profile_batch_id
        profiles.users = db.scalar(select(func.count()).select_from(UserProfile).where(UserProfile.batch_id==paired.profile_batch_id))
        evidence = func.json_unquote(func.json_extract(UserProfile.interest_profile,'$.evidence'))
        profiles.evidence = {kind:count for kind,count in db.execute(select(evidence,func.count()).where(UserProfile.batch_id==paired.profile_batch_id).group_by(evidence)) if kind is not None}
        rows = db.execute(select(RecommendationResult.algorithm,func.count(),func.count(func.distinct(RecommendationResult.user_id)),func.count(func.distinct(RecommendationResult.resource_id))).where(RecommendationResult.batch_id==paired.batch_id, RecommendationResult.resource_id.not_in(HIDDEN_LEARNER_RESOURCE_IDS)).group_by(RecommendationResult.algorithm).order_by(RecommendationResult.algorithm)).all()
        recommendations = RecommendationStats(batch_id=paired.batch_id,generated_at=paired.generated_at,
            rows=db.scalar(select(func.count()).select_from(RecommendationResult).where(RecommendationResult.batch_id==paired.batch_id, RecommendationResult.resource_id.not_in(HIDDEN_LEARNER_RESOURCE_IDS))),
            algorithms=[RecommendationMetric(algorithm=a,rows=n,users=u,resources=r) for a,n,u,r in rows])
    return DashboardResponse(available=True,data=artifact,profiles=profiles,recommendations=recommendations,message=None)

