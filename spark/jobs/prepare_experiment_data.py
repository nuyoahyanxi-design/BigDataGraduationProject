"""Publish labeled synthetic Parquet, then run existing offline evaluation."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from uuid import uuid4
from pyspark.sql import functions as F
from spark.utils.config import ROOT
from spark.utils.files import write_json,parquet_files,validate_hashes
from spark.utils.profiles import canonical
from spark.utils.schemas import TABLE_COLUMNS,schema_for
from spark.utils.experiment_seed_data import build_seed_data
from spark.utils.session import build_spark
from spark.jobs.clean import clean
from spark.jobs.recommendation_experiment import run as experiment_run

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def publish_snapshot(spark,snapshot,cutoff,config_digest):
    moment=datetime.fromisoformat(cutoff)
    if moment>=datetime.now(timezone.utc).replace(tzinfo=None):
        raise ValueError('Synthetic snapshot cutoff cannot be in the future')
    logical=hashlib.sha256(canonical(snapshot).encode()).hexdigest()
    digest=hashlib.sha256((logical+config_digest).encode()).hexdigest()[:8]
    batch=moment.strftime('%Y%m%dT%H%M%SZ')+'_'+digest
    ods=ROOT/'data/ods'/('batch_id='+batch);dwd=ROOT/'data/dwd'/('batch_id='+batch)
    if ods.exists():
        manifest=load(ods/'manifest.json')
        if manifest['status']!='completed' or manifest.get('source_system')!='synthetic' or manifest.get('snapshot_content_sha256')!=logical:
            raise ValueError('Existing synthetic snapshot differs or incomplete')
        for name,record in manifest['tables'].items():
            validate_hashes(ods/name,record['files'])
        if not dwd.exists():
            clean(spark,batch)
        dm=load(dwd/'manifest.json')
        if dm['status']!='completed':
            raise ValueError('Synthetic DWD incomplete')
        for name in ['learning_events','learning_events_rejected']:
            validate_hashes(dwd/name,dm[name]['files'])
        return batch,manifest,dm
    ods.mkdir(parents=True,exist_ok=False)
    manifest={'status':'writing','batch_id':batch,'snapshot_at':cutoff,'source_system':'synthetic','source_database':'synthetic_no_database','source_version':'synthetic_state_machine_v1','dataset_origin':'offline simulated records, not API receipts or real learners','reader':'offline state machine; no MySQL connection','snapshot_content_sha256':logical,'generator_configuration_sha256':config_digest,'tables':{}}
    write_json(ods/'manifest.json',manifest)
    for name,columns in TABLE_COLUMNS.items():
        frame=spark.createDataFrame([tuple(row[field] for field,_ in columns) for row in snapshot[name]],schema_for(name))
        frame=(frame.withColumn('_batch_id',F.lit(batch)).withColumn('_snapshot_at',F.to_timestamp(F.lit(cutoff))).withColumn('_source_database',F.lit('synthetic_no_database')).withColumn('_source_table',F.lit(name)))
        if name=='learning_events' and frame.filter((F.to_timestamp('occurred_at')>F.to_timestamp(F.lit(cutoff)))|(F.to_timestamp('received_at')>F.to_timestamp(F.lit(cutoff)))).limit(1).count():
            raise ValueError('Future event in synthetic training snapshot')
        path=ods/name
        frame.coalesce(1).write.mode('errorifexists').parquet(str(path))
        back=spark.read.parquet(str(path))
        if back.count()!=len(snapshot[name]) or frame.exceptAll(back).limit(1).count() or back.exceptAll(frame).limit(1).count():
            raise ValueError('Synthetic ODS round-trip differs')
        manifest['tables'][name]={'rows':len(snapshot[name]),'source_columns':[field for field,_ in columns],'schema':frame.schema.jsonValue(),'files':parquet_files(path),'round_trip':'passed'}
    manifest['status']='completed';write_json(ods/'manifest.json',manifest)
    quality=clean(spark,batch)
    if quality['invalid_count'] or quality['duplicate_count']:
        raise ValueError('Synthetic behavior failed existing DWD validation')
    return batch,manifest,load(dwd/'manifest.json')

def run(spark):
    config=load(ROOT/'spark/configs/experiment-data-preparation.json')
    algorithm_before={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in [ROOT/'spark/utils/profiles.py',ROOT/'spark/utils/recommendations.py',ROOT/'spark/jobs/recommendation_experiment.py']}
    generator_digest=hashlib.sha256(canonical(config).encode()+(ROOT/'spark/utils/experiment_seed_data.py').read_bytes()+(ROOT/'spark/jobs/prepare_experiment_data.py').read_bytes()).hexdigest()
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid4().hex[:8]
    directory=ROOT/'outputs/experiment-data-preparation'/run_id;directory.mkdir(parents=True)
    write_json(directory/'config.json',dict(config,generator_sha256=generator_digest))
    training={}
    def freeze_train(snapshot):
        batch,om,dm=publish_snapshot(spark,snapshot,config['train_cutoff_utc'],generator_digest)
        training.update(batch=batch,ods=om,dwd=dm)
        write_json(directory/'training-freeze.json',{'batch_id':batch,'status':'completed before test event generation','source_origin':'synthetic_state_machine_v1'})
    data=build_seed_data(config,freeze_train)
    test_batch,test_ods,test_dwd=publish_snapshot(spark,data['test_end'],config['test_cutoff_utc'],generator_digest)
    write_json(directory/'resource-seeds.json',data['resource_payloads'])
    write_json(directory/'simulated-learners.json',data['user_groups'])
    train_uuids={event['event_uuid'] for event in data['train']['learning_events']}
    test_only=[event for event in data['test_end']['learning_events'] if event['event_uuid'] not in train_uuids]
    if not test_only or max(e['occurred_at'] for e in data['train']['learning_events'])>=min(e['occurred_at'] for e in test_only):
        raise ValueError('Training/test time ordering failed')
    def stats(events):
        return {kind:sum(e['event_type']==kind for e in events) for kind in ['resource_view','learning_start','learning_complete','favorite_add','favorite_remove']}
    audit={'origin':'synthetic_state_machine_v1','database_writes':False,'api_requests':False,'resources':len(data['resource_payloads']),'learners':len(data['user_groups']),'admin_reference_records':1,'themes':5,'train_batch':training['batch'],'test_batch':test_batch,'train_events':len(data['train']['learning_events']),'test_period_events':len(test_only),'train_event_types':stats(data['train']['learning_events']),'test_event_types':stats(test_only),'train_quality':training['dwd']['quality'],'test_end_quality':test_dwd['quality'],'strict_time_order':'passed','train_test_uuid_overlap':0,'training_metadata_snapshot_isolated':True}
    write_json(directory/'data-validation.json',audit)
    experiment_config={'version':'v1','train_batch':training['batch'],'test_batch':test_batch,'k':10,'positive_event_types':['learning_start','learning_complete','favorite_add'],'data_origin':'synthetic_state_machine_v1_seed20261005; deliberately theme-correlated simulated behavior, not real learners'}
    write_json(directory/'experiment-config.json',experiment_config)
    experiment=experiment_run(spark,experiment_config)
    metrics=load(ROOT/'outputs/experiments/recommendation'/experiment['run_id']/'metrics.json')
    if not metrics['accuracy_computable'] or any(value['evaluated_users']<30 for value in metrics['algorithms'].values()):
        raise ValueError('Simulated data still lacks eligible test labels')
    if any(hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest for path,digest in algorithm_before.items()):
        raise ValueError('Existing algorithm changed')
    result={'status':'completed','run_id':run_id,'origin':'synthetic_state_machine_v1','directory':str(directory),'train_batch':training['batch'],'test_batch':test_batch,'experiment':experiment,'metrics':metrics['algorithms'],'algorithm_sha256_unchanged':algorithm_before,'validation':audit}
    write_json(directory/'manifest.json',result)
    write_json(ROOT/'outputs/experiment-data-preparation/latest.json',result)
    return result

if __name__=='__main__':
    spark=build_spark('prepare-synthetic-experiment-data')
    try:
        result=run(spark)
        print(json.dumps({'status':result['status'],'run_id':result['run_id'],'train_batch':result['train_batch'],'test_batch':result['test_batch'],'experiment_id':result['experiment']['run_id'],'metrics':result['metrics']},ensure_ascii=False))
    finally:
        spark.stop()
