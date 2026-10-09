import copy
from decimal import Decimal
import json
import math
from pathlib import Path
from uuid import uuid4
import pymysql
import pytest
from pyspark.sql import functions as F
from spark.utils.config import ROOT,MysqlSettings
from spark.utils.profiles import canonical
from spark.utils.recommendations import compute_recommendations,validate_parameters
from spark.utils.session import build_spark
from spark.jobs.recommendations import run,publish_mysql,batch_lock,load_inputs

@pytest.fixture(scope='module')
def spark_session():
    spark=build_spark('recommendation-acceptance')
    yield spark
    spark.stop()

def parameters(n=2):
    p=json.loads((ROOT/'spark/configs/recommendation.json').read_text())
    p['top_n']=n
    return p

@pytest.fixture(scope='module')
def synthetic(spark_session):
    s=spark_session
    users=s.createDataFrame([(1,'learner','active'),(2,'learner','active'),(3,'learner','active'),(4,'learner','active'),(5,'admin','active'),(6,'learner','disabled')],'id long,role string,status string')
    profiles=s.createDataFrame([(1,canonical({'weights':{'python':0.8,'java':0.2},'evidence':'observed'})),(2,canonical({'weights':{'sql':1.0},'evidence':'explicit_only'})),(3,canonical({'weights':{},'evidence':'no_evidence'})),(4,canonical({'weights':{'java':1.0},'evidence':'observed'}))],'user_id long,interest_profile string')
    resources=s.createDataFrame([(10,'published','["python"]'),(11,'published','["sql"]'),(12,'published','["sql","python","python"]'),(12,'published','["sql","python","python"]'),(13,'offline','["python"]'),(14,'draft','["sql"]'),(15,'published','[]'),(16,'published','["python"]'),(17,'published','["java"]')],'id long,status string,tags string')
    events=s.createDataFrame([(1,1,10,'resource_view','2026-10-01 23:00:00',1),(2,1,10,'resource_view','2026-10-02 01:00:00',1),(3,1,10,'learning_start','2026-10-02 02:00:00',1),(4,1,10,'learning_complete','2026-10-02 03:00:00',1),(5,2,10,'favorite_add','2026-10-02 04:00:00',1),(6,2,10,'favorite_remove','2026-10-02 05:00:00',1),(7,4,11,'favorite_add','2026-10-02 05:00:00',1),(8,2,10,'resource_view','2026-10-05 00:00:00',1),(9,2,10,'learning_start','2026-10-02 03:00:00',0)],'id long,user_id long,resource_id long,event_type string,occurred_at string,is_effective int')
    progress=s.createDataFrame([(1,16,'completed')],'user_id long,resource_id long,status string')
    args=(profiles,users,resources,events,progress,'2026-10-04 00:00:00',parameters())
    rows,counts=compute_recommendations(*args)
    return args,rows,counts

def selected(rows,uid,algorithm='content_v1'):
    return [r for r in rows if r['user_id']==uid and r['algorithm']==algorithm]

def test_different_interests_and_explicit_cold_start(synthetic):
    _,rows,_=synthetic
    assert [r['resource_id'] for r in selected(rows,1)]==[12,17]
    assert [r['resource_id'] for r in selected(rows,2)]==[11,12]
    assert '学习兴趣匹配' in selected(rows,2)[0]['reason']
    assert '学习兴趣匹配' in selected(rows,1)[0]['reason']

def test_cosine_full_vector_norm_and_binary_resource_tags(synthetic):
    _,rows,_=synthetic
    assert float(selected(rows,1)[0]['score'])==pytest.approx(0.6*0.8/(math.sqrt(0.8**2+0.2**2)*math.sqrt(2)),abs=1e-12)
    assert float(selected(rows,2)[1]['score'])==pytest.approx(0.6/math.sqrt(2),abs=1e-12)

