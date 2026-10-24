"""Read-only OULAD archive audit; no database or Spark dependencies."""
import argparse
import collections
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path
from datetime import datetime, timezone

EXPECTED={
 'courses':{'code_module','code_presentation','module_presentation_length'},
 'assessments':{'code_module','code_presentation','id_assessment','assessment_type','date','weight'},
 'studentAssessment':{'id_assessment','id_student','date_submitted','is_banked','score'},
 'studentInfo':{'code_module','code_presentation','id_student','final_result'},
 'studentRegistration':{'code_module','code_presentation','id_student','date_registration','date_unregistration'},
 'vle':{'id_site','code_module','code_presentation','activity_type','week_from','week_to'},
 'studentVle':{'code_module','code_presentation','id_student','id_site','date','sum_click'},
}

def audit(archive, output):
    archive=Path(archive);output=Path(output)
    report={'dataset':'OULAD','source_kind':'external_anonymised_education_data','repository':'UCI Machine Learning Repository','source_url':'https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset','doi':'10.24432/C5KK69','license':'CC BY 4.0','audited_at':datetime.now(timezone.utc).isoformat(),'archive_bytes':archive.stat().st_size,'tables':{},'scope':'Original CSV audit only; not platform users, chapter completion, or recommendation evaluation.'}
    with archive.open('rb') as stream:report['archive_sha256']=hashlib.file_digest(stream,'sha256').hexdigest()
    students=set();enrolments=set();sites=set();course_keys=set();assessment_keys={}
    outcomes=collections.Counter();activities=collections.Counter();module_clicks=collections.Counter();daily=collections.Counter();errors=collections.Counter()
    with zipfile.ZipFile(archive) as z:
        names={Path(i.filename).stem:i for i in z.infolist() if i.filename.lower().endswith('.csv')}
        if 'studentAssessments' in names and 'studentAssessment' not in names:names['studentAssessment']=names.pop('studentAssessments')
        if set(names)!=set(EXPECTED):raise ValueError('Unexpected CSV inventory')
        if sum(i.file_size for i in names.values())>1024**3:raise ValueError('Expanded archive size exceeds audit limit')
        for table in ['courses','studentInfo','vle','assessments','studentRegistration','studentAssessment','studentVle']:
            info=names[table];count=0;missing=collections.Counter();clicks=0;minimum=None;maximum=None
            with z.open(info) as binary:
                reader=csv.DictReader(io.TextIOWrapper(binary,encoding='utf-8-sig',newline=''))
                if not EXPECTED[table]<=set(reader.fieldnames or []):raise ValueError('Missing required source columns: '+table)
                columns=reader.fieldnames
                for row in reader:
                    count+=1
                    for key,value in row.items():
                        if value is None or value.strip() in {'', '?', 'NA', 'N/A', 'NaN', 'nan', 'NULL', 'null'}:missing[key]+=1
                    if table=='courses':course_keys.add((row['code_module'],row['code_presentation']))
                    elif table=='studentInfo':
                        if (row['code_module'],row['code_presentation']) not in course_keys:errors['enrolment_missing_course']+=1
                        if (row['code_module'],row['code_presentation'],row['id_student']) in enrolments:errors['duplicate_enrolment_rows']+=1
                        students.add(row['id_student']);enrolments.add((row['code_module'],row['code_presentation'],row['id_student']));outcomes[row['final_result']]+=1
                    elif table=='vle':sites.add((row['code_module'],row['code_presentation'],row['id_site']));activities[row['activity_type']]+=1
                    elif table=='assessments':assessment_keys[row['id_assessment']]=(row['code_module'],row['code_presentation'])
                    elif table=='studentRegistration':
                        if (row['code_module'],row['code_presentation'],row['id_student']) not in enrolments:errors['registration_missing_enrolment']+=1
                    elif table=='studentAssessment':
                        course=assessment_keys.get(row['id_assessment'])
                        if course is None:errors['assessment_missing_definition']+=1
                        elif (*course,row['id_student']) not in enrolments:errors['assessment_missing_enrolment']+=1
                    elif table=='studentVle':
                        key=(row['code_module'],row['code_presentation'])
                        if (*key,row['id_student']) not in enrolments:errors['interaction_missing_enrolment']+=1
                        if (*key,row['id_site']) not in sites:errors['interaction_missing_resource']+=1
                        try:
                            value=int(row['sum_click']);day=int(row['date'])
                            if value<0:errors['negative_clicks']+=1
                            clicks+=value;module_clicks[row['code_module']]+=value;daily[day]+=value
                            minimum=day if minimum is None else min(minimum,day);maximum=day if maximum is None else max(maximum,day)
                        except ValueError:errors['invalid_numeric_interaction']+=1
            report['tables'][table]={'rows':count,'columns':columns,'missing_values':dict(missing),'uncompressed_bytes':info.file_size,'zip_crc32':format(info.CRC,'08x'),'crc_checked_by_full_read':True}
            if table=='studentVle':report['tables'][table].update(total_clicks=clicks,relative_day_min=minimum,relative_day_max=maximum)
            print(table+': '+str(count)+' rows',flush=True)
    report.update(unique_students=len(students),student_module_enrolments=len(enrolments),unique_modules=len({k[0] for k in course_keys}),module_presentations=len(course_keys),outcomes_by_enrolment=dict(outcomes),resources_by_activity=dict(activities),clicks_by_module=dict(module_clicks),clicks_by_relative_day={str(k):v for k,v in sorted(daily.items())},quality_findings=dict(errors),status='audited' if not errors else 'audited_with_findings')
    output.mkdir(parents=True,exist_ok=True)
    (output/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('archive');parser.add_argument('--output',default='outputs/oulad-intake');args=parser.parse_args();result=audit(args.archive,args.output)
    print(json.dumps({k:result[k] for k in ['status','unique_students','student_module_enrolments','unique_modules','module_presentations','archive_sha256']}))
