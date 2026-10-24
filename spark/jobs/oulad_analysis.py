"""Independent OULAD local analysis; never touches MySQL or platform publications."""
import hashlib
import json
import os
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from pyspark.sql import SparkSession, functions as F

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/external/oulad'

def run(spark):
    audit=json.loads((ROOT/'outputs/oulad-intake/audit.json').read_text())
    archive=BASE/'oulad-uci.zip'
    with archive.open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=audit['archive_sha256']:raise ValueError('Source checksum mismatch')
    batch=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid4().hex[:8]
    folder=BASE/'analysis'/batch;folder.mkdir(parents=True,exist_ok=False)
    raw=folder/'raw';raw.mkdir()
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            name=Path(member.filename).name
            if not name.endswith('.csv'):continue
            if Path(name).stem not in audit['tables']:raise ValueError('Unexpected source table')
            with z.open(member) as src,(raw/name).open('xb') as dst:shutil.copyfileobj(src,dst)
    frames={};counts={}
    for name in audit['tables']:
        source=spark.read.option('header',True).option('inferSchema',False).option('mode','FAILFAST').csv(str(raw/(name+'.csv')))
        source.write.mode('errorifexists').parquet(str(folder/'ods'/name))
        frame=spark.read.parquet(str(folder/'ods'/name))
        count=frame.count();counts[name]=count
        if count!=audit['tables'][name]['rows']:raise ValueError('Source row count mismatch: '+name)
        clean=frame.select(*[F.when(F.trim(F.col(c)).isin('','?','NA','N/A','NaN','nan','NULL','null'),F.lit(None)).otherwise(F.col(c)).alias(c) for c in frame.columns])
        if name=='studentVle':
            clean=clean.withColumn('date',F.col('date').cast('int')).withColumn('sum_click',F.col('sum_click').cast('long'))
            valid=clean.filter(F.col('date').isNotNull()&F.col('sum_click').isNotNull()&(F.col('sum_click')>=0)&F.col('id_student').isNotNull()&F.col('id_site').isNotNull())
            if valid.count()!=count:raise ValueError('Invalid interactions require explicit review')
            clean=valid
        clean.write.mode('errorifexists').parquet(str(folder/'dwd'/name))
        frames[name]=spark.read.parquet(str(folder/'dwd'/name))
        print(name+': ODS/DWD '+str(count),flush=True)
    info=frames['studentInfo'];vle=frames['vle'];events=frames['studentVle'].cache()
    keys=['code_module','code_presentation','id_student'];resource_keys=['code_module','code_presentation','id_site']
    if info.select(*keys).distinct().count()!=counts['studentInfo']:raise ValueError('Duplicate enrolment keys')
    if vle.select(*resource_keys).distinct().count()!=counts['vle']:raise ValueError('Duplicate resource keys')
    if events.join(info.select(*keys),keys,'left_anti').limit(1).count():raise ValueError('Interaction enrolment missing')
    if events.join(vle.select(*resource_keys),resource_keys,'left_anti').limit(1).count():raise ValueError('Interaction resource missing')
    students=info.select('id_student').distinct().count()
    clicks=int(events.agg(F.sum('sum_click')).first()[0])
    if students!=audit['unique_students'] or clicks!=audit['tables']['studentVle']['total_clicks']:raise ValueError('Independent audit reconciliation failed')
    def collect(frame):return [r.asDict() for r in frame.collect()]
    result={
        'schema_version':1,'source_dataset':'OULAD','source_kind':'external_anonymised_education_data','source_doi':'10.24432/C5KK69','source_url':'https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset','license':'CC BY 4.0',
        'citation':'Kuzilek, Hlosta & Zdrahal (2015), UCI Machine Learning Repository.','source_period':'2013–2014','generated_at':datetime.now(timezone.utc).isoformat(),'batch_id':batch,'archive_sha256':audit['archive_sha256'],'spark_version':spark.version,'spark_master':spark.sparkContext.master,
        'metrics':{'unique_students':students,'enrolments':counts['studentInfo'],'modules':frames['courses'].select('code_module').distinct().count(),'presentations':counts['courses'],'interaction_rows':counts['studentVle'],'total_clicks':clicks},
        'daily_clicks':collect(events.groupBy('date').agg(F.sum('sum_click').alias('clicks')).orderBy('date')),
        'outcomes':collect(info.groupBy('final_result').count().orderBy('final_result')),
        'activity_clicks':collect(events.join(vle.select(*resource_keys,'activity_type'),resource_keys).groupBy('activity_type').agg(F.sum('sum_click').alias('clicks')).orderBy(F.desc('clicks'))),
        'module_clicks':collect(events.groupBy('code_module').agg(F.sum('sum_click').alias('clicks')).orderBy('code_module')),
        'quality':{'input_rows':counts['studentVle'],'output_rows':counts['studentVle'],'invalid_rows':0,'orphan_interactions':0,'source_counts':counts,'audit_reconciled':True},
        'definitions':{'interaction_rows':'Aggregated student/resource/day rows, not individual video plays.','daily_clicks':'Days relative to each course start; presentations aligned, not calendar dates.','outcomes':'Original enrolment final results, not platform chapter completion.','dws':'In-job logical aggregation; no independent physical DWS table.','scope':'External historical data, not accounts or behaviour generated on this platform.'},
    }
    if sum(x['count'] for x in result['outcomes'])!=counts['studentInfo']:raise ValueError('Outcome totals mismatch')
    for name in ['daily_clicks','activity_clicks','module_clicks']:
        if sum(x['clicks'] for x in result[name])!=clicks:raise ValueError('Aggregate reconciliation failed: '+name)
    (folder/'ads').mkdir();target=folder/'ads'/'summary.json'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    # Dedicated atomic publication. The platform latest files are untouched.
    latest=BASE/'analysis'/'latest.json';temporary=latest.with_name('latest.'+uuid4().hex+'.tmp')
    temporary.write_text(json.dumps({'batch_id':batch,'summary':str(target.relative_to(BASE))},ensure_ascii=False),encoding='utf-8');os.replace(temporary,latest)
    events.unpersist()
    return result

if __name__=='__main__':
    session=SparkSession.builder.master('local[2]').appName('oulad-independent-analysis').config('spark.driver.memory','1g').config('spark.sql.shuffle.partitions','2').config('spark.sql.session.timeZone','UTC').config('spark.ui.enabled','false').getOrCreate()
    session.sparkContext.setLogLevel('ERROR')
    try:
        result=run(session);print(json.dumps({'status':'completed','batch_id':result['batch_id'],'metrics':result['metrics'],'master':result['spark_master']}),flush=True)
    finally:session.stop()
