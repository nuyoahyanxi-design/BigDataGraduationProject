"""Frozen formal-course scope; never modify the full ODS/DWD history."""
import json
from pyspark.sql import functions as F
from backend.app.core.resource_scope import HIDDEN_IDS,VALIDATION_SOURCE,VALIDATION_LICENSE,SCOPE_RULE,SCOPE_LABEL
from spark.utils.files import validate_hashes

def eligible(resources):
    result=resources.filter(~F.col('id').isin(list(HIDDEN_IDS)))
    if {'source_name','license_note'} <= set(resources.columns):
        validation=F.coalesce((F.col('source_name')==VALIDATION_SOURCE)&(F.col('license_note')==VALIDATION_LICENSE),F.lit(False))
        result=result.filter(~validation)
    return result

def formal_courses(resources,chapters):
    return eligible(resources).filter("status='published'").join(chapters.select(F.col('resource_id').alias('id')).distinct(),'id','left_semi').withColumn('resource_type',F.lit('course'))

def restrict(frame,resources):
    return None if frame is None else frame.join(resources.select(F.col('id').alias('resource_id')),'resource_id','left_semi')

def load_formal(spark,ods):
    manifest=json.loads((ods/'manifest.json').read_text())
    if 'course_chapters' not in manifest['tables']:return None
    for name in ['resources','course_chapters']:validate_hashes(ods/name,manifest['tables'][name]['files'])
    return formal_courses(spark.read.parquet(str(ods/'resources')),spark.read.parquet(str(ods/'course_chapters')))
