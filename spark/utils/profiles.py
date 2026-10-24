"""Frozen-snapshot profile aggregation; no recommendation or ability scoring."""
import json
from pyspark.sql import functions as F, Window

TYPES=['resource_view','learning_start','learning_complete','favorite_add','favorite_remove']

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)

def compute_profiles(spark,events,users,resources,cutoff,chapter_events=None,chapters=None,effective_progress=None):
    people=users.filter((F.col('role')=='learner') & (F.col('status')=='active'))
    e=events.filter((F.col('is_effective')==1) & (F.col('occurred_at')<=F.to_timestamp(F.lit(cutoff)))).join(people.select(F.col('id').alias('user_id')),'user_id')
    e=e.withColumn('day',F.to_date(F.from_utc_timestamp('occurred_at','Asia/Shanghai')))
    counts={r.user_id:r.asDict() for r in e.groupBy('user_id').agg(F.countDistinct('day').alias('active_days'),*[F.sum(F.when(F.col('event_type')==t,1).otherwise(0)).alias(t) for t in TYPES]).collect()}
    starts=e.filter(F.col('event_type')=='learning_start').select('user_id','resource_id').distinct()
    completes=e.filter(F.col('event_type')=='learning_complete').select('user_id','resource_id').distinct().withColumn('completed',F.lit(1))
    learning=starts.join(completes,['user_id','resource_id'],'left').fillna({'completed':0}).join(resources.select(F.col('id').alias('resource_id'),F.col('resource_type').alias('type')),'resource_id')
    if effective_progress is not None:
        learning=effective_progress.join(people.select(F.col('id').alias('user_id')),'user_id').filter(F.col('status').isin('in_progress','completed')).select('user_id','resource_id',(F.col('status')=='completed').cast('int').alias('completed')).join(resources.select(F.col('id').alias('resource_id'),F.col('resource_type').alias('type')),'resource_id')
    totals={r.user_id:r.asDict() for r in learning.groupBy('user_id').agg(F.count('*').alias('started'),F.sum('completed').alias('completed')).collect()}
    preferences={}
    for r in learning.groupBy('user_id','type').agg(F.sum(1+2*F.col('completed')).alias('score')).collect():
        preferences.setdefault(r.user_id,{})[r.type]=float(r.score)
    views=e.filter(F.col('event_type')=='resource_view').dropDuplicates(['user_id','resource_id','day']).select('user_id','resource_id').withColumn('weight',F.lit(1.0))
    other=e.filter(F.col('event_type').isin('learning_start','learning_complete')).select('user_id','resource_id',F.when(F.col('event_type')=='learning_start',2.0).otherwise(3.0).alias('weight'))
    if effective_progress is not None:
        p=effective_progress.join(people.select(F.col('id').alias('user_id')),'user_id')
        other=p.filter(F.col('status').isin('in_progress','completed')).select('user_id','resource_id',F.lit(2.0).alias('weight')).unionByName(p.filter("status='completed'").select('user_id','resource_id',F.lit(3.0).alias('weight')))
    window=Window.partitionBy('user_id','resource_id').orderBy(F.col('occurred_at').desc(),F.col('id').desc())
    favorites=e.filter(F.col('event_type').isin('favorite_add','favorite_remove')).withColumn('rank',F.row_number().over(window)).filter((F.col('rank')==1)&(F.col('event_type')=='favorite_add')).select('user_id','resource_id').withColumn('weight',F.lit(2.0))
    tags=resources.select(F.col('id').alias('resource_id'),F.array_distinct(F.from_json('tags','array<string>')).alias('tags')).withColumn('tags',F.expr("filter(tags, x -> x is not null and length(trim(x)) > 0)"))
    scored=views.unionByName(other).unionByName(favorites).join(tags,'resource_id').filter(F.size('tags')>0).withColumn('score',F.col('weight')/F.size('tags')).withColumn('tag',F.explode('tags'))
    chapter_counts={}
    if chapter_events is not None:
        from spark.utils.chapter_analytics import learner_events,signals,summaries
        ce=learner_events(chapter_events,users,cutoff)
        chapter_counts=summaries(ce)
        days=e.select('user_id','day').unionByName(ce.select('user_id','day')).distinct().groupBy('user_id').count().collect()
        for row in days:
            counts.setdefault(row.user_id,{})['active_days']=row['count']
        sig=signals(ce).join(chapters.select(F.col('id').alias('chapter_id'),F.col('resource_id').alias('resource_id'),F.from_json('knowledge_tags','array<string>').alias('chapter_tags')),['chapter_id','resource_id']).join(tags,'resource_id')
        sig=sig.withColumn('chapter_tags',F.array_distinct(F.expr("transform(filter(chapter_tags, x -> x is not null and length(trim(x)) > 0), x -> lower(trim(x)))")))
        sig=sig.withColumn('tags',F.when(F.size('chapter_tags')>0,F.col('chapter_tags')).otherwise(F.col('tags'))).filter(F.size('tags')>0).withColumn('score',F.col('weight')/F.size('tags')).withColumn('tag',F.explode('tags'))
        scored=scored.select('user_id','tag','score').unionByName(sig.select('user_id','tag','score'))
    interests={}
    for r in scored.groupBy('user_id','tag').agg(F.sum('score').alias('score')).collect():
        interests.setdefault(r.user_id,{})[r.tag]=float(r.score)
    def normalized(scores):
        total=sum(scores.values())
        return {k:v/total for k,v in sorted(scores.items())} if total else {}
    results=[]
    for user in people.orderBy('id').collect():
        uid=user.id; explicit=sorted(set(json.loads(user.interest_tags or '[]')))
        a=normalized({t:1.0 for t in explicit});b=normalized(interests.get(uid,{}))
        merged={t:(0.3*a.get(t,0)+0.7*b.get(t,0) if a and b else a.get(t,0)+b.get(t,0)) for t in sorted(set(a)|set(b))}
        c=counts.get(uid,{});l=totals.get(uid,{'started':0,'completed':0})
        results.append({'user_id':uid,'interest_profile':{'weights':merged,'evidence':'observed' if c else ('explicit_only' if a else 'no_evidence')},'activity_profile':{'active_days':c.get('active_days',0),'event_counts':{t:c.get(t,0) for t in TYPES}},'learning_preference':{'started_resources':l['started'],'completed_resources':l['completed'],'completion_rate':l['completed']/l['started'] if l['started'] else None,'type_weights':normalized(preferences.get(uid,{}))}})
    if chapter_events is not None:
        for row in results:
            row['activity_profile']['chapter_activity']=chapter_counts.get(row['user_id'],dict(chapter_views=0,video_plays=0,viewed_chapters=0,played_chapters=0,completed_chapters=0))
    return results
