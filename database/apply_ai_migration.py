"""Apply only 004; compare all pre-existing schemas and row counts."""
import hashlib
import json
from pathlib import Path
from sqlalchemy import inspect, text
from app.core.config import Settings
from app.database.session import build_engine
from app.models.ai_qa import AIQARecord

ROOT = Path(__file__).resolve().parents[1]


def run():
    engine = build_engine(Settings.from_environment())
    try:
        with engine.connect() as db:
            old = [t for t in inspect(engine).get_table_names() if t != 'ai_qa_records']
            def snapshot():
                return {t:{'rows':db.scalar(text('SELECT COUNT(*) FROM `'+t+'`')),
                           'ddl_sha256':hashlib.sha256(db.execute(text('SHOW CREATE TABLE `'+t+'`')).first()[1].encode()).hexdigest()} for t in old}
            before = snapshot()
            exists = 'ai_qa_records' in inspect(engine).get_table_names()
            if not exists:
                db.execute(text((ROOT/'database/migrations/004_create_ai_qa_records.sql').read_text(encoding='utf-8-sig')))
                db.commit()
            inspector = inspect(engine)
            columns = inspector.get_columns('ai_qa_records')
            table = AIQARecord.__table__
            assert [c['name'] for c in columns] == list(table.columns.keys())
            for c in columns:
                mapped=table.c[c['name']]
                assert mapped.nullable == c['nullable']
                assert str(mapped.type.compile(dialect=engine.dialect)).split(' COLLATE')[0].split(' CHARACTER SET')[0] == str(c['type'].compile(dialect=engine.dialect)).split(' COLLATE')[0].split(' CHARACTER SET')[0]
            assert inspector.get_pk_constraint('ai_qa_records')['constrained_columns']==['id']
            indexes={i['name']:(i['column_names'],i['unique']) for i in inspector.get_indexes('ai_qa_records')}
            assert indexes=={i.name:([c.name for c in i.columns],bool(i.unique)) for i in table.indexes}
            assert len(inspector.get_foreign_keys('ai_qa_records'))==2
            assert {c['name'] for c in inspector.get_check_constraints('ai_qa_records')}=={'chk_ai_qa_mode','chk_ai_qa_status','chk_ai_qa_answer','chk_ai_qa_question'}
            ddl=db.execute(text('SHOW CREATE TABLE ai_qa_records')).first()[1]
            assert 'utf8mb4_unicode_ci' in ddl and ddl.count('RESTRICT')==4
            after=snapshot()
            assert before==after
            result={'status':'passed','migration':'004_create_ai_qa_records.sql','action':'verified_existing' if exists else 'created',
                    'ai_columns':len(columns),'foreign_keys':2,'indexes':indexes,'charset':'utf8mb4_unicode_ci',
                    'existing_tables_unchanged':True,'before':before,'after':after}
            (ROOT/'outputs/ai-migration-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
            print(json.dumps({'status':result['status'],'action':result['action'],'existing_tables_unchanged':True}))
    finally:
        engine.dispose()


if __name__=='__main__':
    run()
