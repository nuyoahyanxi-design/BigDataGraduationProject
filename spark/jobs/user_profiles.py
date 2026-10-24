import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timezone
import pymysql
from spark.utils.config import ROOT,MysqlSettings
from spark.utils.files import write_json,parquet_files,validate_hashes
from spark.utils.session import build_spark
from spark.utils.profiles import compute_profiles,canonical

def same_profile_json(old, new, path):
    """Only named floating metrics tolerate JSON DOUBLE round-trip noise."""
    if isinstance(old, dict) and isinstance(new, dict):
        return old.keys()==new.keys() and all(same_profile_json(old[k],new[k],path+(k,)) for k in old)
    if isinstance(old, list) and isinstance(new, list):
        return len(old)==len(new) and all(same_profile_json(a,b,path+(str(i),)) for i,(a,b) in enumerate(zip(old,new)))
    floating = (len(path)==3 and path[:2] in [('interest_profile','weights'),('learning_preference','type_weights')]) or path==('learning_preference','completion_rate')
    if floating and type(old) in (int,float) and type(new) in (int,float):
        return math.isfinite(old) and math.isfinite(new) and math.isclose(old,new,rel_tol=1e-12,abs_tol=1e-12)
    return type(old) is type(new) and old==new

def publish_mysql(rows):
    s=MysqlSettings.from_environment()
    conn=pymysql.connect(host=s.host,port=s.port,user=s.user,password=s.password,database=s.database,charset='utf8mb4',autocommit=False)
    try:
        with conn.cursor() as cur:
            cur.execute("SET time_zone='+00:00'")
            for row in rows:
                if type(row['user_id']) is not int or type(row['batch_id']) is not str:
                    raise ValueError('Profile identity types must be exact')
                values=[row[k] for k in ['user_id','batch_id','generated_at','interest_profile','activity_profile','learning_preference','metric_explanations']]
                cur.execute('SELECT generated_at,interest_profile,activity_profile,learning_preference,metric_explanations FROM user_profiles WHERE user_id=%s AND batch_id=%s FOR UPDATE',values[:2])
                old=cur.fetchone()
                if old:
                    if old[0]!=datetime.fromisoformat(values[2]) or any(not same_profile_json(json.loads(old[i+1]),json.loads(values[i+3]),(field,)) for i,field in enumerate(['interest_profile','activity_profile','learning_preference','metric_explanations'])):
                        raise RuntimeError('Existing profile differs; immutable batch publication rejected')
                else:
                    cur.execute('INSERT INTO user_profiles VALUES (%s,%s,%s,%s,%s,%s,%s)',values)
        conn.commit()
    except Exception:
        conn.rollback();raise
    finally:
        conn.close()

