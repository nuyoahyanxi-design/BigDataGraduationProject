"""Publish only approved MySQL/HDFS chapters via existing authenticated APIs."""
import argparse
import hashlib
import json
import os
import re
import secrets
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text
from app.main import app
from app.models import User, Resource, CourseChapter, ChapterProgress
from app.core.security import issue_token
from app.schemas.courses import ChapterWrite
from tools.apply_chapter_teaching_content import protected_snapshot

ROOT = Path(__file__).resolve().parents[2]
APPROVED = {1071: 'MySQL数据库基础', 1070: 'Hadoop HDFS入门'}

def load_seed(path=None):
    data = json.loads(Path(path or ROOT / 'database/seeds/formal-course-chapters.json').read_text(encoding='utf-8'))
    if len(data) != 2 or {c['resource_id']: c['title'] for c in data} != APPROVED:
        raise RuntimeError('Only the two approved formal courses may be seeded')
    for course in data:
        if [ch['position'] for ch in course['chapters']] != [1, 2, 3, 4, 5]:
            raise RuntimeError('Exactly five ordered chapters are required')
        for chapter in course['chapters']:
            ChapterWrite.model_validate(chapter)
            if not chapter['learning_objectives'] or not chapter['example_code'] or not chapter['exercises'] or chapter['video_url'] != '/demo/video.mp4':
                raise RuntimeError('Complete teaching fields and fixed video placeholder required')
    return data

def schema_snapshot(connection):
    schemas = {}
    for table in sorted(inspect(connection).get_table_names()):
        escaped = table.replace('`', '``')
        ddl = connection.execute(text(f'SHOW CREATE TABLE `{escaped}`')).one()[1]
        # Inserted fixture/seed rows advance this counter without altering structure.
        ddl = re.sub(r'AUTO_INCREMENT=\d+\s*', '', ddl)
        schemas[table] = hashlib.sha256(ddl.encode()).hexdigest()
    return schemas

def verify_schema(connection):
    inspector = inspect(connection)
    columns = {c['name']: c for c in inspector.get_columns('course_chapters')}
    if set(columns) != {c.name for c in CourseChapter.__table__.columns}:
        raise RuntimeError('Chapter schema differs from existing models; no migration will be executed')
    if not all(str(columns[name]['type']).upper() == 'JSON' for name in ('knowledge_tags', 'learning_objectives', 'exercises')):
        raise RuntimeError('Expected teaching JSON fields from migration 006')
    checks = {c['name'] for c in inspector.get_check_constraints('course_chapters')}
    if not {'ck_chapter_objectives', 'ck_chapter_exercises', 'ck_chapter_tags'} <= checks:
        raise RuntimeError('Expected migration 005/006 checks')
    primary_key = inspector.get_pk_constraint('course_chapters')['constrained_columns']
    indexes = inspector.get_indexes('course_chapters')
    names = {i['name'] for i in indexes if i['unique']}
    foreign_keys = inspector.get_foreign_keys('course_chapters')
    if primary_key != ['id'] or not {'uk_chapter_position', 'uk_chapter_resource'} <= names:
        raise RuntimeError('Chapter identity or order constraints differ')
    if not any(f['constrained_columns'] == ['resource_id'] and f['referred_table'] == 'resources' for f in foreign_keys):
        raise RuntimeError('Missing resource foreign key')
    collation = connection.scalar(text("SELECT TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='course_chapters'"))
    if not collation.startswith('utf8mb4_'): raise RuntimeError('Expected utf8mb4 chapter table')
    return {'migration_005_006_verified': True, 'ddl_executed': False, 'columns': sorted(columns),
            'checks': sorted(checks), 'primary_key': primary_key, 'unique_indexes': sorted(names), 'collation': collation}

def rows_snapshot(db):
    rows = db.execute(select(CourseChapter.__table__)).mappings().all()
    return {r['id']: hashlib.sha256(json.dumps(dict(r), default=str, sort_keys=True, ensure_ascii=False).encode()).hexdigest() for r in rows}

def excluded_resources(db):
    rows = db.scalars(select(Resource)).all()
    ids = [r.id for r in rows if re.sub(r'\s+', '', r.title).startswith('Spark真实浏览器联调演示资源')]
    return {rid: list(db.scalars(select(CourseChapter.id).where(CourseChapter.resource_id == rid))) for rid in ids}