def test_no_interest_popular_and_zero_match_fallback(synthetic):
    _,rows,_=synthetic
    content=selected(rows,3);baseline=selected(rows,3,'popular_v1')
    assert [r['resource_id'] for r in content]==[r['resource_id'] for r in baseline]==[10,11]
    assert [Decimal(r['score']) for r in content]==[Decimal(1),Decimal('0.333333333333')]
    assert all('热门回退' in r['reason'] for r in content)
    assert selected(rows,4)[1]['resource_id']==11
    assert '收藏记录' in selected(rows,4)[1]['reason']

def test_heat_formula_daily_views_and_cancel(synthetic):
    _,rows,_=synthetic
    assert [Decimal(r['score']) for r in selected(rows,3,'popular_v1')]==[Decimal(6),Decimal(2)]

def test_status_completion_uniqueness_and_contiguous_rank(synthetic):
    _,rows,counts=synthetic
    assert all(r['resource_id'] not in [13,14] for r in rows)
    assert all(r['resource_id'] not in [10,16] for r in rows if r['user_id']==1)
    assert len({(r['user_id'],r['algorithm'],r['resource_id']) for r in rows})==len(rows)
    assert counts['users']==4 and counts['published_resources']==6
    for uid in range(1,5):
        for algorithm in ['popular_v1','content_v1']:
            assert [r['rank'] for r in selected(rows,uid,algorithm)]==[1,2]

def test_repeated_computation(synthetic):
    args,rows,counts=synthetic
    other,other_counts=compute_recommendations(*args)
    assert other==rows and other_counts==counts

def test_empty_candidates_and_all_empty_events(spark_session,synthetic):
    args,_,_=synthetic
    profiles,users,resources,events,progress,cutoff,p=args
    rows,counts=compute_recommendations(profiles,users,resources.filter('1=0'),events.filter('1=0'),progress,cutoff,p)
    assert rows==[] and counts['zero_result_users']==4
    rows,_=compute_recommendations(profiles,users,resources,events.filter('1=0'),progress,cutoff,p)
    assert all(Decimal(r['score'])==0 for r in rows if r['algorithm']=='popular_v1')

def test_parameter_limits_and_bad_vectors(synthetic):
    args,_,_=synthetic
    invalid=parameters();invalid['top_n']=0
    with pytest.raises(ValueError):
        validate_parameters(invalid)
    invalid=parameters();invalid['max_candidate_pairs']=1
    with pytest.raises(ValueError,match='Candidate pair'):
        compute_recommendations(*args[:-1],invalid)
    with pytest.raises(ValueError,match='Duplicate user profile'):
        compute_recommendations(args[0].unionByName(args[0]),*args[1:])
    bad=args[0].withColumn('interest_profile',F.lit('{"weights":{"python":-1},"evidence":"observed"}'))
    with pytest.raises(ValueError,match='Invalid interest vector'):
        compute_recommendations(bad,*args[1:])
    conflicting=args[2].unionByName(args[2].limit(1).withColumn('status',F.lit('offline')))
    with pytest.raises(ValueError,match='Conflicting resource'):
        compute_recommendations(args[0],args[1],conflicting,*args[3:])
    with pytest.raises(ValueError,match='Invalid profile batch'):
        load_inputs(args[0].sparkSession,'../unsafe-path')

def test_batch_lock(tmp_path):
    with batch_lock(tmp_path):
        with pytest.raises(RuntimeError,match='already running'):
            with batch_lock(tmp_path):
                pass


def test_publication_refuses_changed_code(monkeypatch,spark_session):
    from spark.jobs import recommendations as job
    monkeypatch.setattr(job,'JOB_SOURCE_BYTES',b'changed-code')
    with pytest.raises(RuntimeError,match='code changed'):
        job.run(spark_session,'invalid-unused-profile')

@pytest.fixture(scope='module')
def published(spark_session,isolated_publication):
    profile=json.loads((ROOT/'outputs/user-profile-latest.json').read_text())['batch_id']
    first=run(spark_session,profile)
    second=run(spark_session,profile)
    assert first==second
    artifact=json.loads((ROOT/'outputs/recommendations'/first['batch_id']/'results.json').read_text())
    return first,artifact['results']

