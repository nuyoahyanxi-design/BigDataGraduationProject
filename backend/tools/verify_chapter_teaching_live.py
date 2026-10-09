"""Read-only HTTP check using the existing JWT vault, without passwords or Key output."""
import argparse
import json
import os
import subprocess
import urllib.request
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.core.security import AuthSettings, issue_token
from app.database.session import build_engine
from app.models import User

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--seed', choices=['course-teaching-content.json', 'formal-course-chapters.json'], default='course-teaching-content.json')
args = parser.parse_args()
if not os.environ.get('JWT_SECRET'):
    source = """import sys
sys.path.insert(0,r'D:\BigDataGraduationProject\environments\mysql-admin-tools')
from keyring.backends.Windows import WinVaultKeyring
value=WinVaultKeyring().get_password('BigDataGraduationProject/JWT','backend')
if value is None: raise SystemExit(2)
print(value)
"""
    result = subprocess.run(['/mnt/c/Program Files/Python312/python.exe', '-c', source], capture_output=True, text=True)
    if result.returncode or not result.stdout.strip(): raise SystemExit('Existing signing credential unavailable')
    os.environ['JWT_SECRET'] = result.stdout.strip()
    del result
engine = build_engine(Settings.from_environment())
try:
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.username == 'student_demo', User.status == 'active'))
        if user is None: raise SystemExit('Existing student_demo required; no accounts changed')
        token = issue_token(user, AuthSettings.from_environment())
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    seed = json.loads((root / 'database/seeds' / args.seed).read_text(encoding='utf-8'))
    from app.models import Resource
    results = []
    with Session(engine) as db:
        for course in seed:
            rid = db.scalar(select(Resource.id).where(Resource.title == course['title'], Resource.status == 'published'))
            request = urllib.request.Request(f'http://127.0.0.1:5173/api/resources/{rid}/course', headers={'Authorization': 'Bearer ' + token})
            try:
                with opener.open(request, timeout=10) as response:
                    body = json.load(response)
                chapters = body.get('chapters', [])
                passed = len(chapters) == 5 and all(all(ch.get(field) == expected[field] for field in ('content','learning_objectives','example_code','exercises','video_url')) for ch, expected in zip(chapters, course['chapters'], strict=True))
                results.append({'resource_id': rid, 'chapters': len(chapters), 'complete_teaching_fields': passed})
            except Exception as error:
                results.append({'resource_id': rid, 'complete_teaching_fields': False, 'error_type': type(error).__name__})
    del token
finally:
    engine.dispose()
report_name = 'formal-course-live-api-verification.json' if args.seed == 'formal-course-chapters.json' else 'course-teaching-live-api-verification.json'
(root / 'outputs' / report_name).write_text(json.dumps(results, indent=2), encoding='utf-8')
print(json.dumps({'courses': len(results), 'passed': sum(item['complete_teaching_fields'] for item in results), 'readonly': True}))
if not all(item['complete_teaching_fields'] for item in results): raise SystemExit(1)
