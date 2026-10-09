"""Seed authorized courses through authenticated chapter APIs; preserve existing data."""
import json,os,secrets
from pathlib import Path
from sqlalchemy import select
from fastapi.testclient import TestClient
from app.main import app
from app.models import User,Resource,CourseChapter
from app.core.security import issue_token
root=Path(__file__).resolve().parents[2]
os.environ['JWT_SECRET']=secrets.token_urlsafe(48)
report=[]
with TestClient(app) as client:
    with app.state.session_factory() as db:
        admin=db.scalar(select(User).where(User.username=='admin_demo',User.role=='admin',User.status=='active'))
        if admin is None:raise SystemExit('Active admin_demo required; no accounts changed')
        headers={'Authorization':'Bearer '+issue_token(admin,app.state.auth_settings)}
    for course in json.loads((root/'database/seeds/course-chapters.json').read_text(encoding='utf-8')):
        with app.state.session_factory() as db:
            resources=list(db.scalars(select(Resource).where(Resource.title==course['title'],Resource.status=='published')))
            if len(resources)!=1:raise SystemExit('Exactly one published seed resource required; no resource overwritten')
            rid=resources[0].id
        ids=[]
        for chapter in course['chapters']:
            with app.state.session_factory() as db:
                existing=db.scalar(select(CourseChapter).where(CourseChapter.resource_id==rid,CourseChapter.position==chapter['position']))
                if existing:
                    if any(getattr(existing,key)!=value for key,value in chapter.items()):raise SystemExit('Seed chapter conflict; preserved existing content')
                    ids.append(existing.id);continue
            response=client.post(f'/api/resources/{rid}/chapters',headers=headers,json=chapter)
            if response.status_code!=201:raise SystemExit('Chapter seed API rejected; inspect validation, no credentials printed')
            ids.append(response.json()['id'])
        report.append({'resource_id':rid,'title':course['title'],'chapter_ids':ids,'video':'/videos/demo.mp4','video_file_created':False})
(root/'outputs/course-learning-seed-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
