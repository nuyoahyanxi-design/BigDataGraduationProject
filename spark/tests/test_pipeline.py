import hashlib
import json
import secrets
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4, uuid5, NAMESPACE_URL

import pymysql
import pytest
from pyspark.sql import functions as F
from pyspark.sql.types import TimestampType

from spark.utils.config import ROOT,MysqlSettings
from spark.utils.session import build_spark
from spark.utils.schemas import schema_for,TABLE_COLUMNS
from spark.utils.cleaning import clean_events
from spark.utils.files import write_json,parquet_files,validate_hashes
from spark.utils.mysql_snapshot import snapshot_connection,scalar_row,read_table
from spark.utils import mysql_snapshot
from spark.jobs import clean as clean_job


@pytest.fixture(scope='module')
def session():
    spark=build_spark('spark-pipeline-acceptance')
    yield spark
    spark.stop()


def test_real_batch_spark_sql_and_parquet(session):
    assert session.version=='3.5.7'
    assert session.conf.get('spark.sql.session.timeZone')=='UTC'
    latest=json.loads((ROOT/'outputs/spark-data-pipeline-latest.json').read_text(encoding='utf-8'))
    ods=Path(latest['ods']);dwd=Path(latest['dwd'])
    manifest=json.loads((ods/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['status']=='completed' and len(manifest['tables'])==5
    assert sum(len(c) for c in TABLE_COLUMNS.values())==46
    for table in TABLE_COLUMNS:
        frame=session.read.parquet(str(ods/table))
        assert frame.count()==manifest['tables'][table]['rows']
        assert set(frame.columns)=={c for c,_ in TABLE_COLUMNS[table]}|{'_batch_id','_snapshot_at','_source_database','_source_table'}
        validate_hashes(ods/table,manifest['tables'][table]['files'])
    users=session.read.parquet(str(ods/'users'))
    assert not {'password_hash','username','nickname'}&set(users.columns)
    assert session.read.parquet(str(ods/'favorites')).count()==manifest['tables']['favorites']['rows']
    events=session.read.parquet(str(dwd/'learning_events'))
    assert isinstance(events.schema['occurred_at'].dataType,TimestampType)
    assert events.filter(F.col('is_effective')!=1).count()==0
    events.createOrReplaceTempView('acceptance_events')
    sql_count=session.sql('SELECT COUNT(*) AS n FROM acceptance_events').first()['n']
    report=json.loads(Path(latest['quality_report']).read_text(encoding='utf-8'))
    assert report['input_count']==manifest['tables']['learning_events']['rows']
    assert report['input_count']==report['filtered_count']+report['output_count']
    assert sql_count==report['output_count']
    assert sum(report['primary_reasons'].values())==report['filtered_count']


def references(session):
    return session.createDataFrame([(1,),(2,)],'id long'),session.createDataFrame([(1,3)],'id long, version_no long')


def make_event(id,kind='resource_view',**changes):
    item={'id':id,'event_uuid':str(uuid4()),'user_id':1,'resource_id':1,'event_type':kind,
          'event_source':'client' if kind=='resource_view' else 'server','schema_version':1,'resource_version':2,
          'session_id':str(uuid4()) if kind=='resource_view' else None,'occurred_at':'2026-10-04 00:00:00.000',
          'received_at':'2026-10-04 00:00:00.000','client_occurred_at':None,'is_effective':1,
          'state_before':None if kind=='resource_view' else 'not_started','state_after':None if kind=='resource_view' else 'in_progress'}
    item.update(changes)
    semantic=[item['schema_version'],item['user_id'],item['resource_id'],item['event_type']]
    item['request_fingerprint']=hashlib.sha256(json.dumps(semantic,separators=(',',':')).encode()).hexdigest()
    return item


def dataframe(session,records):
    columns=[c for c,_ in TABLE_COLUMNS['learning_events']]
    return session.createDataFrame([tuple(r[c] for c in columns) for r in records],schema_for('learning_events'))


def test_damaged_data_cleaning_and_quality(session,tmp_path):
    base=make_event(1)
    conflict=make_event(11,'learning_start')
    records=[base,{**base,'id':101},make_event(2,'learning_start'),
             make_event(3,'learning_complete',state_before='completed',state_after='completed',is_effective=0),
             make_event(4,user_id=None),make_event(5,resource_id=None),make_event(6,kind='alien'),
             make_event(7,occurred_at='bad-time'),make_event(8,user_id=999),make_event(9,event_uuid='bad-uuid'),
             conflict,make_event(12,'learning_start',user_id=2,event_uuid=conflict['event_uuid']),
             make_event(13,received_at='2026-10-04 00:00:01'),make_event(14,schema_version=2),
             make_event(15,session_id='bad-session'),make_event(16,occurred_at='2026-10-04T08:00:00+08:00')]
    users,resources=references(session)
    cleaned,rejected,report=clean_events(dataframe(session,records),users,resources,'2026-10-05 00:00:00')
    try:
        assert (report['input_count'],report['filtered_count'],report['output_count'])==(16,13,3)
        assert report['duplicate_count']==1 and report['no_state_change_count']==1 and report['invalid_count']==11
        expected={'empty_or_invalid_user','empty_or_invalid_resource','invalid_event_type','invalid_authoritative_time',
                  'missing_user_reference','invalid_event_uuid','duplicate_uuid_conflict','time_order','unsupported_schema_version',
                  'invalid_session_uuid','duplicate_event_uuid','no_state_change'}
        assert set(report['primary_reasons'])==expected
        assert report['primary_reasons']['duplicate_uuid_conflict']==2
        assert 'future_authoritative_time' not in report['overlapping_reason_hits']
        assert {r.id for r in cleaned.select('id').collect()}=={1,2,16}
        assert cleaned.filter('id=16').select('occurred_at').first()[0]==datetime(2026,10,4)
        cleaned.write.parquet(str(tmp_path/'cleaned'))
        rejected.write.parquet(str(tmp_path/'rejected'))
        assert session.read.parquet(str(tmp_path/'cleaned')).count()==3
        assert session.read.parquet(str(tmp_path/'rejected')).count()==13
        write_json(ROOT/'outputs/spark-data-pipeline-synthetic-quality.json',
                   {'dataset':'isolated synthetic fault fixture; not MySQL batch',**report,'parquet_round_trip':'passed'})
    finally:
        cleaned.unpersist();rejected.unpersist()


def test_empty_dataframe_round_trip(session,tmp_path):
    users,resources=references(session)
    clean,reject,report=clean_events(dataframe(session,[]),users,resources,'2026-10-05 00:00:00')
    try:
        assert report['input_count']==report['output_count']==report['filtered_count']==0
        clean.write.parquet(str(tmp_path/'empty'))
        assert session.read.parquet(str(tmp_path/'empty')).count()==0
    finally:
        clean.unpersist();reject.unpersist()


def test_course_bridge_uuid_compatibility_and_validation(session,tmp_path):
    def bridge(identity,kind='learning_start',**values):
        return make_event(identity,kind,event_uuid=str(uuid5(NAMESPACE_URL,f'bridge:{identity}')),**values)
    records=[make_event(1),make_event(2,'learning_start'),
        make_event(3,'learning_complete',state_before='in_progress',state_after='completed'),
        make_event(4,'favorite_add',state_before='not_favorited',state_after='favorited'),
        make_event(5,'favorite_remove',state_before='favorited',state_after='not_favorited'),
        bridge(6),bridge(7,'learning_complete',state_before='in_progress',state_after='completed'),
        bridge(8,'resource_view'),bridge(9,'favorite_add',state_before='not_favorited',state_after='favorited'),
        bridge(10,'favorite_remove',state_before='favorited',state_after='not_favorited'),
        bridge(11,event_source='client'),make_event(12,session_id=str(uuid5(NAMESPACE_URL,'session'))),
        bridge(13,state_before='completed',state_after='in_progress'),
        bridge(14,received_at='2026-10-04 00:00:01'),bridge(15,request_fingerprint='0'*64),
        bridge(16,user_id=999),bridge(17,is_effective=0,state_before='in_progress'),
        make_event(18,event_uuid=None),
        bridge(19,event_source=None)]
    # Correct the no-op state; malformed versions/variants remain rejected.
    records[16]['state_after']='in_progress'
    records[14]['request_fingerprint']='0'*64
    for identity,value in [(20,'00000000-0000-3000-8000-000000000001'),
                           (21,'00000000-0000-5000-7000-000000000001')]:
        records.append(make_event(identity,'learning_start',event_uuid=value))
    duplicate=bridge(22);records.extend([duplicate,{**duplicate,'id':23}])
    conflict=bridge(24);records.extend([conflict,{**conflict,'id':25,'resource_version':1}])
    users,resources=references(session)
    cleaned,rejected,report=clean_events(dataframe(session,records),users,resources,'2026-10-05 00:00:00')
    try:
        assert {row.id for row in cleaned.select('id').collect()}=={1,2,3,4,5,6,7,22}
        reasons={row.id:row.quality_reasons for row in rejected.select('id','quality_reasons').collect()}
        for identity in [8,9,10,11,18,19,20,21]:assert 'invalid_event_uuid' in reasons[identity]
        assert 'invalid_session_uuid' in reasons[12]
        for identity,reason in [(13,'invalid_state_semantics'),(14,'time_order'),
                                (15,'invalid_request_fingerprint'),(16,'missing_user_reference'),
                                (17,'no_state_change'),(23,'duplicate_event_uuid'),
                                (24,'duplicate_uuid_conflict'),(25,'duplicate_uuid_conflict')]:
            assert reason in reasons[identity]
        assert report['input_count']==25 and report['output_count']==8 and report['filtered_count']==17
        cleaned.write.parquet(str(tmp_path/'compatible-dwd'))
        assert session.read.parquet(str(tmp_path/'compatible-dwd')).count()==8
    finally:
        cleaned.unpersist();rejected.unpersist()


def test_mysql_snapshot_isolation(session):
    settings=MysqlSettings.from_environment()
    writer=pymysql.connect(host=settings.host,port=settings.port,user=settings.user,password=settings.password,
                           database=settings.database,charset='utf8mb4',autocommit=False)
    inserted=None
    try:
        with snapshot_connection(session,settings) as first:
            initial=int(scalar_row(first,'SELECT COUNT(*) FROM users')[0])
            with writer.cursor() as cursor:
                stamp=datetime.now(timezone.utc).replace(tzinfo=None)
                salt=secrets.token_bytes(16)
                digest=hashlib.scrypt(secrets.token_bytes(32),salt=salt,n=16384,r=8,p=1).hex()
                cursor.execute('INSERT INTO users(username,password_hash,interest_tags,created_at,updated_at) VALUES (%s,%s,%s,%s,%s)',
                  ('sp_'+secrets.token_hex(8),'scrypt:16384:8:1$'+salt.hex()+'$'+digest,'[]',stamp,stamp))
                inserted=cursor.lastrowid
            writer.commit()
            assert int(scalar_row(first,'SELECT COUNT(*) FROM users')[0])==initial
        with snapshot_connection(session,settings) as second:
            assert int(scalar_row(second,'SELECT COUNT(*) FROM users')[0])==initial+1
        write_json(ROOT/'outputs/spark-data-pipeline-snapshot-isolation.json',
                   {'test':'real concurrent MySQL commit','before_count':initial,'same_snapshot_count':initial,
                    'new_snapshot_count':initial+1,'result':'passed','temporary_user_cleanup':'performed in fixture finally'})
    finally:
        if inserted is not None:
            with writer.cursor() as cursor:cursor.execute('DELETE FROM users WHERE id=%s',(inserted,))
            writer.commit()
        writer.close()


def test_row_limit_no_silent_truncation(session,monkeypatch):
    monkeypatch.setattr(mysql_snapshot,'pipeline_config',lambda:{'max_rows_per_table':1})
    with snapshot_connection(session) as connection:
        with pytest.raises(RuntimeError,match='row limit'):
            read_table(session,connection,'users')


def test_manifest_hash_tamper_guard(tmp_path):
    (tmp_path/'part.parquet').write_bytes(b'original')
    hashes=parquet_files(tmp_path);validate_hashes(tmp_path,hashes)
    (tmp_path/'part.parquet').write_bytes(b'changed')
    with pytest.raises(RuntimeError,match='checksum'):
        validate_hashes(tmp_path,hashes)
    with pytest.raises(RuntimeError,match='escapes'):
        validate_hashes(tmp_path,[{'path':'../outside.parquet','sha256':'unused'}])
    (tmp_path/'part.parquet').write_bytes(b'original')
    (tmp_path/'unexpected.parquet').write_bytes(b'extra')
    with pytest.raises(RuntimeError,match='inventory'):
        validate_hashes(tmp_path,hashes)


def test_incomplete_batch_not_consumed(session,tmp_path,monkeypatch):
    batch='20261004T000000Z_abcdef12'
    write_json(tmp_path/'data/ods'/('batch_id='+batch)/'manifest.json',{'status':'failed'})
    monkeypatch.setattr(clean_job,'ROOT',tmp_path)
    with pytest.raises(RuntimeError,match='incomplete'):
        clean_job.clean(session,batch)
    assert not (tmp_path/'data/dwd').exists()


def test_invalid_batch_path_guard(session):
    with pytest.raises(ValueError,match='batch'):
        clean_job.clean(session,'../outside')
