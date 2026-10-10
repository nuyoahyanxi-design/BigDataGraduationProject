from pyspark.sql import functions as F, Window

EVENT_TYPES=['resource_view','learning_start','learning_complete','favorite_add','favorite_remove']
UUID_PATTERN=r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
BRIDGE_UUID_PATTERN=r'^[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'


def clean_events(events,users,resources,cutoff):
    original=events.columns
    frame=(events.withColumn('_raw_hash',F.sha2(F.to_json(F.struct(*original)),256))
           .withColumn('_client_supplied',F.col('client_occurred_at').isNotNull())
           .withColumn('event_uuid',F.lower(F.trim('event_uuid')))
           .withColumn('request_fingerprint',F.lower('request_fingerprint')))
    for column in ['occurred_at','received_at','client_occurred_at']:
        frame=frame.withColumn(column,F.to_timestamp(column))
    frame=(frame.join(users.select(F.col('id').alias('_user_ref')).distinct(),frame.user_id==F.col('_user_ref'),'left')
           .join(resources.select(F.col('id').alias('_resource_ref'),F.col('version_no').alias('_resource_version')).distinct(),F.col('resource_id')==F.col('_resource_ref'),'left'))
    expected_fingerprint=F.sha2(F.concat(F.lit('['),F.col('schema_version').cast('string'),F.lit(','),
        F.col('user_id').cast('string'),F.lit(','),F.col('resource_id').cast('string'),F.lit(',"'),F.col('event_type'),F.lit('"]')),256)
    semantics=F.expr("""
      (event_type='resource_view' AND event_source='client' AND is_effective=1 AND session_id IS NOT NULL AND state_before IS NULL AND state_after IS NULL)
      OR (event_source='server' AND client_occurred_at IS NULL AND state_before IS NOT NULL AND state_after IS NOT NULL AND (
       (event_type='learning_start' AND ((is_effective=1 AND state_before='not_started' AND state_after='in_progress') OR (is_effective=0 AND state_before=state_after AND state_before IN ('in_progress','completed'))))
       OR (event_type='learning_complete' AND ((is_effective=1 AND state_before='in_progress' AND state_after='completed') OR (is_effective=0 AND state_before='completed' AND state_after='completed')))
       OR (event_type='favorite_add' AND ((is_effective=1 AND state_before='not_favorited' AND state_after='favorited') OR (is_effective=0 AND state_before='favorited' AND state_after='favorited')))
       OR (event_type='favorite_remove' AND ((is_effective=1 AND state_before='favorited' AND state_after='not_favorited') OR (is_effective=0 AND state_before='not_favorited' AND state_after='not_favorited')))
      ))""")
    # Client/session UUIDs remain v4; deterministic server course bridges use v5.
    valid_event_uuid=(F.col('event_uuid').rlike(UUID_PATTERN) |
        (F.col('event_uuid').rlike(BRIDGE_UUID_PATTERN) &
         (F.col('event_source')=='server') &
         F.col('event_type').isin('learning_start','learning_complete')))
    checks=[
      ('empty_or_invalid_user',F.col('user_id').isNull() | (F.col('user_id')<=0)),
      ('empty_or_invalid_resource',F.col('resource_id').isNull() | (F.col('resource_id')<=0)),
      ('invalid_event_type',F.col('event_type').isNull() | ~F.col('event_type').isin(EVENT_TYPES)),
      ('invalid_event_uuid',~F.coalesce(valid_event_uuid,F.lit(False))),
      ('invalid_event_id',F.col('id').isNull() | (F.col('id')<=0)),
      ('invalid_authoritative_time',F.col('occurred_at').isNull() | F.col('received_at').isNull()),
      ('invalid_client_time',F.col('_client_supplied') & F.col('client_occurred_at').isNull()),
      ('time_order',F.col('occurred_at')<F.col('received_at')),
      ('future_authoritative_time',(F.col('occurred_at')>F.lit(cutoff).cast('timestamp')) | (F.col('received_at')>F.lit(cutoff).cast('timestamp'))),
      ('missing_user_reference',F.col('_user_ref').isNull()),
      ('missing_resource_reference',F.col('_resource_ref').isNull()),
      ('unsupported_schema_version',F.col('schema_version').isNull() | (F.col('schema_version')!=1)),
      ('invalid_resource_version',F.col('resource_version').isNull() | (F.col('resource_version')<1) | (F.col('resource_version')>F.col('_resource_version'))),
      ('invalid_effectiveness',F.col('is_effective').isNull() | ~F.col('is_effective').isin(0,1)),
      ('invalid_session_uuid',F.col('session_id').isNotNull() & ~F.lower('session_id').rlike(UUID_PATTERN)),
      ('invalid_state_semantics',F.coalesce(~semantics,F.lit(True))),
      ('invalid_request_fingerprint',F.col('request_fingerprint').isNull() | ~F.col('request_fingerprint').rlike('^[0-9a-f]{64}$') | (expected_fingerprint.isNotNull() & (F.col('request_fingerprint')!=expected_fingerprint)))]
    # Missing timestamps are their own error; unknown comparisons do not imply future time.
    frame=frame.withColumn('quality_reasons',F.filter(F.array(*[F.when(F.coalesce(condition,F.lit(False)),F.lit(reason)) for reason,condition in checks]),lambda value:value.isNotNull())).cache()
    invalid=(frame.filter(F.size('quality_reasons')>0).withColumn('quality_reason',F.col('quality_reasons')[0])
             .withColumn('quality_class',F.lit('invalid')))
    valid=frame.filter(F.size('quality_reasons')==0)
    receipt_columns=[c for c in original if c!='id' and not c.startswith('_')]
    valid=valid.withColumn('_receipt_hash',F.sha2(F.to_json(F.struct(*receipt_columns)),256))
    conflicts=valid.groupBy('event_uuid').agg(F.countDistinct('_receipt_hash').alias('_variants')).filter('_variants > 1').select('event_uuid')
    conflicted=valid.join(conflicts,'event_uuid','inner')
    consistent=valid.join(conflicts,'event_uuid','left_anti')
    ordered=consistent.withColumn('_rank',F.row_number().over(Window.partitionBy('event_uuid').orderBy('received_at','occurred_at','id','_raw_hash')))
    duplicates=ordered.filter('_rank > 1')
    unique=ordered.filter('_rank = 1')
    noops=unique.filter('is_effective = 0')
    cleaned=unique.filter('is_effective = 1').select(*original).cache()

    def reject(df,reason,kind):
        return df.withColumn('quality_reason',F.lit(reason)).withColumn('quality_reasons',F.array(F.lit(reason))).withColumn('quality_class',F.lit(kind))
    rejected_columns=original+['quality_reason','quality_reasons','quality_class']
    rejected=(invalid.select(*rejected_columns)
              .unionByName(reject(conflicted,'duplicate_uuid_conflict','invalid').select(*rejected_columns))
              .unionByName(reject(duplicates,'duplicate_event_uuid','duplicate').select(*rejected_columns))
              .unionByName(reject(noops,'no_state_change','excluded').select(*rejected_columns))).cache()
    total=events.count();out=cleaned.count();filtered=rejected.count()
    primary={r['quality_reason']:r['count'] for r in rejected.groupBy('quality_reason').count().collect()}
    classes={r['quality_class']:r['count'] for r in rejected.groupBy('quality_class').count().collect()}
    all_reasons={r['reason']:r['count'] for r in rejected.select(F.explode('quality_reasons').alias('reason')).groupBy('reason').count().collect()}
    if total!=out+filtered or filtered!=sum(primary.values()):
        raise RuntimeError('Cleaning count conservation failed')
    frame.unpersist()
    return cleaned,rejected,{'input_count':total,'filtered_count':filtered,'output_count':out,
                             'primary_reasons':primary,'overlapping_reason_hits':all_reasons,
                             'invalid_count':classes.get('invalid',0),'duplicate_count':classes.get('duplicate',0),
                             'no_state_change_count':classes.get('excluded',0),'conservation':'passed'}
