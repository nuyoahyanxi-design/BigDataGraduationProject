import json
import re
from spark.utils.config import ROOT
from spark.utils.cleaning import clean_events
from spark.utils.files import write_json,parquet_files,validate_hashes


def clean(spark,batch):
    if not re.fullmatch(r'\d{8}T\d{6}Z_[0-9a-f]{8}',batch):
        raise ValueError('Invalid batch identifier')
    source=ROOT/'data/ods'/('batch_id='+batch)
    manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    if manifest['status']!='completed':
        raise RuntimeError('ODS snapshot is incomplete')
    for table,record in manifest['tables'].items():
        validate_hashes(source/table,record['files'])
    target=ROOT/'data/dwd'/('batch_id='+batch)
    target.mkdir(parents=True,exist_ok=False)
    status={'batch_id':batch,'status':'cleaning'}
    write_json(target/'manifest.json',status)
    try:
        events=spark.read.parquet(str(source/'learning_events'))
        users=spark.read.parquet(str(source/'users'))
        resources=spark.read.parquet(str(source/'resources'))
        cleaned,rejected,report=clean_events(events,users,resources,manifest['snapshot_at'])
        try:
            for name,frame in [('learning_events',cleaned),('learning_events_rejected',rejected)]:
                frame.coalesce(1).write.mode('errorifexists').parquet(str(target/name))
                readback=spark.read.parquet(str(target/name))
                if frame.count()!=readback.count() or frame.exceptAll(readback).limit(1).count() or readback.exceptAll(frame).limit(1).count():
                    raise RuntimeError('DWD Parquet round-trip content mismatch')
                status[name]={'rows':frame.count(),'schema':frame.schema.jsonValue(),'files':parquet_files(target/name),'round_trip':'passed'}
            if 'chapter_events' in manifest['tables']:
                from spark.utils.chapter_analytics import clean_chapters
                ce,cr,cq=clean_chapters(spark.read.parquet(str(source/'chapter_events')),users,resources,spark.read.parquet(str(source/'course_chapters')),manifest['snapshot_at'])
                try:
                    for name,frame in [('chapter_events',ce),('chapter_events_rejected',cr)]:
                        frame.coalesce(1).write.mode('errorifexists').parquet(str(target/name))
                        rb=spark.read.parquet(str(target/name))
                        if frame.count()!=rb.count() or frame.exceptAll(rb).limit(1).count() or rb.exceptAll(frame).limit(1).count():
                            raise RuntimeError('Chapter DWD round-trip mismatch')
                        status[name]={'rows':frame.count(),'files':parquet_files(target/name),'round_trip':'passed'}
                    status['chapter_quality']=cq
                    from spark.utils.progress import derive_progress,RULE
                    canonical=derive_progress(spark.read.parquet(str(source/'learning_progress')),spark.read.parquet(str(source/'course_chapters')),spark.read.parquet(str(source/'chapter_progress')),users,manifest['snapshot_at'])
                    canonical.coalesce(1).write.mode('errorifexists').parquet(str(target/'effective_progress'))
                    rb=spark.read.parquet(str(target/'effective_progress'))
                    if canonical.count()!=rb.count() or canonical.exceptAll(rb).limit(1).count() or rb.exceptAll(canonical).limit(1).count():
                        raise RuntimeError('Canonical progress round-trip mismatch')
                    status['effective_progress']={'rows':rb.count(),'files':parquet_files(target/'effective_progress'),'round_trip':'passed'}
                    status['progress_rule']=RULE
                finally:
                    ce.unpersist();cr.unpersist()
            status.update(status='completed',quality=report,snapshot_at=manifest['snapshot_at'])
            write_json(target/'manifest.json',status)
            return report
        finally:
            cleaned.unpersist();rejected.unpersist()
    except Exception:
        status['status']='failed';write_json(target/'manifest.json',status)
        raise
