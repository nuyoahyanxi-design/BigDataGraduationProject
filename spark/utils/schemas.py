from pyspark.sql.types import StructType,StructField,LongType,StringType,IntegerType

# Whitelisted analytical projections. Never select account password hashes.
TABLE_COLUMNS={
 'users': [('id','long'),('role','str'),('status','str'),('interest_tags','str'),('created_at','str'),('updated_at','str')],
 'resources': [('id','long'),('title','str'),('resource_type','str'),('category_code','str'),('tags','str'),('difficulty','int'),('summary','str'),('source_name','str'),('license_note','str'),('status','str'),('version_no','long'),('created_by','long'),('published_at','str'),('created_at','str'),('updated_at','str')],
 'learning_progress': [('user_id','long'),('resource_id','long'),('status','str'),('first_started_at','str'),('completed_at','str'),('updated_at','str')],
 'favorites': [('user_id','long'),('resource_id','long'),('created_at','str')],
 'learning_events': [('id','long'),('event_uuid','str'),('user_id','long'),('resource_id','long'),('event_type','str'),('event_source','str'),('schema_version','int'),('resource_version','long'),('session_id','str'),('occurred_at','str'),('received_at','str'),('client_occurred_at','str'),('is_effective','int'),('state_before','str'),('state_after','str'),('request_fingerprint','str')]
}


def schema_for(table):
    types={'long':LongType(),'int':IntegerType(),'str':StringType()}
    return StructType([StructField(name,types[kind],True) for name,kind in TABLE_COLUMNS[table]])
