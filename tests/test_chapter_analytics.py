"""In-memory fixtures; never write production DB or published artifacts."""
import json
from uuid import uuid4
import pytest
from pyspark.sql import functions as F
from spark.utils.session import build_spark
from spark.utils.chapter_analytics import clean_chapters,learner_events,signals,dashboard_chapters
from spark.utils.profiles import compute_profiles
from spark.utils.recommendations import compute_recommendations

@pytest.fixture(scope='module')
def s():
    spark=build_spark('chapter-analytics-tests')
    yield spark
    spark.stop()

def fixture(s):
    users=s.createDataFrame([(1,'learner','active','[]'),(2,'admin','active','[]')],'id long, role string, status string, interest_tags string')
    resources=s.createDataFrame([(10,'course','published','["spark"]'),(11,'course','published','["mysql"]')],'id long, resource_type string, status string, tags string')
    chapters=s.createDataFrame([(i,10,'["PySpark","pyspark"]') for i in range(1,6)],'id long,resource_id long,knowledge_tags string')
    rows=[(i,str(uuid4()),1,10,(i-1)%5+1,'video_play','2026-10-01 01:00:00','0',1) for i in range(1,12)]
    events=s.createDataFrame(rows,'id long,event_uuid string,user_id long,resource_id long,chapter_id long,event_type string,occurred_at string,playback_seconds string,is_effective int')
    return users,resources,chapters,events

def test_clean_and_daily_cap(s):
    users,resources,chapters,events=fixture(s)
    good,bad,q=clean_chapters(events,users,resources,chapters,'2026-10-02 00:00:00')
    try:
        assert q['output_count']==11 and bad.count()==0
        e=learner_events(good,users,'2026-10-02 00:00:00')
        assert signals(e).count()==5
        assert signals(e).agg(F.sum('weight')).first()[0]==pytest.approx(3)
        m=dashboard_chapters(good,users,'2026-10-02 00:00:00')
        assert m['video_plays']==11 and m['played_pairs']==5 and m['play_users']==1
    finally:good.unpersist();bad.unpersist()

def test_invalid_and_uuid_conflict(s):
    u,r,ch,e=fixture(s)
    bad=e.limit(1).withColumn('resource_id',F.lit(11)).unionByName(e.limit(1).withColumn('event_uuid',F.lit(str(uuid4()))).withColumn('occurred_at',F.lit('2030-01-01')))
    good,rejected,q=clean_chapters(bad,u,r,ch,'2026-10-02')
    try:assert q['filtered_count']==2 and good.count()==0
    finally:good.unpersist();rejected.unpersist()
    duplicate=e.limit(1).unionByName(e.limit(1).withColumn('id',F.lit(99)))
    good,rejected,q=clean_chapters(duplicate,u,r,ch,'2026-10-02')
    try:assert q['output_count']==1 and q['reasons']['duplicate']==1
    finally:good.unpersist();rejected.unpersist()
    conflict=e.limit(1).unionByName(e.limit(1).withColumn('chapter_id',F.lit(2)))
    with pytest.raises(RuntimeError,match='Conflicting'):clean_chapters(conflict,u,r,ch,'2026-10-02')

def test_profiles_and_recommendations(s):
    u,r,ch,ce=fixture(s)
    events=s.createDataFrame([], 'id long,user_id long,resource_id long,event_type string,occurred_at timestamp,is_effective int')
    old=compute_profiles(s,events,u,r,'2026-10-02')
    new=compute_profiles(s,events,u,r,'2026-10-02',ce,ch)
    assert 'chapter_activity' not in old[0]['activity_profile']
    assert new[0]['activity_profile']['active_days']==1
    assert new[0]['activity_profile']['chapter_activity']['video_plays']==11
    assert new[0]['interest_profile']['weights']=={'pyspark':1.0}
    profiles=s.createDataFrame([(row['user_id'],json.dumps(row['interest_profile'])) for row in new],'user_id long,interest_profile string')
    progress=s.createDataFrame([], 'user_id long,resource_id long,status string')
    params=dict(version='v1',top_n=5,weights=dict(view=1,start=2,complete=3,favorite=2),business_timezone='Asia/Shanghai',max_candidate_pairs=100,max_output_rows=100)
    rows,_=compute_recommendations(profiles,u,r,events,progress,'2026-10-02',params,ce)
    assert next(row for row in rows if row['algorithm']=='content_v1')['resource_id']==10
    assert float(next(row for row in rows if row['algorithm']=='popular_v1' and row['resource_id']==10)['score'])==3