def test_real_publication_repeat(published):
    status,rows=published
    assert status['status']=='completed'
    profile=json.loads((ROOT/'data/ads/user_profiles'/('batch_id='+status['profile_batch_id'])/'manifest.json').read_text())
    assert status['counts']['users']==profile['rows']
    assert status['counts']['output_rows']==len(rows)
    assert len(rows)>0
    assert all(1<=row['rank']<=status['parameters']['top_n'] for row in rows)
    assert all(row['resource_id']!=1 for row in rows if row['user_id']==2)

def connection():
    s=MysqlSettings.from_environment()
    return pymysql.connect(host=s.host,port=s.port,user=s.user,password=s.password,database=s.database,charset='utf8mb4',cursorclass=pymysql.cursors.DictCursor)

def test_db_schema_and_immutable_conflict(published):
    status,rows=published
    c=connection()
    try:
        with c.cursor() as q:
            q.execute('SHOW CREATE TABLE recommendation_results');schema=q.fetchone()['Create Table']
            assert 'UNIQUE KEY `uq_recommendation_rank`' in schema
            assert schema.count('FOREIGN KEY')==2 and schema.count(' CHECK ')==4
            q.execute('SHOW COLUMNS FROM recommendation_results')
            assert [r['Field'] for r in q.fetchall()]==['user_id','resource_id','batch_id','algorithm','score','rank','reason']
        conflict=copy.deepcopy(rows);conflict[0]['reason']='conflicting reason'
        with pytest.raises(RuntimeError,match='Immutable'):
            publish_mysql(conflict,status['batch_id'])
        evidence={'schema':schema,'rows':rows,'tests':'schema,immutable conflict,real publication repeat'}
        (ROOT/'outputs/recommendation-database-verification.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        c.close()

def test_insert_failure_rolls_back_whole_batch(published):
    _,rows=published
    # Valid current-state checks, then a deliberately duplicated rank triggers
    # the real UNIQUE constraint after the first insert in executemany.
    first=dict(rows[0],batch_id='rollback_'+uuid4().hex)
    second=dict(next(r for r in rows if r['user_id']==first['user_id'] and r['algorithm']==first['algorithm'] and r['resource_id']!=first['resource_id']),batch_id=first['batch_id'],rank=first['rank'])
    with pytest.raises(pymysql.err.IntegrityError):
        publish_mysql([first,second],first['batch_id'])
    c=connection()
    try:
        with c.cursor() as q:
            q.execute('SELECT COUNT(*) AS n FROM recommendation_results WHERE batch_id=%s',(first['batch_id'],))
            assert q.fetchone()['n']==0
    finally:
        c.close()

def test_current_completed_resource_rejected(published):
    _,rows=published
    c=connection()
    try:
        with c.cursor() as q:
            q.execute("SELECT user_id,resource_id FROM learning_progress WHERE status='completed' LIMIT 1")
            completed=q.fetchone()
        row=dict(rows[0],**completed,batch_id='stale_'+uuid4().hex)
        with pytest.raises(RuntimeError,match='completion state'):
            publish_mysql([row],row['batch_id'])
    finally:
        c.close()

def test_current_offline_resource_rejected(published):
    _,rows=published
    c=connection();rid=None;title='recommendation_stage_temp_'+uuid4().hex
    batch='offline_test_'+uuid4().hex
    try:
        with c.cursor() as q:
            q.execute("INSERT INTO resources (title,resource_type,category_code,tags,difficulty,summary,content,content_url,source_name,license_note,status,version_no,created_by,published_at,created_at,updated_at) SELECT %s,resource_type,category_code,tags,difficulty,summary,content,content_url,source_name,license_note,'offline',version_no,created_by,published_at,created_at,updated_at FROM resources WHERE id=%s",(title,rows[0]['resource_id']))
            assert q.rowcount==1
            rid=q.lastrowid
        c.commit()
        row=dict(rows[0],resource_id=rid,batch_id=batch)
        with pytest.raises(RuntimeError,match='Stale recommendation resource'):
            publish_mysql([row],batch)
        with c.cursor() as q:
            q.execute('SELECT COUNT(*) AS n FROM recommendation_results WHERE batch_id=%s',(batch,))
            assert q.fetchone()['n']==0
    finally:
        if rid is not None:
            with c.cursor() as q:
                q.execute('DELETE FROM recommendation_results WHERE batch_id=%s',(batch,))
                q.execute('DELETE FROM resources WHERE id=%s AND title=%s',(rid,title))
            c.commit()
        c.close()


def test_spark_database_interest_and_no_history(spark_session):
    s=spark_session
    users=s.createDataFrame([(1,'learner','active','["spark"]'),(2,'learner','active','["mysql"]'),(3,'learner','active','["spark"]')], 'id long,role string,status string,interest_tags string')
    profiles=s.createDataFrame([(i,canonical({'weights':{'mysql':1.0},'evidence':'observed'})) for i in (1,2,3)],'user_id long,interest_profile string')
    resources=s.createDataFrame([(10,'published','["spark","rdd","大数据"]','教学','自编'),(11,'published','["mysql","数据库"]','教学','自编'),(12,'published','["python","pyspark","spark"]','教学','自编'),(13,'published','["spark"]','本项目测试','仅供开发验收')],'id long,status string,tags string,source_name string,license_note string')
    events=s.createDataFrame([(1,1,10,'resource_view','2026-10-01 00:00:00',1),(2,2,11,'favorite_add','2026-10-01 00:00:00',1),(3,2,11,'learning_start','2026-10-01 00:00:00',1)],'id long,user_id long,resource_id long,event_type string,occurred_at string,is_effective int')
    progress=s.createDataFrame([], 'user_id long,resource_id long,status string')
    rows,_=compute_recommendations(profiles,users,resources,events,progress,'2026-10-04 00:00:00',parameters(3))
    assert selected(rows,1)[0]['resource_id']==10
    assert selected(rows,2)[0]['resource_id']==11
    assert all(r['resource_id']!=13 for r in rows)
    assert [r['resource_id'] for r in selected(rows,3)]==[r['resource_id'] for r in selected(rows,3,'popular_v1')]
    assert '无历史行为' in selected(rows,3)[0]['reason']
    assert all('按资源编号' not in r['reason'] for r in rows)
    assert all(0<=Decimal(r['score'])<=1 for r in rows if r['algorithm']=='content_v1')


def test_completed_recommendation_failure_preserves_state(spark_session,published,monkeypatch):
    from spark.jobs import recommendations as job
    status,_=published
    manifest=ROOT/'data/ads/recommendations'/('batch_id='+status['batch_id'])/'manifest.json'
    latest=ROOT/'outputs/recommendation-latest.json'
    before=(manifest.read_bytes(),latest.read_bytes())
    def fail(*args):raise RuntimeError('isolated recommendation publication failure')
    monkeypatch.setattr(job,'publish_mysql',fail)
    with pytest.raises(RuntimeError,match='isolated recommendation publication failure'):
        run(spark_session,status['profile_batch_id'])
    assert (manifest.read_bytes(),latest.read_bytes())==before


def test_initial_recommendation_failure_can_retry_without_losing_latest(spark_session,published,monkeypatch):
    from spark.jobs import recommendations as job
    status,_=published
    config=parameters(1)
    latest=ROOT/'outputs/recommendation-latest.json';before=latest.read_bytes()
    directory=ROOT/'data/ads/recommendations'
    existing=set(directory.glob('batch_id=*'))
    original_publish=job.publish_mysql
    def fail(*args):raise RuntimeError('isolated initial recommendation failure')
    monkeypatch.setattr(job,'publish_mysql',fail)
    with pytest.raises(RuntimeError,match='isolated initial recommendation failure'):
        run(spark_session,status['profile_batch_id'],config)
    new=set(directory.glob('batch_id=*'))-existing
    assert len(new)==1
    manifest=next(iter(new))/'manifest.json'
    assert json.loads(manifest.read_text())['status']=='failed'
    assert latest.read_bytes()==before
    monkeypatch.setattr(job,'publish_mysql',original_publish)
    recovered=run(spark_session,status['profile_batch_id'],config)
    assert recovered['status']=='completed'
    assert json.loads(manifest.read_text())==recovered
    assert json.loads(latest.read_text())==recovered
