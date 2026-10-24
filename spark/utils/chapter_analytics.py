"""Chapter events remain independent of resource events; no watch-time inference."""
import json
from pyspark.sql import functions as F, Window
from spark.utils.files import validate_hashes

RULE = 'chapter-v1: daily distinct chapter_view=.5/video_play=1; course/day cap=3'

def load_chapters(spark, ods, dwd):
    om=json.loads((ods/'manifest.json').read_text())
    if 'chapter_events' not in om['tables']:
        return None, None
    dm=json.loads((dwd/'manifest.json').read_text())
    for name in ['course_chapters','chapter_progress','chapter_events']:
        validate_hashes(ods/name,om['tables'][name]['files'])
    if dm.get('chapter_quality',{}).get('conservation')!='passed':
        raise RuntimeError('Chapter quality unavailable')
    validate_hashes(dwd/'chapter_events',dm['chapter_events']['files'])
    return spark.read.parquet(str(dwd/'chapter_events')), spark.read.parquet(str(ods/'course_chapters'))

def clean_chapters(events, users, resources, chapters, cutoff):
    e=events.withColumn('occurred_at',F.to_timestamp('occurred_at'))
    e=e.join(users.select(F.col('id').alias('_user')) ,e.user_id==F.col('_user'),'left')
    e=e.join(resources.select(F.col('id').alias('_resource')),e.resource_id==F.col('_resource'),'left')
    ch=chapters.select(F.col('id').alias('_chapter'),F.col('resource_id').alias('_course'))
    e=e.join(ch,e.chapter_id==F.col('_chapter'),'left')
    valid=(F.col('id').isNotNull() & (F.col('id')>0) & F.col('event_uuid').rlike('^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$') & F.col('_user').isNotNull() & F.col('_resource').isNotNull() & (F.col('_course')==F.col('resource_id')) & F.col('event_type').isin('chapter_view','video_play','chapter_complete') & F.col('occurred_at').isNotNull() & (F.col('occurred_at')<=F.to_timestamp(F.lit(cutoff))) & F.col('is_effective').isin(0,1) & (F.col('playback_seconds').isNull() | ((F.col('event_type')=='video_play') & F.col('playback_seconds').cast('double').isNotNull() & ~F.isnan(F.col('playback_seconds').cast('double')) & (F.col('playback_seconds').cast('double')>=0) & (F.col('playback_seconds').cast('double')<float('inf')))))
    e=e.withColumn('_reason',F.when(~F.coalesce(valid,F.lit(False)),'invalid').when(F.col('is_effective')==0,'no_state_change')).drop('_user','_resource','_chapter','_course')
    payload=F.to_json(F.struct(*[F.col(c) for c in events.columns if c!='id']))
    conflicts=e.groupBy('event_uuid').agg(F.countDistinct(payload).alias('variants')).filter('variants>1')
    if conflicts.limit(1).count():
        raise RuntimeError('Conflicting chapter UUID payload')
    e=e.withColumn('_rank',F.row_number().over(Window.partitionBy('event_uuid').orderBy('id')))
    e=e.withColumn('_reason',F.when(F.col('_reason').isNotNull(),F.col('_reason')).when(F.col('_rank')>1,'duplicate')).drop('_rank').cache()
    good=e.filter('_reason IS NULL').drop('_reason').cache()
    bad=e.filter('_reason IS NOT NULL').cache()
    n=e.count(); rejected=bad.count(); kept=good.count()
    if n!=rejected+kept: raise RuntimeError('Chapter conservation failed')
    report={'input_count':n,'filtered_count':rejected,'output_count':kept,'conservation':'passed','reasons':{r['_reason']:r['count'] for r in bad.groupBy('_reason').count().collect()}}
    e.unpersist()
    return good,bad,report

def learner_events(events, users, cutoff):
    learners=users.filter("role='learner' AND status='active'").select(F.col('id').alias('user_id'))
    return events.filter((F.col('is_effective')==1)&(F.col('occurred_at')<=F.to_timestamp(F.lit(cutoff)))).join(learners,'user_id').withColumn('day',F.to_date(F.from_utc_timestamp('occurred_at','Asia/Shanghai')))

def signals(events):
    e=events.filter(F.col('event_type').isin('chapter_view','video_play')).dropDuplicates(['user_id','resource_id','chapter_id','day','event_type'])
    e=e.withColumn('weight',F.when(F.col('event_type')=='video_play',1.0).otherwise(0.5))
    w=Window.partitionBy('user_id','resource_id','day')
    return e.withColumn('weight',F.col('weight')*F.least(F.lit(1.0),F.lit(3.0)/F.sum('weight').over(w)))

def summaries(events):
    rows=events.groupBy('user_id').agg(F.sum(F.when(F.col('event_type')=='chapter_view',1).otherwise(0)).alias('chapter_views'),F.sum(F.when(F.col('event_type')=='video_play',1).otherwise(0)).alias('video_plays'),F.countDistinct(F.when(F.col('event_type')=='chapter_view',F.col('chapter_id'))).alias('viewed_chapters'),F.countDistinct(F.when(F.col('event_type')=='video_play',F.col('chapter_id'))).alias('played_chapters'),F.countDistinct(F.when(F.col('event_type')=='chapter_complete',F.col('chapter_id'))).alias('completed_chapters')).collect()
    return {r.user_id:{k:v for k,v in r.asDict().items() if k!='user_id'} for r in rows}

def dashboard_chapters(events, users, cutoff):
    e=learner_events(events,users,cutoff)
    counts={r.event_type:r['count'] for r in e.groupBy('event_type').count().collect()}
    viewed=e.filter("event_type='chapter_view'")
    played=e.filter("event_type='video_play'")
    completed=e.filter("event_type='chapter_complete'")
    from datetime import datetime,timedelta
    from zoneinfo import ZoneInfo
    end=datetime.fromisoformat(cutoff).replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo('Asia/Shanghai')).date()
    dates=[(end-timedelta(days=i)).isoformat() for i in range(29,-1,-1)]
    daily={str(r.day):r.asDict() for r in e.groupBy('day').agg(*[F.sum(F.when(F.col('event_type')==t,1).otherwise(0)).alias(t) for t in ['chapter_view','video_play','chapter_complete']]).collect()}
    return {'chapter_views':counts.get('chapter_view',0),'video_plays':counts.get('video_play',0),'viewed_pairs':viewed.select('user_id','chapter_id').distinct().count(),'played_pairs':played.select('user_id','chapter_id').distinct().count(),'play_users':played.select('user_id').distinct().count(),'completed_pairs':completed.select('user_id','chapter_id').distinct().count(),'daily':[{'day':d,**{k:int(daily.get(d,{}).get(k,0)) for k in ['chapter_view','video_play','chapter_complete']}} for d in dates],'rule':RULE}
