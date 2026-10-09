import json
import pytest
import pymysql
from uuid import uuid4
from spark.utils.session import build_spark
from spark.utils.profiles import compute_profiles
from spark.jobs.user_profiles import run,publish_mysql,same_profile_json
from spark.utils.config import ROOT,MysqlSettings

@pytest.fixture(scope='module')
def spark_session():
    spark=build_spark('profile-acceptance')
    yield spark
    spark.stop()

@pytest.fixture(scope='module')
def synthetic(spark_session):
    s=spark_session
    users=s.createDataFrame([(1,'learner','active','[]'),(2,'learner','active','["sql"]'),(3,'learner','active','[]'),(4,'admin','active','[]')],'id long,role string,status string,interest_tags string')
    resources=s.createDataFrame([(10,'document','["spark"]'),(11,'course','["sql"]')],'id long,resource_type string,tags string')
    events=s.createDataFrame([(1,1,10,'resource_view','2026-10-01 23:00:00',1),(2,1,10,'resource_view','2026-10-02 01:00:00',1),(3,1,10,'learning_start','2026-10-02 02:00:00',1),(4,1,10,'learning_complete','2026-10-02 03:00:00',1),(5,1,11,'favorite_add','2026-10-02 04:00:00',1),(6,1,11,'favorite_remove','2026-10-02 05:00:00',1),(7,1,11,'learning_complete','2026-10-02 06:00:00',1)],'id long,user_id long,resource_id long,event_type string,occurred_at string,is_effective int')
    args=(events,users,resources,'2026-10-04 00:00:00')
    first=compute_profiles(s,*args)
    second=compute_profiles(s,*args)
    return {p['user_id']:p for p in first},first==second

def test_different_profiles(synthetic):
    p,_=synthetic
    assert p[1]['interest_profile']!=p[2]['interest_profile']
    assert p[1]['activity_profile']['active_days']==1
    assert p[1]['activity_profile']['event_counts']['resource_view']==2

def test_empty_and_cold_start(synthetic):
    p,_=synthetic
    assert p[2]['interest_profile']=={'weights':{'sql':1.0},'evidence':'explicit_only'}
    assert p[3]['interest_profile']=={'weights':{},'evidence':'no_evidence'}
    assert p[3]['learning_preference']['completion_rate'] is None
    assert p[3]['activity_profile']['active_days']==0
    assert 4 not in p

def test_completion_denominator(synthetic):
    p,_=synthetic
    assert p[1]['learning_preference']['started_resources']==1
    assert p[1]['learning_preference']['completed_resources']==1
    assert p[1]['learning_preference']['completion_rate']==1.0
    assert p[1]['learning_preference']['type_weights']=={'document':1.0}

def test_cancelled_favorite_and_daily_view(synthetic):
    p,_=synthetic
    # Spark tag evidence = one daily view + start 2 + complete 3;
    # SQL evidence = complete 3, cancelled favorite adds zero.
    assert p[1]['interest_profile']['weights']=={'spark':2/3,'sql':1/3}

def test_deterministic_computation(synthetic):
    assert synthetic[1]

def test_real_publication_repeat(spark_session,isolated_publication):
    source=json.loads((ROOT/'outputs/spark-data-pipeline-latest.json').read_text())['batch_id']
    first=run(spark_session,source)
    second=run(spark_session,source)
    assert first==second
    users=spark_session.read.parquet(str(ROOT/'data/ods'/('batch_id='+source)/'users'))
    expected=users.filter("role='learner' AND status='active'").count()
    assert first['status']=='completed' and first['rows']==expected

def test_publication_rollback_and_immutable_conflict(spark_session,isolated_publication):
    latest=json.loads((ROOT/'outputs/user-profile-latest.json').read_text())
    path=ROOT/'data/ads/user_profiles'/('batch_id='+latest['batch_id'])/'profiles'
    row=spark_session.read.parquet(str(path)).first().asDict()
    conflict=dict(row,activity_profile='{}')
    with pytest.raises(RuntimeError,match='immutable'):
        publish_mysql([conflict])
    batch='rollback_test_'+uuid4().hex
    first=dict(row,batch_id=batch)
    invalid=dict(first,user_id=9223372036854775807)
    with pytest.raises(pymysql.err.IntegrityError):
        publish_mysql([first,invalid])
    s=MysqlSettings.from_environment()
    c=pymysql.connect(host=s.host,port=s.port,user=s.user,password=s.password,database=s.database)
    try:
        with c.cursor() as q:
            q.execute('SELECT COUNT(*) FROM user_profiles WHERE batch_id=%s',(batch,))
            assert q.fetchone()[0]==0
            q.execute('SELECT COUNT(*) FROM user_profiles WHERE batch_id=%s',(latest['batch_id'],))
            assert q.fetchone()[0]==latest['rows']
    finally:
        c.close()


