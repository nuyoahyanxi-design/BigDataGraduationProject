"""Synthetic fixtures test the audit tool only; never treated as real data."""
import csv
import io
import json
import zipfile
import pytest
from scripts.audit_oulad_source import audit, EXPECTED

ROWS={
 'courses':{'code_module':'AAA','code_presentation':'2013J','module_presentation_length':'200'},
 'studentInfo':{'code_module':'AAA','code_presentation':'2013J','id_student':'100','final_result':'Pass'},
 'vle':{'code_module':'AAA','code_presentation':'2013J','id_site':'10','activity_type':'resource','week_from':'','week_to':''},
 'assessments':{'code_module':'AAA','code_presentation':'2013J','id_assessment':'20','assessment_type':'TMA','date':'?','weight':'100'},
 'studentRegistration':{'code_module':'AAA','code_presentation':'2013J','id_student':'100','date_registration':'-5','date_unregistration':''},
 'studentAssessment':{'id_assessment':'20','id_student':'100','date_submitted':'10','is_banked':'0','score':'80'},
 'studentVle':{'code_module':'AAA','code_presentation':'2013J','id_student':'100','id_site':'10','date':'-2','sum_click':'3'},
}
def archive(tmp_path,broken=False):
 path=tmp_path/'synthetic-test-only.zip'
 with zipfile.ZipFile(path,'w') as z:
  for table,row in ROWS.items():
   row=dict(row)
   if broken and table=='studentVle':row['id_student']='999';row['id_site']='999'
   stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(row));writer.writeheader();writer.writerow(row)
   if table=='studentInfo':writer.writerow(row)
   z.writestr(table+'.csv',stream.getvalue())
 return path

def test_unique_students_not_row_count_and_relative_date_preserved(tmp_path):
 result=audit(archive(tmp_path),tmp_path/'output')
 assert result['tables']['studentInfo']['rows']==2
 assert result['unique_students']==1 and result['student_module_enrolments']==1
 assert result['tables']['studentVle']['relative_day_min']==-2
 assert result['tables']['studentVle']['total_clicks']==3
 assert result['tables']['vle']['missing_values']['week_to']==1
 assert result['tables']['assessments']['missing_values']['date']==1
 assert result['status']=='audited_with_findings'
 assert result['quality_findings']['duplicate_enrolment_rows']==1

def test_broken_relationship_is_reported_not_silently_deleted(tmp_path):
 result=audit(archive(tmp_path,True),tmp_path/'output')
 assert result['status']=='audited_with_findings'
 assert result['quality_findings']['interaction_missing_enrolment']==1
 assert result['quality_findings']['interaction_missing_resource']==1
 assert result['tables']['studentVle']['rows']==1

def test_incomplete_archive_rejected(tmp_path):
 path=tmp_path/'invalid.zip'
 with zipfile.ZipFile(path,'w') as z:z.writestr('unexpected.csv','a,b\n1,2')
 with pytest.raises(ValueError,match='inventory'):audit(path,tmp_path/'output')
