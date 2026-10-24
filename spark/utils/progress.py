"""Current chapter progress, distinct from immutable historical action counts."""
import json
from pyspark.sql import functions as F
from spark.utils.files import validate_hashes

RULE='chapter-progress-v1: chapter records authoritative; legacy only without chapters'

def derive_progress(progress, chapters, chapter_progress, users, cutoff):
    cp=chapter_progress.withColumn('_completion_provided',F.col('completed_at').isNotNull()).withColumn('first_started_at',F.to_timestamp('first_started_at')).withColumn('completed_at',F.to_timestamp('completed_at'))
    stamp=F.to_timestamp(F.lit(cutoff))
    if cp.filter(F.col('first_started_at').isNull() | (F.col('_completion_provided') & F.col('completed_at').isNull()) | (F.col('first_started_at')>stamp) | (F.col('completed_at').isNotNull() & ((F.col('completed_at')<F.col('first_started_at')) | (F.col('completed_at')>stamp)))).limit(1).count():
        raise RuntimeError('Invalid chapter progress timeline')
    if cp.select('user_id').distinct().join(users.select(F.col('id').alias('user_id')),'user_id','left_anti').limit(1).count() or cp.select('chapter_id').distinct().join(chapters.select(F.col('id').alias('chapter_id')),'chapter_id','left_anti').limit(1).count():
        raise RuntimeError('Orphan chapter progress')
    if cp.groupBy('user_id','chapter_id').count().filter('count>1').limit(1).count():
        raise RuntimeError('Duplicate chapter progress')
    total=chapters.groupBy('resource_id').count().withColumnRenamed('count','total_chapters')
    ch=chapters.select(F.col('id').alias('chapter_id'),'resource_id')
    agg=cp.join(ch,'chapter_id').groupBy('user_id','resource_id').agg(F.count('*').alias('started_chapters'),F.count('completed_at').alias('completed_chapters'),F.min('first_started_at').alias('first_started_at'),F.max('completed_at').alias('_last_completed'),F.max(F.coalesce('completed_at','first_started_at')).alias('updated_at'))
    pairs=progress.select('user_id','resource_id').unionByName(agg.select('user_id','resource_id')).distinct().join(total,'resource_id')
    derived=pairs.join(agg,['user_id','resource_id'],'left').fillna({'started_chapters':0,'completed_chapters':0}).withColumn('status',F.when(F.col('completed_chapters')==F.col('total_chapters'),'completed').when(F.col('started_chapters')>0,'in_progress').otherwise('not_started')).withColumn('completed_at',F.when(F.col('status')=='completed',F.col('_last_completed')))
    columns=['user_id','resource_id','status','first_started_at','completed_at','updated_at']
    legacy=progress.join(total.select('resource_id'),'resource_id','left_anti').select(*[F.to_timestamp(c).alias(c) if c.endswith('_at') else F.col(c) for c in columns])
    return legacy.unionByName(derived.select(*columns))

def load_progress(spark, ods, dwd):
    dm=json.loads((dwd/'manifest.json').read_text())
    if 'effective_progress' not in dm:
        if dm.get('progress_rule'):raise RuntimeError('Missing canonical progress')
        return None
    validate_hashes(dwd/'effective_progress',dm['effective_progress']['files'])
    return spark.read.parquet(str(dwd/'effective_progress'))