def prepare_plan(db, seed):
    plan = []
    for course in seed:
        resource = db.get(Resource, course['resource_id'])
        if resource is None or resource.title != course['title'] or resource.status != 'published':
            raise RuntimeError('Approved resource identity or publication status differs')
        existing = {ch.position: ch for ch in db.scalars(select(CourseChapter).where(CourseChapter.resource_id == resource.id))}
        if not set(existing) <= {1, 2, 3, 4, 5}:
            raise RuntimeError('Unexpected existing chapters; nothing overwritten')
        missing = []
        for chapter in course['chapters']:
            old = existing.get(chapter['position'])
            normalized = ChapterWrite.model_validate(chapter).model_dump()
            if old is not None:
                if any(getattr(old, field) != value for field, value in normalized.items()):
                    raise RuntimeError('Existing chapter conflict; no overwrite allowed')
            else: missing.append(normalized)
        if missing and db.scalar(select(ChapterProgress.user_id).join(CourseChapter).where(CourseChapter.resource_id == resource.id).limit(1)):
            raise RuntimeError('Syllabus frozen by existing chapter learning; no bypass allowed')
        plan.append((resource.id, missing))
    return plan

def run(publish=False):
    seed = load_seed()
    os.environ['JWT_SECRET'] = secrets.token_urlsafe(48)
    report = {'published': publish, 'new_chapter_ids': [], 'structure_migration_executed': False}
    try:
        with TestClient(app) as client:
            with app.state.session_factory() as db:
                connection = db.connection()
                report['migration_validation'] = verify_schema(connection)
                report['schema_before'] = schema_snapshot(connection)
                report['protected_before'] = protected_snapshot(connection)
                original = rows_snapshot(db)
                report['excluded_before'] = excluded_resources(db)
                plan = prepare_plan(db, seed)
                admin = db.scalar(select(User).where(User.username == 'admin_demo', User.role == 'admin', User.status == 'active'))
                learner = db.scalar(select(User).where(User.username == 'student_demo', User.role == 'learner', User.status == 'active'))
                if admin is None or learner is None: raise RuntimeError('Existing active demo identities required')
                admin_headers = {'Authorization': 'Bearer ' + issue_token(admin, app.state.auth_settings)}
                learner_headers = {'Authorization': 'Bearer ' + issue_token(learner, app.state.auth_settings)}
            if publish:
                for rid, missing in plan:
                    for chapter in missing:
                        response = client.post(f'/api/resources/{rid}/chapters', headers=admin_headers, json=chapter)
                        if response.status_code != 201: raise RuntimeError(f'Existing chapter API rejected publication (HTTP {response.status_code}); created chapters retained')
                        report['new_chapter_ids'].append(response.json()['id'])
            report['courses'] = []
            for course in seed:
                response = client.get(f'/api/resources/{course["resource_id"]}/course', headers=learner_headers)
                if response.status_code != 200: raise RuntimeError('Learner course query failed')
                chapters = response.json()['chapters']
                complete = len(chapters) == 5 and all(all(ch.get(k) == v for k, v in expected.items()) for ch, expected in zip(chapters, course['chapters'], strict=True))
                report['courses'].append({'resource_id': course['resource_id'], 'title': course['title'],
                                          'chapter_ids': [ch['id'] for ch in chapters], 'chapter_count': len(chapters), 'complete_fields': complete})
                if not complete: raise RuntimeError('Course data does not match complete teaching seed')
            with app.state.session_factory() as db:
                connection = db.connection()
                report['schema_after'] = schema_snapshot(connection)
                report['protected_after'] = protected_snapshot(connection)
                current = rows_snapshot(db)
                report['excluded_after'] = excluded_resources(db)
                assert report['schema_before'] == report['schema_after']
                assert report['protected_before'] == report['protected_after']
                assert all(current.get(cid) == digest for cid, digest in original.items())
                assert set(current) - set(original) == set(report['new_chapter_ids'])
                assert report['excluded_before'] == report['excluded_after']
                report['existing_chapters_unchanged'] = True
        report['success'] = True
    except Exception as error:
        report['success'] = False
        report['error_type'] = type(error).__name__
        raise
    finally:
        name = 'formal-course-chapters-publication.json' if publish else 'formal-course-chapters-verification.json'
        (ROOT / 'outputs' / name).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'success': report['success'], 'added': len(report['new_chapter_ids']),
                      'courses': report['courses'], 'excluded_resources': sorted(report['excluded_after'])}, ensure_ascii=False))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--publish', action='store_true')
    run(parser.parse_args().publish)
