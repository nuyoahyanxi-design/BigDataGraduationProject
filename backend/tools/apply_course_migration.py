"""Apply only additive migration 005 with existing environment credentials."""
import json
from pathlib import Path
from sqlalchemy import inspect,text
from app.core.config import Settings
from app.database.session import build_engine
root=Path(__file__).resolve().parents[2]
engine=build_engine(Settings.from_environment())
core=('users','resources','learning_progress','favorites','learning_events')
with engine.connect() as c:
    before={t:c.scalar(text('SELECT COUNT(*) FROM '+t)) for t in core}
    existing=set(inspect(c).get_table_names())
    targets={'course_chapters','chapter_progress','chapter_events'}
    if targets & existing:
        raise SystemExit('Migration target already exists; inspect manually, no existing table modified.')
    sql=(root/'database/migrations/005_create_course_learning.sql').read_text(encoding='utf-8')
    sql='\n'.join(line for line in sql.splitlines() if not line.lstrip().startswith('--'))
    for statement in sql.split(';'):
        if statement.strip():c.execute(text(statement))
    c.commit()
    inspector=inspect(c)
    after={t:c.scalar(text('SELECT COUNT(*) FROM '+t)) for t in core}
    assert before==after
    result={'migration':'005_create_course_learning.sql','before':before,'after':after,'tables':{
        t:{'columns':[col['name'] for col in inspector.get_columns(t)],'pk':inspector.get_pk_constraint(t),
           'foreign_keys':inspector.get_foreign_keys(t),'indexes':inspector.get_indexes(t),
           'charset':c.execute(text('SELECT TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=:t'),{'t':t}).scalar()} for t in targets}}
(root/'outputs/course-learning-migration-evidence.json').write_text(json.dumps(result,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'migration':'005','new_tables':sorted(targets),'core_counts_unchanged':before==after}))
engine.dispose()
