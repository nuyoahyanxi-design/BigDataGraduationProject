import hashlib
import json
import re
from datetime import datetime, timezone
from spark.utils.config import ROOT
from spark.utils.files import write_json, validate_hashes, parquet_files
from spark.utils.profiles import canonical
from spark.utils.session import build_spark
from spark.utils.dashboard_metrics import compute_metrics
from spark.jobs.recommendations import batch_lock


def run(spark):
    rec_path = ROOT/'outputs/recommendation-latest.json'
    recommendation = json.loads(rec_path.read_text()) if rec_path.exists() else None
    if recommendation:
        if recommendation['status'] != 'completed' or recommendation['mysql_publication'] != 'passed':
            raise RuntimeError('Recommendation publication incomplete')
        source = recommendation['source_batch_id']
    else:
        pointer = json.loads((ROOT/'outputs/spark-data-pipeline-latest.json').read_text())
        if pointer['status'] != 'completed':
            raise RuntimeError('Pipeline incomplete')
        source = pointer['batch_id']
    if not re.fullmatch(r'\d{8}T\d{6}Z_[0-9a-f]{8}',source):
        raise ValueError('Invalid source batch')
    ods = ROOT/'data/ods'/('batch_id='+source); dwd = ROOT/'data/dwd'/('batch_id='+source)
    om = json.loads((ods/'manifest.json').read_text()); dm = json.loads((dwd/'manifest.json').read_text())
    if any(m['status']!='completed' or m['batch_id']!=source for m in [om,dm]) or om['snapshot_at'] != dm['snapshot_at']:
        raise RuntimeError('Snapshot lineage mismatch')
    for table in ['users','resources','learning_progress']:
        validate_hashes(ods/table, om['tables'][table]['files'])
    validate_hashes(dwd/'learning_events', dm['learning_events']['files'])
    quality = json.loads((ROOT/'outputs/spark-data-pipeline'/source/'quality-report.json').read_text())
    if quality['batch_id'] != source or quality['conservation'] != 'passed':
        raise RuntimeError('Quality lineage mismatch')
    from spark.utils.progress import load_progress,RULE as PROGRESS_RULE
    effective_progress=load_progress(spark,ods,dwd)
    progress=effective_progress if effective_progress is not None else spark.read.parquet(str(ods/'learning_progress'))
    from spark.utils.resource_scope import load_formal,restrict,SCOPE_RULE,SCOPE_LABEL
    scoped=load_formal(spark,ods)
    resources=scoped if scoped is not None else spark.read.parquet(str(ods/'resources'))
    events=spark.read.parquet(str(dwd/'learning_events'))
    if scoped is not None: progress=restrict(progress,scoped);events=restrict(events,scoped)
    daily, metrics = compute_metrics(spark,spark.read.parquet(str(ods/'users')),resources,progress,events,om['snapshot_at'])
    if scoped is not None:
        metrics['learning']['scope_label']=SCOPE_LABEL;metrics['resources']['scope_label']=SCOPE_LABEL
    from spark.utils.chapter_analytics import load_chapters,dashboard_chapters
    ce,_=load_chapters(spark,ods,dwd)
    if scoped is not None: ce=restrict(ce,scoped)
    if ce is not None: metrics['chapter']=dashboard_chapters(ce,spark.read.parquet(str(ods/'users')),om['snapshot_at'])
    code_hash = hashlib.sha256(PathBytes()).hexdigest()[:12]
    linked = None if recommendation is None else {k:recommendation[k] for k in ['batch_id','profile_batch_id','generated_at','as_of_utc']}
    identity = hashlib.sha256(canonical({'code':code_hash,'linked':linked}).encode()).hexdigest()[:12]
    batch = source + '_d1_' + identity
    target = ROOT/'data/ads/daily_metrics'/('batch_id='+batch)
    with batch_lock(target):
        manifest_path = target/'manifest.json'
        previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
        generated = previous['generated_at'] if previous else datetime.now(timezone.utc).isoformat(timespec='milliseconds')
        record = {'batch_id':batch,'source_batch_id':source,'generated_at':generated,'as_of_utc':om['snapshot_at'],
            'source':'Spark ODS/DWD daily_metrics Parquet + paired MySQL analytics results'+('; '+PROGRESS_RULE if effective_progress is not None else '')+('; '+SCOPE_RULE if scoped is not None else ''),
            'dataset_origin':quality.get('dataset_origin','snapshot data; provenance not independently verified'),
            'spark_version':spark.version,'code_sha256':code_hash,'recommendation_publication':linked,
            'metrics':metrics,'quality':{k:quality[k] for k in ['input_count','filtered_count','output_count']}}
        digest = hashlib.sha256(canonical(record).encode()).hexdigest()
        if previous and (previous.get('status')!='completed' or previous.get('content_sha256') != digest):
            raise RuntimeError('Repeated dashboard batch differs or is unfinished')
        output = target/'daily_metrics'
        if previous:
            validate_hashes(output,previous['files'])
        else:
            daily.coalesce(1).write.mode('errorifexists').parquet(str(output))
        actual = [row.asDict() for row in spark.read.parquet(str(output)).orderBy('day').collect()]
        if actual != metrics['behavior']['daily']:
            raise RuntimeError('Daily metrics round-trip differs')
        result = {**record,'status':'completed','content_sha256':digest,'files':parquet_files(output),'parquet_round_trip':'passed'}
        write_json(manifest_path,result)
        write_json(ROOT/'outputs/dashboard-latest.json',result)
        write_json(ROOT/'outputs/dashboard-spark-verification.json',{'batch_id':batch,'source_batch_id':source,'spark_version':spark.version,'daily_rows':len(actual),'parquet_round_trip':'passed','total_effective_events':metrics['behavior']['total_effective_events'],'quality':record['quality'],'repeat_identity':bool(previous)})
        return result


def PathBytes():
    from pathlib import Path
    return Path(__file__).read_bytes() + (ROOT/'spark/utils/dashboard_metrics.py').read_bytes() + (ROOT/'spark/utils/chapter_analytics.py').read_bytes() + (ROOT/'spark/utils/progress.py').read_bytes() + (ROOT/'spark/utils/resource_scope.py').read_bytes() + (ROOT/'backend/app/core/resource_scope.py').read_bytes()


if __name__=='__main__':
    session = None
    try:
        session = build_spark('graduation-dashboard-statistics')
        result = run(session)
        print('Dashboard statistics published: '+result['batch_id'])
    except Exception as error:
        print('Dashboard statistics failed: '+type(error).__name__)
        raise SystemExit(1) from None
    finally:
        if session is not None: session.stop()
