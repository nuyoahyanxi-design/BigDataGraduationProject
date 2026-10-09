"""Leakage-free snapshot experiment runner; never publishes to MySQL."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
from time import perf_counter
from uuid import uuid4
from pyspark.sql import functions as F
from spark.utils.config import ROOT
from spark.utils.files import write_json,parquet_files,validate_hashes
from spark.utils.profiles import compute_profiles,canonical
from spark.utils.recommendations import compute_recommendations,eligible_resources
from spark.utils.recommendation_evaluation import time_partition,evaluate
from spark.utils.session import build_spark

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))

def source_manifests(batch):
    if not re.fullmatch(r'\d{8}T\d{6}Z_[0-9a-f]{8}',batch):
        raise ValueError('Invalid data batch')
    ods=ROOT/'data/ods'/('batch_id='+batch);dwd=ROOT/'data/dwd'/('batch_id='+batch)
    om=read_json(ods/'manifest.json');dm=read_json(dwd/'manifest.json')
    if om['status']!='completed' or dm['status']!='completed' or om['batch_id']!=batch or dm['batch_id']!=batch or om['snapshot_at']!=dm['snapshot_at']:
        raise ValueError('Incomplete/inconsistent source batch')
    return ods,dwd,om,dm

def freeze(directory,config):
    start=perf_counter()
    to,td,tm,tc=source_manifests(config['train_batch'])
    eo,ed,em,ec=source_manifests(config['test_batch'])
    if datetime.fromisoformat(tm['snapshot_at'])>=datetime.fromisoformat(em['snapshot_at']):
        raise ValueError('Test snapshot must be strictly later than training snapshot')
    target=directory/'frozen';target.mkdir()
    records={}
    sources=[('train_users',to/'users',tm['tables']['users']['files']),('train_resources',to/'resources',tm['tables']['resources']['files']),('train_progress',to/'learning_progress',tm['tables']['learning_progress']['files']),('train_events',td/'learning_events',tc['learning_events']['files']),('end_events',ed/'learning_events',ec['learning_events']['files'])]
    for name,source,files in sources:
        validate_hashes(source,files)
        shutil.copytree(source,target/name)
        validate_hashes(target/name,files)
        records[name]={'source':str(source),'files':files}
    for name,value in [('train_ods_manifest',tm),('train_dwd_manifest',tc),('test_ods_manifest',em),('test_dwd_manifest',ec)]:
        write_json(target/(name+'.json'),value)
    manifest={'train_batch':config['train_batch'],'test_batch':config['test_batch'],'train_cutoff_utc':tm['snapshot_at'],'test_end_utc':em['snapshot_at'],'datasets':records,'source_manifests_sha256':{name:hashlib.sha256((target/(name+'.json')).read_bytes()).hexdigest() for name in ['train_ods_manifest','train_dwd_manifest','test_ods_manifest','test_dwd_manifest']}}
    write_json(target/'manifest.json',manifest)
    return manifest,perf_counter()-start

def verify_frozen(directory,manifest):
    for name,record in manifest['datasets'].items():
        validate_hashes(directory/'frozen'/name,record['files'])
    for name,digest in manifest['source_manifests_sha256'].items():
        if hashlib.sha256((directory/'frozen'/(name+'.json')).read_bytes()).hexdigest()!=digest:
            raise ValueError('Frozen manifest changed')

def code_digests():
    names=['spark/utils/profiles.py','spark/utils/recommendations.py','spark/utils/recommendation_evaluation.py','spark/jobs/recommendation_experiment.py']
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}

def run(spark,config=None):
    start=perf_counter()
    config=dict(config or read_json(ROOT/'spark/configs/recommendation-experiment.json'))
    if config['version']!='v1' or config['k']!=10 or config['positive_event_types']!=['learning_start','learning_complete','favorite_add']:
        raise ValueError('Unsupported experiment protocol')
    params=read_json(ROOT/'spark/configs/recommendation.json');params['top_n']=10
    config['recommendation_parameters']=params
    hashes=code_digests()
    config['algorithm_versions']={'popular_v1':'v1','content_v1':'hybrid-v2'};config['code_sha256']=hashes
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid4().hex[:8]
    directory=ROOT/'outputs/experiments/recommendation'/run_id
    directory.mkdir(parents=True,exist_ok=False)
    write_json(directory/'config.json',config)
    write_json(directory/'manifest.json',{'status':'running','run_id':run_id})
    frames=[]
    try:
        manifest,freeze_seconds=freeze(directory,config)
        frozen=directory/'frozen'
        users=spark.read.parquet(str(frozen/'train_users'));resources=spark.read.parquet(str(frozen/'train_resources'));progress=spark.read.parquet(str(frozen/'train_progress'))
        train_source=spark.read.parquet(str(frozen/'train_events'));end_events=spark.read.parquet(str(frozen/'end_events'))
        cutoff=manifest['train_cutoff_utc'];end=manifest['test_end_utc']
        for frame in [users,resources]:
            if frame.filter((F.to_timestamp('created_at')>F.to_timestamp(F.lit(cutoff)))|(F.to_timestamp('updated_at')>F.to_timestamp(F.lit(cutoff)))).limit(1).count():
                raise ValueError('Future metadata in training snapshot')
        if progress.filter(F.to_timestamp('updated_at')>F.to_timestamp(F.lit(cutoff))).limit(1).count():
            raise ValueError('Future progress in training snapshot')
        train,test,late=time_partition(train_source,end_events,cutoff,end)
        for frame in [users,resources,progress,train,test]:
            frame.cache();frame.count();frames.append(frame)
        learners=users.filter((F.col('role')=='learner')&(F.col('status')=='active')).select(F.col('id').alias('user_id'))
        catalog=eligible_resources(resources).filter(F.col('status')=='published').select(F.col('id').alias('resource_id'))
        completed=progress.filter(F.col('status')=='completed').select('user_id','resource_id').unionByName(train.filter(F.col('event_type')=='learning_complete').select('user_id','resource_id')).distinct()
        raw=test.filter(F.col('event_type').isin(config['positive_event_types'])).select('user_id','resource_id').distinct()
        known_users=raw.join(learners,'user_id')
        known_resources=known_users.join(catalog,'resource_id')
        relevant=known_resources.join(completed,['user_id','resource_id'],'left_anti')
        truth=[(row.user_id,row.resource_id) for row in relevant.collect()]
        user_ids=[row.user_id for row in learners.collect()];catalog_ids=[row.resource_id for row in catalog.collect()]
        def bounds(frame):
            row=frame.agg(F.min('occurred_at').alias('min'),F.max('occurred_at').alias('max')).first()
            return {k:str(v) if v is not None else None for k,v in row.asDict().items()}
        audit={'train_events':train.count(),'train_source_events':train_source.count(),'test_events':test.count(),'end_snapshot_events':end_events.count(),'late_pre_cutoff_events_excluded':late.count(),'train_time_bounds_utc':bounds(train),'test_time_bounds_utc':bounds(test),'raw_positive_pairs':raw.count(),'excluded_unknown_training_user_pairs':raw.count()-known_users.count(),'excluded_unavailable_training_resource_pairs':known_users.count()-known_resources.count(),'excluded_training_completed_pairs':known_resources.count()-relevant.count(),'eligible_positive_pairs':len(truth),'training_users':len(user_ids),'training_published_resources':len(catalog_ids),'train_test_uuid_overlap':0,'training_metadata_source':config['train_batch'],'accuracy_population_users':len({uid for uid,_ in truth})}
        write_json(directory/'data-audit.json',audit)
        profile_start=perf_counter()
        profiles=compute_profiles(spark,train,users,resources,cutoff)
        profile_seconds=perf_counter()-profile_start
        write_json(directory/'training-profiles.json',{'as_of_utc':cutoff,'profiles':profiles})
        profile_frame=spark.createDataFrame([(row['user_id'],canonical(row['interest_profile'])) for row in profiles],'user_id long,interest_profile string').cache();profile_frame.count();frames.append(profile_frame)
        generation_start=perf_counter()
        recommendations,counts=compute_recommendations(profile_frame,users,resources,train,progress,cutoff,params)
        generation_seconds=perf_counter()-generation_start
        scoring_start=perf_counter()
        metrics=evaluate(recommendations,truth,user_ids,catalog_ids,10)
        scoring_seconds=perf_counter()-scoring_start
        from decimal import Decimal
        schema='user_id long,resource_id long,algorithm string,score decimal(24,12),rank int,reason string'
        columns=['user_id','resource_id','algorithm','score','rank','reason']
        result_frame=spark.createDataFrame([tuple(Decimal(row[k]) if k=='score' else row[k] for k in columns) for row in recommendations],schema)
        result_frame.coalesce(1).write.mode('errorifexists').parquet(str(directory/'recommendations-parquet'))
        back=[dict(row.asDict(),score=format(row.score,'.12f')) for row in spark.read.parquet(str(directory/'recommendations-parquet')).orderBy('user_id','algorithm','rank').collect()]
        if back!=recommendations:
            raise ValueError('Experiment result Parquet mismatch')
        write_json(directory/'recommendations.json',{'counts':counts,'results':recommendations})
        write_json(directory/'metrics.json',metrics)
        runtime={'freeze_seconds':freeze_seconds,'training_profile_seconds':profile_seconds,'recommendation_generation_seconds':generation_seconds,'recommendation_timing_scope':'both existing algorithms in one shared Spark call, including actions/collect; excludes JVM startup/profile/freeze','per_algorithm_generation_seconds':None,'metric_computation_seconds':scoring_seconds,'total_seconds_before_report':perf_counter()-start,'warmup_runs':0,'timing_repetitions':1}
        write_json(directory/'runtime.json',runtime)
        verify_frozen(directory,manifest)
        if hashes!=code_digests():
            raise ValueError('Experiment code changed during execution')
        warning='没有可推荐测试正样本，Recall@10/NDCG@10 不可计算，无法判断哪个算法更好。' if not metrics['accuracy_computable'] else '指标为当前有限样本描述，不代表统计显著提升。'
        pop=metrics['algorithms']['popular_v1'];content=metrics['algorithms']['content_v1']
        def show(value):
            return '不可计算（null）' if value is None else f'{value:.6f}'
        report=f'''# 推荐算法离线实验报告

实验 ID：{run_id}；数据来源：{config['data_origin']}。训练截止 UTC：{cutoff}；测试区间：({cutoff}, {end}]。

结论：{warning}

|算法|Recall@10|NDCG@10|Coverage|有效评价用户|
|---|---|---|---|---|
|popular_v1|{show(pop['recall_at_10'])}|{show(pop['ndcg_at_10'])}|{show(pop['coverage'])}|{pop['evaluated_users']}|
|content_v1|{show(content['recall_at_10'])}|{show(content['ndcg_at_10'])}|{show(content['coverage'])}|{content['evaluated_users']}|

训练 {audit['train_events']} 条事件，测试 {audit['test_events']} 条事件，可推荐测试正样本 {len(truth)} 对。训练用户 {len(user_ids)}、发布资源 {len(catalog_ids)}；未使用测试结束快照的用户兴趣、资源或进度，也未复用全历史线上画像。

两算法联合推荐生成耗时 {generation_seconds:.6f} 秒；共享候选计算，因此没有可独立归因的各算法耗时。单次计时不是性能基准。

Coverage 表示全部训练用户推荐覆盖了多少目录资源，不代表未来兴趣命中。目录只有 {len(catalog_ids)} 个资源而 K=10，小目录可能使两个方法都推荐全部可用资源，不能把高 Coverage 当作准确率。热门方法依据总体行为热度，内容方法依据兴趣标签与热门回退；是否更好需要测试标签。

本次只保存可复现产物，无准确率提升结论。下一次应在训练快照之后采集真实行为并冻结测试快照，扩大主题与资源目录；未在本阶段创建新行为或改算法。
'''
        (directory/'experiment-report.md').write_text(report,encoding='utf-8')
        result={'status':'completed','run_id':run_id,'directory':str(directory),'accuracy_computable':metrics['accuracy_computable'],'conclusion':warning,'train_batch':config['train_batch'],'test_batch':config['test_batch'],'recommendation_content_sha256':hashlib.sha256(canonical(recommendations).encode()).hexdigest(),'metrics_sha256':hashlib.sha256(canonical(metrics).encode()).hexdigest(),'parquet_files':parquet_files(directory/'recommendations-parquet'),'source_freeze_verified':'passed','code_digest_verified':'passed'}
        write_json(directory/'manifest.json',result)
        write_json(ROOT/'outputs/experiments/recommendation/latest.json',result)
        return result
    except Exception as error:
        write_json(directory/'manifest.json',{'status':'failed','run_id':run_id,'error_type':type(error).__name__})
        raise
    finally:
        for frame in frames:
            frame.unpersist()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--train-batch');parser.add_argument('--test-batch');args=parser.parse_args()
    config=read_json(ROOT/'spark/configs/recommendation-experiment.json')
    if args.train_batch:
        config['train_batch']=args.train_batch
    if args.test_batch:
        config['test_batch']=args.test_batch
    spark=build_spark('recommendation-offline-experiment')
    try:
        print(json.dumps(run(spark,config),ensure_ascii=False))
    finally:
        spark.stop()
