"""Private artifact workspace and exact-ID cleanup for real publication tests."""
import hashlib
import json
import shutil
import sys
from pathlib import Path
from uuid import uuid4

import pymysql
import pytest
from pyspark.sql import functions as F

from spark.utils.config import ROOT as PROJECT_ROOT, MysqlSettings
from spark.utils.files import write_json, parquet_files


def persistent_summary():
    settings=MysqlSettings.from_environment()
    conn=pymysql.connect(host=settings.host,port=settings.port,user=settings.user,password=settings.password,
                         database=settings.database,charset='utf8mb4')
    tables={}
    try:
        with conn.cursor() as cur:
            for table in ['users','resources','learning_progress','favorites','learning_events','chapter_progress','chapter_events','user_profiles','recommendation_results']:
                cur.execute(f'SHOW COLUMNS FROM `{table}`')
                columns=[r[0] for r in cur.fetchall() if r[0] not in ['password_hash','username','nickname']]
                cur.execute('SELECT '+','.join('`'+c+'`' for c in columns)+' FROM `'+table+'`')
                rows=sorted(json.dumps(row,ensure_ascii=False,default=str,separators=(',',':')) for row in cur.fetchall())
                tables[table]={'rows':len(rows),'sha256':hashlib.sha256('\n'.join(rows).encode()).hexdigest()}
    finally:
        conn.close()
    paths=list((PROJECT_ROOT/'data').rglob('manifest.json'))+list((PROJECT_ROOT/'data').rglob('*.parquet'))
    paths += [PROJECT_ROOT/'outputs'/name for name in ['spark-data-pipeline-latest.json','user-profile-latest.json','recommendation-latest.json','dashboard-latest.json']]
    files={str(p.relative_to(PROJECT_ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}
    return {'tables':tables,'formal_files':files}


@pytest.fixture(scope='session',autouse=True)
def isolated_spark_workspace(tmp_path_factory):
    before=persistent_summary()
    root=tmp_path_factory.mktemp('spark-publication-isolated')
    for name in ['spark','backend']:
        (root/name).symlink_to(PROJECT_ROOT/name,target_is_directory=True)
    for name in ['ods','dwd']:
        shutil.copytree(PROJECT_ROOT/'data'/name,root/'data'/name)
    shutil.copytree(PROJECT_ROOT/'outputs/spark-data-pipeline',root/'outputs/spark-data-pipeline')
    def remap(value):
        if isinstance(value,dict):return {k:remap(v) for k,v in value.items()}
        if isinstance(value,list):return [remap(v) for v in value]
        if isinstance(value,str):return value.replace(str(PROJECT_ROOT),str(root))
        return value
    for name in ['spark-data-pipeline-latest.json','user-profile-latest.json','recommendation-latest.json','dashboard-latest.json']:
        write_json(root/'outputs'/name,remap(json.loads((PROJECT_ROOT/'outputs'/name).read_text())))
    patch=pytest.MonkeyPatch()
    for name,module in list(sys.modules.items()):
        if name.startswith(('spark.jobs.','spark.utils.','spark.tests.','test_')) and getattr(module,'ROOT',None)==PROJECT_ROOT:
            patch.setattr(module,'ROOT',root)
    try:
        yield root
    finally:
        patch.undo()
        after=persistent_summary()
        result={'status':'passed' if before==after else 'failed','workspace':str(root),
                'formal_file_count':len(before['formal_files']),
                'tables_before':before['tables'],'tables_after':after['tables'],
                'changed_tables':[name for name in before['tables'] if before['tables'][name]!=after['tables'][name]],
                'changed_formal_files':[name for name in set(before['formal_files'])|set(after['formal_files']) if before['formal_files'].get(name)!=after['formal_files'].get(name)]}
        write_json(PROJECT_ROOT/'outputs/spark-publication-consistency.json',result)
        assert before==after, 'Persistent rows or formal batch artifacts changed during isolated Spark tests'


@pytest.fixture(scope='module')
def isolated_publication(spark_session,isolated_spark_workspace):
    from spark.jobs import user_profiles as profile_job
    root=isolated_spark_workspace
    origin=json.loads((root/'outputs/spark-data-pipeline-latest.json').read_text())['batch_id']
    sources=[]
    def new_source():
        source='20990101T000000Z_'+uuid4().hex[:8]
        sources.append(source)
        for layer in ['ods','dwd']:
            old=root/'data'/layer/('batch_id='+origin)
            target=root/'data'/layer/('batch_id='+source)
            target.mkdir()
            manifest=json.loads((old/'manifest.json').read_text())
            manifest['batch_id']=source
            records=manifest['tables'] if layer=='ods' else {key:manifest[key] for key in ['learning_events','learning_events_rejected']}
            for table,record in records.items():
                frame=spark_session.read.parquet(str(old/table))
                if '_batch_id' in frame.columns:frame=frame.withColumn('_batch_id',F.lit(source))
                frame.coalesce(1).write.mode('errorifexists').parquet(str(target/table))
                record['files']=parquet_files(target/table)
            write_json(target/'manifest.json',manifest)
        report=json.loads((root/'outputs/spark-data-pipeline'/origin/'quality-report.json').read_text())
        report['batch_id']=source
        write_json(root/'outputs/spark-data-pipeline'/source/'quality-report.json',report)
        return source
    try:
        source=new_source()
        write_json(root/'outputs/spark-data-pipeline-latest.json',{'batch_id':source,'status':'completed',
            'ods':str(root/'data/ods'/('batch_id='+source)),'dwd':str(root/'data/dwd'/('batch_id='+source)),
            'quality_report':str(root/'outputs/spark-data-pipeline'/source/'quality-report.json')})
        first=profile_job.run(spark_session,source)
        yield {'root':root,'source':source,'first':first,'new_source':new_source}
    finally:
        settings=MysqlSettings.from_environment()
        conn=pymysql.connect(host=settings.host,port=settings.port,user=settings.user,password=settings.password,
                             database=settings.database,charset='utf8mb4',autocommit=False)
        try:
            with conn.cursor() as cur:
                # Only exact batch IDs found under this private workspace, never a SQL wildcard.
                for table,folder in [('recommendation_results','recommendations'),('user_profiles','user_profiles')]:
                    directory=root/'data/ads'/folder
                    for path in directory.glob('batch_id=*'):
                        batch=path.name.removeprefix('batch_id=')
                        if any(batch.startswith(source+'_') for source in sources):
                            cur.execute(f'DELETE FROM `{table}` WHERE batch_id=%s',(batch,))
            conn.commit()
        finally:
            conn.close()
