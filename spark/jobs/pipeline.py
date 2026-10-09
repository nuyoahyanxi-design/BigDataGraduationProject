from spark.jobs.extract import extract
from spark.jobs.clean import clean
from spark.jobs.quality import quality
from spark.utils.config import ROOT
from spark.utils.files import write_json
from spark.utils.session import build_spark


def run(spark):
    batch,manifest=extract(spark)
    clean(spark,batch)
    report=quality(spark,batch)
    write_json(ROOT/'outputs/spark-data-pipeline-latest.json',
               {'batch_id':batch,'status':'completed','quality_report':str(ROOT/'outputs/spark-data-pipeline'/batch/'quality-report.json'),
                'ods':str(ROOT/'data/ods'/('batch_id='+batch)), 'dwd':str(ROOT/'data/dwd'/('batch_id='+batch))})
    return report


if __name__=='__main__':
    session=None
    try:
        session=build_spark()
        report=run(session)
        print(f"Pipeline completed: batch={report['batch_id']}, input={report['input_count']}, filtered={report['filtered_count']}, output={report['output_count']}")
    except Exception as error:
        print(f'Pipeline failed ({type(error).__name__}); no successful latest batch was published')
        raise SystemExit(1) from None
    finally:
        if session is not None:session.stop()