def run(spark,source_batch):
    if not re.fullmatch(r'\d{8}T\d{6}Z_[0-9a-f]{8}',source_batch):
        raise ValueError('Invalid source batch')
    ods=ROOT/'data/ods'/('batch_id='+source_batch);dwd=ROOT/'data/dwd'/('batch_id='+source_batch)
    om=json.loads((ods/'manifest.json').read_text());dm=json.loads((dwd/'manifest.json').read_text())
    if om['status']!='completed' or dm['status']!='completed' or om['snapshot_at']!=dm['snapshot_at']:
        raise RuntimeError('Incomplete or inconsistent source snapshot')
    for table in ['users','resources']:
        validate_hashes(ods/table,om['tables'][table]['files'])
    validate_hashes(dwd/'learning_events',dm['learning_events']['files'])
    digest=hashlib.sha256((ROOT/'spark/utils/profiles.py').read_bytes()+(ROOT/'spark/jobs/user_profiles.py').read_bytes()+(ROOT/'spark/utils/chapter_analytics.py').read_bytes()+(ROOT/'spark/utils/progress.py').read_bytes()+(ROOT/'spark/utils/resource_scope.py').read_bytes()+(ROOT/'backend/app/core/resource_scope.py').read_bytes()).hexdigest()[:12]
    batch=source_batch+'_p1_'+digest
    target=ROOT/'data/ads/user_profiles'/('batch_id='+batch)
    target.mkdir(parents=True,exist_ok=True)
    manifest_path=target/'manifest.json'
    previous=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    generated=previous.get('generated_at',datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec='milliseconds'))
    explanation={'rule_version':'v1','source_batch_id':source_batch,'as_of_utc':om['snapshot_at'],'interest':'daily distinct view=1,start=2,complete=3,current favorite=2; split tags; behavior 0.7 explicit 0.3 when both','activity':'distinct Asia/Shanghai dates of effective events','completion':'distinct completed started resources / distinct started resources; empty denominator=null','preference':'resource type score=distinct started + 2*completed'}
    from spark.utils.chapter_analytics import load_chapters,RULE
    ce,chapters=load_chapters(spark,ods,dwd)
    if ce is not None: explanation.update(chapter_rule=RULE,rule_version='chapter-v1')
    from spark.utils.progress import load_progress,RULE as PROGRESS_RULE
    effective_progress=load_progress(spark,ods,dwd)
    if effective_progress is not None: explanation.update(progress_rule=PROGRESS_RULE,completion='current effective completed resources / current effective started resources',interest=explanation['interest']+'; start/complete signals use effective progress')
    from spark.utils.resource_scope import load_formal,restrict,SCOPE_RULE,SCOPE_LABEL
    scoped=load_formal(spark,ods)
    resources=scoped if scoped is not None else spark.read.parquet(str(ods/'resources'))
    events=spark.read.parquet(str(dwd/'learning_events'))
    if scoped is not None:
        events=restrict(events,scoped);ce=restrict(ce,scoped);effective_progress=restrict(effective_progress,scoped)
        explanation.update(scope_rule=SCOPE_RULE,scope_label=SCOPE_LABEL,completion='completed formal courses / started formal courses; empty denominator=null')
    profiles=compute_profiles(spark,events,spark.read.parquet(str(ods/'users')),resources,om['snapshot_at'],ce,chapters,effective_progress)
    rows=[dict(user_id=p['user_id'],batch_id=batch,generated_at=generated,**{k:canonical(p[k]) for k in ['interest_profile','activity_profile','learning_preference']},metric_explanations=canonical(explanation)) for p in profiles]
    content_hash=hashlib.sha256(canonical(rows).encode()).hexdigest()
    if previous and previous.get('content_sha256')!=content_hash:
        raise RuntimeError('Repeated batch content mismatch')
    status={'status':'prepared','batch_id':batch,'source_batch_id':source_batch,'generated_at':generated,'rows':len(rows),'content_sha256':content_hash}
    parquet=target/'profiles'
    if parquet.exists():
        validate_hashes(parquet,previous['files'])
    else:
        frame=spark.createDataFrame(rows,'user_id long,batch_id string,generated_at string,interest_profile string,activity_profile string,learning_preference string,metric_explanations string')
        frame.coalesce(1).write.mode('errorifexists').parquet(str(parquet))
    actual=sorted([r.asDict() for r in spark.read.parquet(str(parquet)).collect()],key=lambda r:r['user_id'])
    if actual!=rows:
        raise RuntimeError('Profile Parquet round-trip mismatch')
    status['files']=parquet_files(parquet)
    if previous.get('status')!='completed':
        write_json(manifest_path,status)
    try:
        publish_mysql(rows)
    except Exception as error:
        if previous.get('status')!='completed':
            write_json(manifest_path,dict(status,status='failed',error_type=type(error).__name__))
        # Latest has not been touched, and a completed manifest was never demoted.
        raise
    status.update(status='completed',parquet_round_trip='passed',mysql_publication='passed')
    write_json(manifest_path,status)
    write_json(ROOT/'outputs/user-profile-latest.json',status)
    return status

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source-batch');args=parser.parse_args()
    batch=args.source_batch or json.loads((ROOT/'outputs/spark-data-pipeline-latest.json').read_text())['batch_id']
    spark=build_spark('user-profiles')
    try:
        print(json.dumps(run(spark,batch),ensure_ascii=False))
    finally:
        spark.stop()
