import copy
import json
import math
from pathlib import Path
import pytest
from pyspark.sql import functions as F
from spark.utils.config import ROOT
from spark.utils.profiles import compute_profiles
from spark.utils.recommendation_evaluation import evaluate,time_partition
from spark.utils.session import build_spark
from spark.jobs.recommendation_experiment import run,source_manifests,verify_frozen

def prediction(algorithm,uid,rids):
    return [{'algorithm':algorithm,'user_id':uid,'resource_id':rid,'rank':i} for i,rid in enumerate(rids,1)]

def test_metrics_hand_calculation_and_duplicate_truth():
    rows=prediction('popular_v1',1,[10,20,30])+prediction('content_v1',1,[20,30,10])
    result=evaluate(rows,[(1,10),(1,30),(1,10)],[1],[10,20,30],10)
    expected_idcg=1+1/math.log2(3)
    assert result['algorithms']['popular_v1']['recall_at_10']==1
    assert result['algorithms']['popular_v1']['ndcg_at_10']==pytest.approx((1+1/math.log2(4))/expected_idcg)
    assert result['algorithms']['content_v1']['ndcg_at_10']==pytest.approx((1/math.log2(3)+1/math.log2(4))/expected_idcg)
    assert result['algorithms']['popular_v1']['coverage']==1
    assert result['content_minus_popular']['ndcg_at_10']<0

def test_no_labels_null_not_zero_and_catalog_coverage():
    result=evaluate(prediction('popular_v1',1,[10]),[],[1],[10,20],10)
    assert not result['accuracy_computable']
    assert result['algorithms']['popular_v1']['recall_at_10'] is None
    assert result['algorithms']['popular_v1']['ndcg_at_10'] is None
    assert result['algorithms']['popular_v1']['coverage']==0.5
    assert result['content_minus_popular']['recall_at_10'] is None

def test_macro_average_excludes_users_without_labels():
    rows=prediction('popular_v1',1,[10])+prediction('popular_v1',2,[30])
    result=evaluate(rows,[(1,10),(2,20)],[1,2,3],[10,20,30])
    assert result['algorithms']['popular_v1']['recall_at_10']==0.5
    assert result['algorithms']['popular_v1']['ndcg_at_10']==0.5
    assert result['algorithms']['popular_v1']['evaluated_users']==2
    assert result['algorithms']['content_v1']['recall_at_10']==0

def test_empty_catalog_no_users_and_invalid_predictions():
    assert evaluate([],[],[],[])['algorithms']['popular_v1']['coverage'] is None
    with pytest.raises(ValueError,match='Duplicate resource'):
        evaluate(prediction('popular_v1',1,[10,10]),[(1,10)],[1],[10])
    with pytest.raises(ValueError,match='outside'):
        evaluate([],[(1,99)],[1],[10])
    bad=prediction('popular_v1',1,[10]);bad[0]['rank']=2
    with pytest.raises(ValueError,match='rank sequence'):
        evaluate(bad,[],[1],[10])

@pytest.fixture(scope='module')
def spark_session():
    spark=build_spark('recommendation-experiment-acceptance')
    yield spark
    spark.stop()

def temporal_fixture(s):
    schema='event_uuid string,id long,user_id long,resource_id long,event_type string,occurred_at string,received_at string,is_effective int'
    training=s.createDataFrame([('a',1,1,10,'resource_view','2026-01-01 23:59:59','2026-01-01 23:59:59',1),('b',2,1,10,'learning_start','2026-01-02 00:00:00','2026-01-02 00:00:00',1)],schema)
    end=training.unionByName(s.createDataFrame([('c',3,1,20,'learning_complete','2026-01-02 00:00:01','2026-01-02 00:00:01',1),('d',4,1,20,'resource_view','2026-01-03 00:00:00','2026-01-03 00:00:00',1),('late',5,1,20,'resource_view','2026-01-01 23:00:00','2026-01-02 01:00:00',1),('future',6,1,20,'learning_start','2026-01-03 00:00:01','2026-01-03 00:00:01',1)],schema))
    return training,end

def test_global_time_boundary_and_late_arrival(spark_session):
    before,end=temporal_fixture(spark_session)
    train,test,late=time_partition(before,end,'2026-01-02 00:00:00','2026-01-03 00:00:00')
    assert {r.event_uuid for r in train.collect()}=={'a','b'}
    assert {r.event_uuid for r in test.collect()}=={'c','d'}
    assert {r.event_uuid for r in late.collect()}=={'late'}

def test_uuid_overlap_rejected(spark_session):
    before,end=temporal_fixture(spark_session)
    conflict=end.withColumn('event_uuid',F.when(F.col('event_uuid')=='c','a').otherwise(F.col('event_uuid')))
    with pytest.raises(ValueError,match='UUID overlap'):
        time_partition(before,conflict,'2026-01-02 00:00:00','2026-01-03 00:00:00')

def test_training_profile_has_no_test_interest(spark_session):
    before,end=temporal_fixture(spark_session)
    train,_,_=time_partition(before,end,'2026-01-02 00:00:00','2026-01-03 00:00:00')
    users=spark_session.createDataFrame([(1,'learner','active','[]')],'id long,role string,status string,interest_tags string')
    resources=spark_session.createDataFrame([(10,'document','["python"]'),(20,'course','["sql"]')],'id long,resource_type string,tags string')
    profiles=compute_profiles(spark_session,train,users,resources,'2026-01-02 00:00:00')
    assert profiles[0]['interest_profile']['weights']=={'python':1.0}
    assert profiles[0]['learning_preference']['completed_resources']==0

def test_actual_snapshot_protocol_and_artifacts(spark_session):
    result=run(spark_session)
    directory=Path(result['directory'])
    metrics=json.loads((directory/'metrics.json').read_text())
    audit=json.loads((directory/'data-audit.json').read_text())
    runtime=json.loads((directory/'runtime.json').read_text())
    assert result['status']=='completed'
    assert audit['train_events']==5 and audit['test_events']==0
    assert audit['accuracy_population_users']==0
    assert not metrics['accuracy_computable']
    for method in ['popular_v1','content_v1']:
        assert metrics['algorithms'][method]['recall_at_10'] is None
        assert metrics['algorithms'][method]['ndcg_at_10'] is None
        # This original frozen batch contains only database-validation fixtures.
        # The new candidate rule excludes them; empty catalogs have undefined coverage.
        assert audit['training_published_resources']==0
        assert metrics['algorithms'][method]['coverage'] is None
    assert runtime['recommendation_generation_seconds']>0
    assert runtime['per_algorithm_generation_seconds'] is None
    assert (directory/'experiment-report.md').exists()
    manifest=json.loads((directory/'frozen/manifest.json').read_text())
    verify_frozen(directory,manifest)

def test_source_batch_validation():
    with pytest.raises(ValueError,match='Invalid data batch'):
        source_manifests('../unsafe-path')
