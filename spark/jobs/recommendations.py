"""Offline recommendation publication, frozen inputs, no serving API."""
import argparse
from contextlib import contextmanager
from datetime import datetime,timezone
import hashlib
import json
import re
import pymysql
from spark.utils.config import ROOT,MysqlSettings
from spark.utils.files import write_json,parquet_files,validate_hashes
from spark.utils.profiles import canonical
from spark.utils.recommendations import compute_recommendations,validate_parameters,SOURCE_BYTES
from spark.utils.session import build_spark

COLUMNS=['user_id','resource_id','batch_id','algorithm','score','rank','reason']
RESULT_SCHEMA='user_id long,resource_id long,batch_id string,algorithm string,score decimal(24,12),rank int,reason string'
JOB_SOURCE_BYTES = ROOT.joinpath('spark/jobs/recommendations.py').read_bytes()


def verify_loaded_code():
    if SOURCE_BYTES != (ROOT/'spark/utils/recommendations.py').read_bytes() or JOB_SOURCE_BYTES != (ROOT/'spark/jobs/recommendations.py').read_bytes():
        raise RuntimeError('Recommendation code changed after import; restart task before publication')

def json_read(path):
    return json.loads(path.read_text(encoding='utf-8'))

@contextmanager
def batch_lock(target):
    import fcntl
    target.mkdir(parents=True,exist_ok=True)
    with (target/'.publication.lock').open('a') as handle:
        try:
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Recommendation batch is already running') from None
        try:
            yield
        finally:
            fcntl.flock(handle,fcntl.LOCK_UN)

def normalize_db_rows(rows):
    return [dict(row,score=format(row['score'],'.12f')) for row in rows]

