from pyspark.sql import SparkSession
import os
import time
from spark.utils.config import ROOT, pipeline_config


def build_spark(name='graduation-data-pipeline'):
    # Scope timezone to this process, not the WSL or Windows system setting.
    os.environ['TZ']='UTC'
    time.tzset()
    config=pipeline_config()
    jar=ROOT/config['jdbc_jar']
    if not jar.is_file():
        raise RuntimeError('MySQL JDBC driver file is missing')
    session=(SparkSession.builder.appName(name).master(config['master'])
             .config('spark.driver.memory',config['driver_memory'])
             .config('spark.driver.extraClassPath',str(jar))
             .config('spark.jars',str(jar))
             .config('spark.sql.session.timeZone','UTC')
             .config('spark.executorEnv.TZ','UTC')
             .config('spark.sql.ansi.enabled','false')
             .config('spark.sql.legacy.timeParserPolicy','CORRECTED')
             .config('spark.sql.shuffle.partitions',config['shuffle_partitions'])
             .config('spark.ui.enabled','false')
             .config('spark.sql.parquet.compression.codec','snappy')
             .getOrCreate())
    session.sparkContext.setLogLevel('ERROR')
    return session
