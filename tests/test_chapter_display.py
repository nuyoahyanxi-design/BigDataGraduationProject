"""Schema compatibility without a database or authentication mutation."""
from backend.app.schemas.dashboard import Metrics
from backend.app.schemas.recommendations import ProfileSummary

def test_old_dashboard_and_extended_metrics():
    old=dict(users=dict(total=0,active_learners=0,admins=0),resources=dict(total=0,published=0),resource_categories=[],behavior=dict(total_effective_events=0,window_events=0,daily=[],timezone='Asia/Shanghai',window_days=30),learning=dict(started_pairs=0,in_progress=0,completed=0,completion_rate=None))
    assert Metrics.model_validate(old).chapter is None
    new={**old,'chapter':dict(chapter_views=2,video_plays=1,viewed_pairs=2,played_pairs=1,play_users=1,completed_pairs=0,daily=[],rule='chapter-v1')}
    assert Metrics.model_validate(new).chapter.video_plays==1

def test_old_and_new_profile_fields():
    row=dict(batch_id='old',generated_at='2026-10-01T00:00:00Z',as_of_utc='2026-10-01T00:00:00Z',interest_weights={},evidence='no_evidence',event_counts=dict(resource_view=0,learning_start=0,learning_complete=0,favorite_add=0,favorite_remove=0),active_days=0,started_resources=0,completed_resources=0,completion_rate=None)
    assert ProfileSummary.model_validate(row).chapter_activity is None
    row['chapter_activity']=dict(chapter_views=3,video_plays=2,viewed_chapters=1,played_chapters=1,completed_chapters=0)
    assert ProfileSummary.model_validate(row).chapter_activity.chapter_views==3
