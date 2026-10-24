"""Explicit, additive migration; no changes to existing tables or accounts."""
import json
from pathlib import Path
from sqlalchemy import inspect, text
from app.core.config import Settings
from app.database.session import build_engine
ROOT=Path(__file__).resolve().parents[2]
engine=build_engine(Settings.from_environment())
try:
    with engine.connect() as connection:
        names=inspect(connection).get_table_names()
        before={name:connection.scalar(text('SELECT COUNT(*) FROM `'+name+'`')) for name in names}
        checksums={name:connection.execute(text('CHECKSUM TABLE `'+name+'` EXTENDED')).first()[1] for name in names}
        schemas={name:connection.execute(text('SHOW CREATE TABLE `'+name+'`')).first()[1] for name in names}
        created='auth_recovery_codes' not in names
        if created:
            connection.execute(text((ROOT/'database/migrations/008_create_auth_recovery_codes.sql').read_text().strip().rstrip(';')))
            connection.commit()
        assert {c['name'] for c in inspect(connection).get_columns('auth_recovery_codes')}=={'user_id','code_hash'}
        assert inspect(connection).get_pk_constraint('auth_recovery_codes')['constrained_columns']==['user_id']
        assert any(f['referred_table']=='users' and f['constrained_columns']==['user_id'] for f in inspect(connection).get_foreign_keys('auth_recovery_codes'))
        assert all(connection.scalar(text('SELECT COUNT(*) FROM `'+name+'`'))==count for name,count in before.items())
        assert all(connection.execute(text('CHECKSUM TABLE `'+name+'` EXTENDED')).first()[1]==checksum for name,checksum in checksums.items())
        assert all(connection.execute(text('SHOW CREATE TABLE `'+name+'`')).first()[1]==schema for name,schema in schemas.items())
        evidence={'migration':'008_create_auth_recovery_codes.sql','created':created,'existing_table_counts_unchanged':True,'existing_schema_unchanged':True,'existing_table_checksums_unchanged':True}
        (ROOT/'outputs/login-auth-migration-evidence.json').write_text(json.dumps(evidence,indent=2))
        print(json.dumps(evidence))
finally:engine.dispose()
