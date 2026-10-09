import pytest
from spark.utils.session import build_spark
from spark.utils.dashboard_metrics import compute_metrics

@pytest.fixture(scope='module')
def spark():
    session = build_spark('dashboard-tests')
    yield session
    session.stop()

def frames(spark, empty=False):
    users = spark.createDataFrame([] if empty else [(1,'learner','active'),(2,'admin','active')], 'id long,role string,status string')
    resources = spark.createDataFrame([] if empty else [(1,'published','python-basics'),(2,'offline','data-engineering')], 'id long,status string,category_code string')
    progress = spark.createDataFrame([] if empty else [(1,'completed')], 'user_id long,status string')
    events = spark.createDataFrame([] if empty else [(1,'resource_view','2026-10-04 16:30:00',1),(1,'learning_start','2026-10-05 00:01:00',1),(2,'resource_view','2026-10-04 16:40:00',1),(1,'favorite_add','2026-10-04 16:50:00',0)], 'user_id long,event_type string,occurred_at string,is_effective int')
    return users, resources, progress, events

def test_timezone_valid_event_filter_and_learning_denominator(spark):
    daily, result = compute_metrics(spark,*frames(spark),'2026-10-05 00:00:00')
    assert daily.count() == 30
    assert result['behavior']['daily'][-1]['day'] == '2026-10-05'
    assert result['behavior']['daily'][-1]['resource_view'] == 1
    assert result['behavior']['window_events'] == 1
    assert result['behavior']['total_effective_events'] == 1
    assert result['resource_categories'] == [{'category':'python-basics','count':1}]
    assert result['users'] == {'total':2,'active_learners':1,'admins':1}
    assert result['learning']['completion_rate'] == 1.0

def test_empty_data_is_typed_zero_without_fake_completion(spark):
    daily, result = compute_metrics(spark,*frames(spark,True),'2026-10-05 00:00:00')
    assert daily.count() == 30
    assert result['users']['total'] == 0
    assert result['behavior']['window_events'] == 0
    assert result['learning']['completion_rate'] is None
    assert result['resource_categories'] == []
