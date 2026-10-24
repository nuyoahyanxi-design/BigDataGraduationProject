"""Scope parity and ranking fixtures; no production data writes."""
import json
import pytest
from sqlalchemy import create_engine,text,select
from sqlalchemy.orm import Session
from app.models import Resource
from app.services.course_presentation import formal_course_clause
from spark.utils.session import build_spark
from spark.utils.resource_scope import formal_courses,restrict
from spark.utils.profiles import compute_profiles
from spark.utils.dashboard_metrics import compute_metrics
from spark.utils.recommendations import compute_recommendations

def test_online_scope_excludes_hidden_validation_offline_and_no_chapters():
    engine=create_engine('sqlite://')
    with engine.begin() as c:
        c.execute(text('CREATE TABLE resources(id INTEGER,status TEXT,source_name TEXT,license_note TEXT)'))
        c.execute(text('CREATE TABLE course_chapters(id INTEGER,resource_id INTEGER)'))
        c.execute(text("INSERT INTO resources VALUES(10,'published',NULL,NULL),(11,'published','本项目测试','仅供开发验收'),(12,'offline',NULL,NULL),(13,'published',NULL,NULL),(406,'published',NULL,NULL)"))
        c.execute(text('INSERT INTO course_chapters VALUES(1,10),(2,11),(3,12),(4,406)'))
    with Session(engine) as db:
        assert db.scalars(select(Resource.id).where(formal_course_clause())).all()==[10]
        assert db.execute(text('SELECT COUNT(*) FROM resources')).scalar_one()==5

@pytest.fixture(scope='module')
def spark():
    s=build_spark('formal-course-scope-tests')
    yield s
    s.stop()

def fixture(s):
    rows=[(i,'document','published','["spark"]','data-engineering',None,None) for i in range(10,15)]
    rows += [(406,'course','published','["spark"]','data-engineering',None,None),(20,'course','published','["spark"]','data-engineering','本项目测试','仅供开发验收'),(21,'course','offline','["spark"]','data-engineering',None,None),(22,'course','published','["spark"]','data-engineering',None,None)]
    r=s.createDataFrame(rows,'id long,resource_type string,status string,tags string,category_code string,source_name string,license_note string')
    ch=s.createDataFrame([(i,i) for i in [10,11,12,13,14,406,20,21]],'id long,resource_id long')
    users=s.createDataFrame([(1,'learner','active','[]'),(2,'learner','active','[]')],'id long,role string,status string,interest_tags string')
    events=s.createDataFrame([(i,1,rid,'resource_view','2026-10-01',1) for i,rid in enumerate([10,406,20,21,22])],'id long,user_id long,resource_id long,event_type string,occurred_at string,is_effective int')
    p=s.createDataFrame([(1,10,'in_progress'),(1,406,'completed'),(1,20,'completed'),(1,21,'completed'),(1,22,'completed')],'user_id long,resource_id long,status string')
    return r,ch,users,events,p

def test_scope_statistics_and_history_preservation(spark):
    r,ch,u,e,p=fixture(spark);scope=formal_courses(r,ch)
    assert sorted(x.id for x in scope.collect())==list(range(10,15))
    assert {x.resource_type for x in scope.collect()}=={'course'}
    assert r.filter("id=10 AND resource_type='document'").count()==1
    events=restrict(e,scope);progress=restrict(p,scope)
    profiles=compute_profiles(spark,events,u,scope,'2026-10-02',effective_progress=progress)
    assert profiles[0]['learning_preference']['started_resources']==1
    assert profiles[0]['learning_preference']['completed_resources']==0
    assert profiles[0]['activity_profile']['event_counts']['resource_view']==1
    assert profiles[1]['learning_preference']['completion_rate'] is None
    _,metrics=compute_metrics(spark,u,scope,progress,events,'2026-10-02')
    assert metrics['resources']['total']==5 and metrics['learning']['started_pairs']==1 and metrics['learning']['completed']==0
    assert e.count()==5 and p.count()==5

def test_no_hidden_topn_slot_consumption(spark):
    r,ch,u,e,p=fixture(spark);scope=formal_courses(r,ch)
    profiles=spark.createDataFrame([(i,json.dumps({'weights':{'spark':1.0},'evidence':'observed'})) for i in [1,2]],'user_id long,interest_profile string')
    params=dict(version='v1',top_n=5,weights=dict(view=1,start=2,complete=3,favorite=2),business_timezone='Asia/Shanghai',max_candidate_pairs=100,max_output_rows=100)
    rows,counts=compute_recommendations(profiles,u,scope,restrict(e,scope),restrict(p,scope),'2026-10-02',params,progress_is_canonical=True)
    assert counts['published_resources']==5 and len(rows)==20
    for user in [1,2]:
        for algorithm in ['popular_v1','content_v1']:
            selected=[r for r in rows if r['user_id']==user and r['algorithm']==algorithm]
            assert {r['resource_id'] for r in selected}==set(range(10,15))
            assert [r['rank'] for r in selected]==[1,2,3,4,5]
