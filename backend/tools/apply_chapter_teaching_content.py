"""Apply migration 006 and refresh only the authorized demo chapters."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import inspect, select, text, update
from app.core.config import Settings
from app.database.session import build_engine
from app.models import CourseChapter, Resource
from app.schemas.courses import ChapterWrite

ROOT = Path(__file__).resolve().parents[2]
PROTECTED = ('users', 'resources', 'learning_progress', 'favorites', 'learning_events',
             'chapter_progress', 'chapter_events', 'user_profiles', 'recommendation_results')
FIELDS = ('content', 'learning_objectives', 'example_code', 'exercises', 'video_url')
NEW_FIELDS = {'learning_objectives', 'example_code', 'exercises'}

def protected_snapshot(connection):
    result = {}
    for table in PROTECTED:
        columns = '*' if table != 'users' else 'id,username,nickname,role,status,interest_tags,created_at,updated_at'
        rows = [dict(row) for row in connection.execute(text(f'SELECT {columns} FROM {table}')).mappings()]
        serialized = sorted(json.dumps(row, sort_keys=True, default=str, ensure_ascii=False) for row in rows)
        digest = hashlib.sha256('\n'.join(serialized).encode()).hexdigest()
        result[table] = {'count': len(rows), 'digest': digest}
    return result

def load_seed():
    data = json.loads((ROOT / 'database/seeds/course-teaching-content.json').read_text(encoding='utf-8'))
    expected = ['Spark RDD基础教程', 'PySpark数据处理实践', 'Python机器学习基础']
    if [c['title'] for c in data] != expected or any(len(c['chapters']) != 5 for c in data):
        raise RuntimeError('Unexpected teaching seed scope')
    for course in data:
        if [c['position'] for c in course['chapters']] != list(range(1, 6)):
            raise RuntimeError('Unexpected chapter positions')
        for chapter in course['chapters']:
            ChapterWrite.model_validate(chapter)
            if chapter['video_url'] != '/demo/video.mp4':
                raise RuntimeError('Unexpected video placeholder')
    return data

def migrate(engine):
    with engine.connect() as connection:
        before = protected_snapshot(connection)
        columns = {c['name'] for c in inspect(connection).get_columns('course_chapters')}
        present = columns & NEW_FIELDS
        if present and present != NEW_FIELDS:
            raise RuntimeError('Partial migration detected; inspect manually')
        executed = not present
        if executed:
            sql = (ROOT / 'database/migrations/006_add_chapter_teaching_content.sql').read_text(encoding='utf-8')
            sql = '\n'.join(line for line in sql.splitlines() if not line.lstrip().startswith('--'))
            connection.execute(text(sql.strip().rstrip(';')))
            connection.commit()
        schema = inspect(connection)
        checks = {c['name'] for c in schema.get_check_constraints('course_chapters')}
        current_columns = {c['name']: c for c in schema.get_columns('course_chapters')}
        assert NEW_FIELDS <= set(current_columns)
        assert {'ck_chapter_objectives', 'ck_chapter_exercises'} <= checks
        assert all(current_columns[name]['nullable'] for name in NEW_FIELDS)
        assert all(str(current_columns[name]['type']).upper() == 'JSON' for name in ('learning_objectives', 'exercises'))
        assert 'LONGTEXT' in str(current_columns['example_code']['type']).upper()
        after = protected_snapshot(connection)
        assert before == after
        return {'migration': '006', 'executed': executed, 'added_fields': sorted(NEW_FIELDS),
                'protected_before': before, 'protected_after': after, 'checks': sorted(checks)}

def prepare_updates(connection, seed):
    updates = []
    summary = []
    for course in seed:
        resources = connection.execute(select(Resource.id).where(Resource.title == course['title'], Resource.status == 'published')).scalars().all()
        if len(resources) != 1:
            raise RuntimeError('Expected one existing published demo resource per course')
        rid = resources[0]
        chapters = connection.execute(select(CourseChapter.__table__).where(CourseChapter.resource_id == rid).order_by(CourseChapter.position).with_for_update()).mappings().all()
        if len(chapters) != 5:
            raise RuntimeError('Expected exactly five existing chapters; no syllabus changes allowed')
        for existing, chapter in zip(chapters, course['chapters'], strict=True):
            if (existing['title'], existing['position'], existing['knowledge_tags']) != (chapter['title'], chapter['position'], chapter['knowledge_tags']):
                raise RuntimeError('Demo chapter identity or tags differ; no changes made')
            values = {name: chapter[name] for name in FIELDS}
            if any(existing[name] != values[name] for name in FIELDS):
                updates.append({'chapter_id': existing['id'], 'before': {name: existing[name] for name in FIELDS}, 'after': values})
            summary.append({'resource_id': rid, 'chapter_id': existing['id'], 'title': existing['title'],
                            'body_characters': len(chapter['content']), 'objectives': len(chapter['learning_objectives']),
                            'code_lines': len(chapter['example_code'].splitlines()), 'exercises': len(chapter['exercises']),
                            'video_url': chapter['video_url']})
    return updates, summary

def seed_content(engine):
    seed = load_seed()
    backup = None
    with engine.begin() as connection:
        before = protected_snapshot(connection)
        updates, summary = prepare_updates(connection, seed)
        if updates:
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            backup = ROOT / f'outputs/course-teaching-content-backup-{stamp}.json'
            backup.write_text(json.dumps([{'chapter_id': u['chapter_id'], **u['before']} for u in updates], ensure_ascii=False, indent=2), encoding='utf-8')
            for item in updates:
                connection.execute(update(CourseChapter.__table__).where(CourseChapter.id == item['chapter_id']).values(**item['after']))
        assert protected_snapshot(connection) == before
    with engine.connect() as connection:
        remaining, _ = prepare_updates(connection, seed)
        assert not remaining
        after = protected_snapshot(connection)
        assert before == after
    return {'updated_chapters': len(updates), 'chapter_count': len(summary), 'chapters': summary,
            'backup': str(backup) if backup else None, 'protected_before': before, 'protected_after': after}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--migrate', action='store_true')
    parser.add_argument('--seed', action='store_true')
    args = parser.parse_args()
    engine = build_engine(Settings.from_environment())
    try:
        report = {}
        if args.migrate: report['migration'] = migrate(engine)
        if args.seed: report['seed'] = seed_content(engine)
        if not report:
            with engine.connect() as connection:
                remaining, chapters = prepare_updates(connection, load_seed())
                report = {'verified_chapters': len(chapters), 'content_matches_seed': not remaining,
                          'protected_snapshot': protected_snapshot(connection)}
        (ROOT / 'outputs/course-teaching-content-data-evidence.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'migration_executed': report.get('migration', {}).get('executed'),
                          'updated_chapters': report.get('seed', {}).get('updated_chapters'),
                          'verified_chapters': report.get('verified_chapters'), 'evidence_saved': True}))
    finally:
        engine.dispose()

if __name__ == '__main__':
    main()
