"""Apply additive migration 007; never alter existing tables or rows."""
import json
from pathlib import Path
from sqlalchemy import inspect, text
from app.core.config import Settings
from app.database.session import build_engine
from tools.seed_formal_course_chapters import schema_snapshot, rows_snapshot, protected_snapshot
from app.models import AICourseContext

ROOT = Path(__file__).resolve().parents[2]
engine = build_engine(Settings.from_environment())
try:
    with engine.connect() as connection:
        before = protected_snapshot(connection)
        chapters = rows_snapshot(connection)
        schema = schema_snapshot(connection)
        exists = 'ai_course_contexts' in inspect(connection).get_table_names()
        if not exists:
            sql = (ROOT/'database/migrations/007_create_ai_course_contexts.sql').read_text(encoding='utf-8')
            connection.execute(text(sql.strip().rstrip(';')))
            connection.commit()
        inspector = inspect(connection)
        assert {c['name'] for c in inspector.get_columns('ai_course_contexts')} == {c.name for c in AICourseContext.__table__.columns}
        assert inspector.get_pk_constraint('ai_course_contexts')['constrained_columns'] == ['qa_record_id']
        assert any(f['referred_table']=='ai_qa_records' and f['constrained_columns']==['qa_record_id'] for f in inspector.get_foreign_keys('ai_course_contexts'))
        assert 'ck_ai_course_references' in {c['name'] for c in inspector.get_check_constraints('ai_course_contexts')}
        assert connection.scalar(text("SELECT TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='ai_course_contexts'")) == 'utf8mb4_unicode_ci'
        after = schema_snapshot(connection)
        unchanged = before == protected_snapshot(connection) and chapters == rows_snapshot(connection)
        old_schema = all(after[name]==digest for name,digest in schema.items())
        assert unchanged and old_schema
        result = {'migration':'007_create_ai_course_contexts.sql','executed':not exists,'pk_fk_checks_charset':'passed',
                  'existing_schema_unchanged':old_schema,'existing_data_unchanged':unchanged}
    (ROOT/'outputs/course-ai-migration-evidence.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
finally:
    engine.dispose()
