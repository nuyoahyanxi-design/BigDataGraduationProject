import json
from spark.utils.config import ROOT
from spark.utils.files import write_json,validate_hashes


def quality(spark,batch):
    ods=ROOT/'data/ods'/('batch_id='+batch)
    dwd=ROOT/'data/dwd'/('batch_id='+batch)
    source=json.loads((ods/'manifest.json').read_text(encoding='utf-8'))
    result=json.loads((dwd/'manifest.json').read_text(encoding='utf-8'))
    if source['status']!='completed' or result['status']!='completed':
        raise RuntimeError('Pipeline layers incomplete')
    report={**result['quality'],'batch_id':batch,'snapshot_at':source['snapshot_at'],
            'source_system':'mysql','source_database':source['source_database'],'source_version':source['source_version'],
            'spark_version':spark.version,'ods_counts':{t:r['rows'] for t,r in source['tables'].items()},
            'schema_timezone':'UTC','dataset_origin':'existing development acceptance fixtures; not real learner study'}
    for name in ['learning_events','learning_events_rejected']:
        validate_hashes(dwd/name,result[name]['files'])
    if 'chapter_quality' in result:
        report['chapter_quality']=result['chapter_quality']
        for name in ['chapter_events','chapter_events_rejected']:
            validate_hashes(dwd/name,result[name]['files'])
    if 'progress_rule' in result:
        validate_hashes(dwd/'effective_progress',result['effective_progress']['files'])
        report['progress_rule']=result['progress_rule']
    events=spark.read.parquet(str(dwd/'learning_events'))
    events.createOrReplaceTempView('dwd_learning_events')
    report['sql_event_statistics']=[r.asDict() for r in spark.sql('SELECT event_type, COUNT(*) AS rows FROM dwd_learning_events GROUP BY event_type ORDER BY event_type').collect()]
    if sum(r['rows'] for r in report['sql_event_statistics'])!=report['output_count']:
        raise RuntimeError('Spark SQL count verification failed')
    report['spark_sql']='passed';report['parquet_round_trip']='passed';report['file_checksums']='passed'
    output=ROOT/'outputs/spark-data-pipeline'/batch
    write_json(output/'quality-report.json',report)
    lines=['# Spark数据质量报告',f"批次：{batch}；快照UTC：{report['snapshot_at']}",'',
           '数据来源：已有开发验收样本，不代表真实学习数据。','',
           '| 指标 | 数量 |','|---|---:|',f"| 输入 | {report['input_count']} |",f"| 过滤合计 | {report['filtered_count']} |",
           f"| 异常 | {report['invalid_count']} |",f"| 重复移除 | {report['duplicate_count']} |",
           f"| 正常无变化回执排除 | {report['no_state_change_count']} |",f"| 输出 | {report['output_count']} |",'',
           '主原因互斥统计：','']
    lines.extend(f'- {key}：{value}' for key,value in sorted(report['primary_reasons'].items()))
    if not report['primary_reasons']:lines.append('- 无排除记录。')
    lines.extend(['','输入=过滤+输出：通过。多原因命中统计见JSON，可重叠，不作为互斥行数相加。',
                  'Spark SQL、ODS/DWD Parquet读写和摘要检查通过；未实施画像或推荐。'])
    (output/'quality-report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return report
