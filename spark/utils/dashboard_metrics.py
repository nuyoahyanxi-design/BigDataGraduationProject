"""Descriptive statistics only; no profile or recommendation algorithm."""
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from pyspark.sql import functions as F

EVENTS = ['resource_view','learning_start','learning_complete','favorite_add','favorite_remove']


def compute_metrics(spark, users, resources, progress, events, cutoff):
    stamp = datetime.fromisoformat(cutoff).replace(tzinfo=timezone.utc)
    end = stamp.astimezone(ZoneInfo('Asia/Shanghai')).date()
    dates = [((end - timedelta(days=29-i)).isoformat(),) for i in range(30)]
    learners = users.filter((F.col('role') == 'learner') & (F.col('status') == 'active')).select(F.col('id').alias('user_id'))
    user_counts = users.agg(F.count('*').alias('total'),
        F.sum(F.when((F.col('role')=='learner') & (F.col('status')=='active'),1).otherwise(0)).alias('active_learners'),
        F.sum(F.when(F.col('role')=='admin',1).otherwise(0)).alias('admins')).first().asDict()
    resource_counts = resources.agg(F.count('*').alias('total'), F.sum(F.when(F.col('status')=='published',1).otherwise(0)).alias('published')).first().asDict()
    distribution = [dict(category=row.category_code, count=row['count']) for row in resources.filter(F.col('status')=='published').groupBy('category_code').count().orderBy('category_code').collect()]
    e = events.filter((F.col('is_effective')==1) & (F.to_timestamp('occurred_at')<=F.to_timestamp(F.lit(cutoff)))).join(learners,'user_id').filter(F.col('event_type').isin(EVENTS))
    total_events = e.count()
    daily = e.withColumn('day', F.date_format(F.from_utc_timestamp(F.to_timestamp('occurred_at'),'Asia/Shanghai'),'yyyy-MM-dd')).groupBy('day').agg(*[F.sum(F.when(F.col('event_type')==kind,1).otherwise(0)).cast('long').alias(kind) for kind in EVENTS])
    daily = spark.createDataFrame(dates, 'day string').join(daily,'day','left').fillna(0).orderBy('day')
    timeline = [row.asDict() for row in daily.collect()]
    window_events = int(daily.agg(F.sum(F.expr('+'.join(EVENTS)))).first()[0] or 0)
    observed = progress.join(learners,'user_id').filter(F.col('status').isin('in_progress','completed')).groupBy('status').count()
    counts = {r.status:r['count'] for r in observed.collect()}
    started = sum(counts.values()); completed = counts.get('completed',0)
    summary = {'users':{k:int(v or 0) for k,v in user_counts.items()},
        'resources':{k:int(v or 0) for k,v in resource_counts.items()}, 'resource_categories':distribution,
        'behavior':{'total_effective_events':total_events,'window_events':window_events,'daily':timeline,'timezone':'Asia/Shanghai','window_days':30},
        'learning':{'started_pairs':started,'in_progress':counts.get('in_progress',0),'completed':completed,'completion_rate':completed/started if started else None}}
    return daily, summary
