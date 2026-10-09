from contextlib import contextmanager

from spark.utils.config import MysqlSettings, pipeline_config
from spark.utils.schemas import TABLE_COLUMNS, schema_for


@contextmanager
def snapshot_connection(spark,settings=None):
    settings=settings or MysqlSettings.from_environment()
    jvm=spark.sparkContext._jvm
    properties=jvm.java.util.Properties()
    properties.setProperty('user',settings.user)
    properties.setProperty('password',settings.password)
    url=(f'jdbc:mysql://{settings.host}:{settings.port}/{settings.database}'
         '?characterEncoding=UTF-8&connectionCollation=utf8mb4_unicode_ci&connectionTimeZone=UTC'
         '&sslMode=DISABLED&allowPublicKeyRetrieval=true&connectTimeout=10000&socketTimeout=30000')
    connection=jvm.com.mysql.cj.jdbc.Driver().connect(url,properties)
    try:
        connection.setAutoCommit(False)
        connection.setTransactionIsolation(4)
        statement=connection.createStatement()
        try:
            statement.execute("SET time_zone = '+00:00'")
            statement.execute('START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY')
        finally:
            statement.close()
        yield connection
    finally:
        connection.rollback()
        connection.close()


def scalar_row(connection,sql):
    statement=connection.createStatement()
    try:
        result=statement.executeQuery(sql)
        try:
            result.next()
            return [result.getString(i+1) for i in range(result.getMetaData().getColumnCount())]
        finally:
            result.close()
    finally:
        statement.close()


def read_table(spark,connection,table):
    columns=TABLE_COLUMNS[table]
    max_rows=pipeline_config()['max_rows_per_table']
    statement=connection.createStatement()
    rows=[]
    try:
        result=statement.executeQuery('SELECT '+','.join('`'+c+'`' for c,_ in columns)+' FROM `'+table+'`')
        try:
            while result.next():
                if len(rows)>=max_rows:
                    raise RuntimeError('Snapshot exceeds per-table row limit; no truncation performed')
                row=[]
                for i,(name,kind) in enumerate(columns):
                    value=result.getString(i+1)
                    if value is not None and kind in ('long','int'):
                        value=int(value)
                        maximum=9223372036854775807 if kind=='long' else 2147483647
                        if not 0<=value<=maximum:
                            raise RuntimeError('Unsigned numeric column exceeds Spark signed type range')
                    row.append(value)
                rows.append(tuple(row))
        finally:
            result.close()
    finally:
        statement.close()
    return spark.createDataFrame(rows,schema_for(table))
