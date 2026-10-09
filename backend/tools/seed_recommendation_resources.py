"""Authorized local maintenance via real authenticated API routes, no direct inserts."""
import json
import os
import secrets
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.models import User, Resource
from app.core.security import issue_token

root = Path(__file__).resolve().parents[2]
# Isolated in-process API signing key; never shared with the running service.
os.environ['JWT_SECRET'] = secrets.token_urlsafe(48)
created = []
with TestClient(app) as client:
    with app.state.session_factory() as db:
        admin = db.scalar(select(User).where(User.username == 'admin_demo', User.role == 'admin', User.status == 'active'))
        if admin is None:
            raise SystemExit('Active admin_demo is required; no account was modified.')
        headers = {'Authorization': 'Bearer '+issue_token(admin, app.state.auth_settings)}
    for seed in json.loads((root/'database/seeds/recommendation-resources.json').read_text(encoding='utf-8')):
        with app.state.session_factory() as db:
            existing = list(db.scalars(select(Resource).where(Resource.title == seed['title'])))
            if len(existing) > 1 or existing and existing[0].tags != seed['tags']:
                raise SystemExit('Conflicting seed title; existing data preserved.')
            rid = existing[0].id if existing else None
            status = existing[0].status if existing else None
        if rid is None:
            response = client.post('/api/resources', headers=headers, json=dict(seed, resource_type='document', difficulty=1,
                                   source_name='本项目自编教学种子', license_note='本项目自编内容，仅作教学演示'))
            if response.status_code != 201:
                raise SystemExit('Seed API creation failed; inspect validation without credentials.')
            rid = response.json()['id']
            status = 'draft'
        if status != 'published':
            response = client.patch(f'/api/resources/{rid}/status', headers=headers, json={'status':'published'})
            if response.status_code != 200:
                raise SystemExit('Seed API publication failed; created resource retained.')
        created.append({'resource_id':rid,'title':seed['title'],'tags':seed['tags'],'status':'published','already_existed':bool(existing)})
(root/'outputs/recommendation-resource-seed-report.json').write_text(json.dumps(created,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(created,ensure_ascii=False))
