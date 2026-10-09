from datetime import datetime,timezone
from uuid import uuid4

from pyspark.sql import functions as F
from spark.utils.config import ROOT, MysqlSettings
from spark.utils.mysql_snapshot import snapshot_connection,scalar_row,read_table
from spark.utils.schemas import TABLE_COLUMNS
from spark.utils.files import write_json,parquet_files


def extract(spark):
    settings=MysqlSettings.from_environment()
    batch=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid4().hex[:8]
    directory=ROOT/'data/ods'/('batch_id='+batch)
    directory.mkdir(parents=True,exist_ok=False)
    manifest={'batch_id':batch,'status':'extracting','source_system':'mysql','source_database':settings.database,
              'reader':'PySpark JVM JDBC single-connection snapshot','tables':{}}
    write_json(directory/'manifest.json',manifest)
    try:
        with snapshot_connection(spark,settings) as connection:
            cutoff,version=scalar_row(connection,'SELECT UTC_TIMESTAMP(3), VERSION()')
            manifest.update(snapshot_at=cutoff,source_version=version,spark_version=spark.version,
                            isolation='REPEATABLE READ / WITH CONSISTENT SNAPSHOT / READ ONLY')
            frames={table:read_table(spark,connection,table) for table in TABLE_COLUMNS}
        for table,frame in frames.items():
            enriched=(frame.withColumn('_batch_id',F.lit(batch)).withColumn('_snapshot_at',F.lit(cutoff).cast('timestamp'))
                      .withColumn('_source_database',F.lit(settings.database)).withColumn('_source_table',F.lit(table)))
            count=enriched.count()
            path=directory/table
            enriched.coalesce(1).write.mode('errorifexists').parquet(str(path))
            reread=spark.read.parquet(str(path))
            if reread.count()!=count or enriched.exceptAll(reread).limit(1).count() or reread.exceptAll(enriched).limit(1).count():
                raise RuntimeError('ODS Parquet round-trip content mismatch')
            manifest['tables'][table]={'rows':count,'source_columns':frame.columns,'schema':enriched.schema.jsonValue(),
                                       'files':parquet_files(path),'round_trip':'passed'}
        manifest['received_watermark']=frames['learning_events'].agg(F.max('received_at')).first()[0]
        manifest['status']='completed'
        write_json(directory/'manifest.json',manifest)
        return batch,manifest
    except Exception:
        manifest['status']='failed'
        write_json(directory/'manifest.json',manifest)
        raise