@pytest.mark.parametrize('field,path,a,b,expected',[
    ('interest_profile',('weights','python'),0.37580645161290316,0.3758064516129032,True),
    ('learning_preference',('type_weights','course'),0.23076923076923078,0.2307692307692308,True),
    ('learning_preference',('completion_rate',),0.8,0.8+1e-14,True),
    ('interest_profile',('weights','python'),0.3,0.30001,False),
    ('activity_profile',('active_days',),2,2.00000000000001,False),
    ('learning_preference',('started_resources',),5,5.0,False),
    ('interest_profile',('weights','python'),float('nan'),float('nan'),False),
    ('interest_profile',('weights','python'),True,1.0,False),
    ('metric_explanations',('unknown_score',),0.2,0.2+1e-14,False),
])
def test_only_named_floating_metrics_tolerate_noise(field,path,a,b,expected):
    assert same_profile_json(a,b,(field,)+path)==expected


def test_json_keys_remain_strict():
    assert not same_profile_json({'weights':{'python':1.0}},{'weights':{'python':1.0,'spark':0.0}},('interest_profile',))


def test_real_mysql_round_trip_retry_does_not_mutate_rows(spark_session,isolated_publication):
    first=isolated_publication['first']
    rows=[row.asDict() for row in spark_session.read.parquet(str(ROOT/'data/ads/user_profiles'/('batch_id='+first['batch_id'])/'profiles')).collect()]
    settings=MysqlSettings.from_environment()
    conn=pymysql.connect(host=settings.host,port=settings.port,user=settings.user,password=settings.password,database=settings.database)
    def stored():
        with conn.cursor() as cur:
            cur.execute('SELECT user_id,batch_id,generated_at,interest_profile,activity_profile,learning_preference,metric_explanations FROM user_profiles WHERE batch_id=%s ORDER BY user_id',(first['batch_id'],))
            return cur.fetchall()
    try:
        before=stored();publish_mysql(rows)
        conn.rollback()  # End the reader snapshot before verifying committed contents.
        assert stored()==before
    finally:conn.close()


@pytest.mark.parametrize('kind',['weight','count','keys','timestamp','identity_type'])
def test_real_semantic_conflicts_still_rejected(spark_session,isolated_publication,kind):
    from datetime import datetime,timedelta
    row=spark_session.read.parquet(str(ROOT/'data/ads/user_profiles'/('batch_id='+isolated_publication['first']['batch_id'])/'profiles')).first().asDict()
    if kind=='weight':
        value=json.loads(row['interest_profile']);value['weights']['test-new-tag']=0.001;row['interest_profile']=json.dumps(value)
    elif kind=='count':
        value=json.loads(row['activity_profile']);value['active_days']+=1;row['activity_profile']=json.dumps(value)
    elif kind=='keys':
        value=json.loads(row['learning_preference']);value['extra']=0;row['learning_preference']=json.dumps(value)
    elif kind=='timestamp':row['generated_at']=(datetime.fromisoformat(row['generated_at'])+timedelta(milliseconds=1)).isoformat()
    else:row['user_id']=float(row['user_id'])
    with pytest.raises((RuntimeError,ValueError)):publish_mysql([row])


def test_completed_failure_preserves_manifest_and_latest(spark_session,isolated_publication,monkeypatch):
    from spark.jobs import user_profiles as job
    batch=isolated_publication['first']['batch_id']
    manifest=ROOT/'data/ads/user_profiles'/('batch_id='+batch)/'manifest.json'
    latest=ROOT/'outputs/user-profile-latest.json'
    before=(manifest.read_bytes(),latest.read_bytes())
    def fail(rows):raise RuntimeError('isolated publication failure')
    monkeypatch.setattr(job,'publish_mysql',fail)
    with pytest.raises(RuntimeError,match='isolated publication failure'):run(spark_session,isolated_publication['source'])
    assert (manifest.read_bytes(),latest.read_bytes())==before


def test_new_failed_publication_is_not_prepared_or_latest(spark_session,isolated_publication,monkeypatch):
    from spark.jobs import user_profiles as job
    source=isolated_publication['new_source']()
    latest=ROOT/'outputs/user-profile-latest.json';before=latest.read_bytes()
    original_publish=job.publish_mysql
    def fail(rows):raise RuntimeError('isolated initial failure')
    monkeypatch.setattr(job,'publish_mysql',fail)
    with pytest.raises(RuntimeError,match='isolated initial failure'):run(spark_session,source)
    artifacts=list((ROOT/'data/ads/user_profiles').glob('batch_id='+source+'*/manifest.json'))
    assert len(artifacts)==1 and json.loads(artifacts[0].read_text())['status']=='failed'
    assert latest.read_bytes()==before
    monkeypatch.setattr(job,'publish_mysql',original_publish)
    recovered=run(spark_session,source)
    assert recovered['status']=='completed'
    assert json.loads(artifacts[0].read_text())==recovered
    assert json.loads(latest.read_text())==recovered