def publish_mysql(rows,batch):
    if any(row['batch_id']!=batch for row in rows):
        raise ValueError('Mixed recommendation batches')
    settings=MysqlSettings.from_environment()
    conn=pymysql.connect(host=settings.host,port=settings.port,user=settings.user,password=settings.password,database=settings.database,charset='utf8mb4',autocommit=False,cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as q:
            q.execute("SET time_zone='+00:00'")
            # Business writers lock user then resource; use the same order.
            for uid in sorted({row['user_id'] for row in rows}):
                q.execute('SELECT role,status FROM users WHERE id=%s FOR UPDATE',(uid,))
                user=q.fetchone()
                if user!={'role':'learner','status':'active'}:
                    raise RuntimeError('Stale recommendation user; generate a fresh source batch')
            for rid in sorted({row['resource_id'] for row in rows}):
                q.execute('SELECT status FROM resources WHERE id=%s FOR SHARE',(rid,))
                resource=q.fetchone()
                if resource!={'status':'published'}:
                    raise RuntimeError('Stale recommendation resource; generate a fresh source batch')
            for uid,rid in sorted({(row['user_id'],row['resource_id']) for row in rows}):
                q.execute('SELECT status FROM learning_progress WHERE user_id=%s AND resource_id=%s FOR SHARE',(uid,rid))
                state=q.fetchone()
                if state and state['status']=='completed':
                    raise RuntimeError('Stale completion state; generate a fresh source batch')
            sql='SELECT user_id,resource_id,batch_id,algorithm,score,`rank`,reason FROM recommendation_results WHERE batch_id=%s ORDER BY user_id,algorithm,`rank` FOR UPDATE'
            q.execute(sql,(batch,));old=normalize_db_rows(q.fetchall())
            if old:
                if old!=rows:
                    raise RuntimeError('Immutable recommendation batch conflict')
            elif rows:
                q.executemany('INSERT INTO recommendation_results (user_id,resource_id,batch_id,algorithm,score,`rank`,reason) VALUES (%s,%s,%s,%s,%s,%s,%s)',[[row[k] for k in COLUMNS] for row in rows])
            q.execute(sql,(batch,))
            if normalize_db_rows(q.fetchall())!=rows:
                raise RuntimeError('MySQL recommendation read-back mismatch')
        conn.commit()
    except Exception:
        conn.rollback();raise
    finally:
        conn.close()

def load_inputs(spark,profile_batch):
    if not re.fullmatch(r'\d{8}T\d{6}Z_[0-9a-f]{8}_p1_[0-9a-f]{12}',profile_batch):
        raise ValueError('Invalid profile batch')
    location=ROOT/'data/ads/user_profiles'/('batch_id='+profile_batch)
    pm=json_read(location/'manifest.json')
    if pm['status']!='completed' or pm['batch_id']!=profile_batch:
        raise RuntimeError('Incomplete profile batch')
    source=pm['source_batch_id']
    if not re.fullmatch(r'\d{8}T\d{6}Z_[0-9a-f]{8}',source):
        raise ValueError('Invalid source batch')
    ods=ROOT/'data/ods'/('batch_id='+source);dwd=ROOT/'data/dwd'/('batch_id='+source)
    om=json_read(ods/'manifest.json');dm=json_read(dwd/'manifest.json')
    if om['status']!='completed' or dm['status']!='completed' or om['batch_id']!=source or dm['batch_id']!=source or om['snapshot_at']!=dm['snapshot_at']:
        raise RuntimeError('Inconsistent ODS/DWD snapshots')
    validate_hashes(location/'profiles',pm['files'])
    for table in ['users','resources','learning_progress']:
        validate_hashes(ods/table,om['tables'][table]['files'])
    validate_hashes(dwd/'learning_events',dm['learning_events']['files'])
    profiles=spark.read.parquet(str(location/'profiles'))
    if pm['rows']>50000:
        raise ValueError('Profile row limit exceeded')
    actual=[row.asDict() for row in profiles.orderBy('user_id').limit(50001).collect()]
    if len(actual)!=pm['rows'] or hashlib.sha256(canonical(actual).encode()).hexdigest()!=pm['content_sha256']:
        raise RuntimeError('Profile content digest mismatch')
    if any(row['batch_id']!=profile_batch or json.loads(row['metric_explanations'])['source_batch_id']!=source or json.loads(row['metric_explanations'])['as_of_utc']!=om['snapshot_at'] for row in actual):
        raise RuntimeError('Profile lineage mismatch')
    return (profiles,spark.read.parquet(str(ods/'users')),spark.read.parquet(str(ods/'resources')),spark.read.parquet(str(dwd/'learning_events')),spark.read.parquet(str(ods/'learning_progress'))),pm,om

def run(spark,profile_batch,parameters=None):
    parameters=parameters or json_read(ROOT/'spark/configs/recommendation.json')
    validate_parameters(parameters)
    verify_loaded_code()
    frames,pm,om=load_inputs(spark,profile_batch)
    code_hash=hashlib.sha256(SOURCE_BYTES+JOB_SOURCE_BYTES).hexdigest()
    digest=hashlib.sha256(canonical({'profile_batch':profile_batch,'profile_digest':pm['content_sha256'],'parameters':parameters,'code_sha256':code_hash}).encode()).hexdigest()[:20]
    batch=pm['source_batch_id']+'_r1_'+digest
    target=ROOT/'data/ads/recommendations'/('batch_id='+batch)
    with batch_lock(target):
        path=target/'manifest.json';previous=json_read(path) if path.exists() else {}
        if previous and previous.get('status') not in ['prepared','completed','failed']:
            raise RuntimeError('Unfinished artifact needs inspection; preserved without overwrite')
        rows,counts=compute_recommendations(*frames,om['snapshot_at'],parameters)
        verify_loaded_code()
        rows=[dict(row,batch_id=batch) for row in rows]
        generated=previous.get('generated_at',datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec='milliseconds'))
        checksum=hashlib.sha256(canonical(rows).encode()).hexdigest()
        if previous and previous.get('content_sha256')!=checksum:
            raise RuntimeError('Repeated recommendation batch differs')
        metadata={'batch_id':batch,'source_batch_id':pm['source_batch_id'],'profile_batch_id':profile_batch,'as_of_utc':om['snapshot_at'],'generated_at':generated,'algorithms':{'popular_v1':{'version':'v1','score':'w_view*V + w_start*S + w_complete*C + w_favorite*F; weights in parameters'},'content_v1':{'version':'hybrid-v2','score':'0.6*tag_cosine + 0.25*personal_behavior/max_personal_behavior + 0.15*heat/max_heat; no-history uses normalized popularity'}},'parameters':parameters,'code_sha256':code_hash,'content_sha256':checksum,'counts':counts}
        output=target/'results'
        if output.exists():
            if not previous or 'files' not in previous:
                raise RuntimeError('Orphan Parquet needs inspection; preserved without overwrite')
            validate_hashes(output,previous['files'])
        else:
            write_json(path,dict(metadata,status='writing'))
            from decimal import Decimal
            frame=spark.createDataFrame([tuple(Decimal(row[k]) if k=='score' else row[k] for k in COLUMNS) for row in rows],RESULT_SCHEMA)
            frame.coalesce(1).write.mode('errorifexists').parquet(str(output))
        readback=normalize_db_rows([row.asDict() for row in spark.read.parquet(str(output)).orderBy('user_id','algorithm','rank').collect()])
        if readback!=rows:
            raise RuntimeError('Recommendation Parquet round-trip mismatch')
        status=dict(metadata,status='prepared',files=parquet_files(output),parquet_round_trip='passed')
        if previous.get('status')!='completed':
            write_json(path,status)
        try:
            publish_mysql(rows,batch)
        except Exception as error:
            if previous.get('status')!='completed':
                write_json(path,dict(status,status='failed',error_type=type(error).__name__))
            raise
        write_json(ROOT/'outputs/recommendations'/batch/'results.json',{'metadata':metadata,'results':rows})
        status.update(status='completed',mysql_publication='passed')
        write_json(path,status)
        write_json(ROOT/'outputs/recommendation-latest.json',status)
        return status

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--profile-batch');parser.add_argument('--top-n',type=int);args=parser.parse_args()
    batch=args.profile_batch or json_read(ROOT/'outputs/user-profile-latest.json')['batch_id']
    parameters=json_read(ROOT/'spark/configs/recommendation.json')
    if args.top_n is not None:
        parameters['top_n']=args.top_n
    spark=build_spark('personalized-recommendations')
    try:
        print(json.dumps(run(spark,batch,parameters),ensure_ascii=False))
    finally:
        spark.stop()
