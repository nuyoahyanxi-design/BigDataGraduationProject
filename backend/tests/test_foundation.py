"""Read-only acceptance tests against the existing development database."""
import importlib.metadata
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, func, text

from app.main import app
from app.core.config import Settings
from app.database.base import Base
from app.models import User, Resource, LearningProgress, Favorite, LearningEvent

EXPECTED_PATHS={'/api/auth/register','/api/auth/login','/api/users/me','/api/users/interests',
                '/api/resources','/api/resources/{id}','/api/resources/{id}/status',
                '/api/resources/{id}/view','/api/resources/{id}/start','/api/resources/{id}/complete',
                '/api/resources/{id}/favorite','/api/users/me/progress','/api/users/me/favorites','/api/users/me/events',
                '/api/recommendations/me','/api/dashboard/overview','/api/admin/users','/api/admin/batches','/api/admin/courses',
                '/api/ai/capabilities','/api/ai/questions','/api/ai/questions/{request_uuid}','/api/ai/history',
                '/api/resources/{course_id}/ai/questions','/api/resources/{course_id}/ai/questions/{request_uuid}',
                '/api/resources/{course_id}/ai/history',
                '/api/resources/{id}/course','/api/resources/{id}/chapters',
                '/api/resources/{id}/chapters/{chapter_id}',
                '/api/resources/{id}/chapters/{chapter_id}/events','/api/users/me/chapter-events'}


@pytest.fixture(scope='module')
def client():
    with TestClient(app) as instance:
        yield instance


def test_configuration_validation(monkeypatch):
    settings = Settings.from_environment()
    assert settings.password not in repr(settings)
    monkeypatch.delenv('MYSQL_PASSWORD')
    with pytest.raises(RuntimeError, match='Missing required'):
        Settings.from_environment()


def test_fastapi_startup(client):
    assert client.get('/docs').status_code == 200
    assert set(client.get('/openapi.json').json()['paths']) == EXPECTED_PATHS
    assert set(client.get('/openapi.json').json()['paths']['/api/resources/{id}/chapters/{chapter_id}']) == {'put','delete'}
    assert client.get('/').status_code == 404


def test_database_connection(client):
    with app.state.engine.connect() as connection:
        assert connection.scalar(text('SELECT 1')) == 1
        assert connection.scalar(text('SELECT DATABASE()')) == 'bigdata_graduation'
        assert connection.scalar(text('SELECT @@session.time_zone')) == '+00:00'
        assert connection.scalar(text('SELECT @@character_set_connection')) == 'utf8mb4'


def test_orm_mapping_and_read_queries(client):
    engine = app.state.engine
    inspector = inspect(engine)
    evidence = {'python':sys.version.split()[0], 'executable':sys.executable,
                'packages':{p:importlib.metadata.version(p) for p in ['fastapi','SQLAlchemy','PyMySQL','uvicorn','pytest','httpx']},
                'tables':{}, 'business_routes':len(EXPECTED_PATHS)}
    models = [User,Resource,LearningProgress,Favorite,LearningEvent]
    # Display stage maps the already migrated analytics tables without DDL.
    assert set(inspector.get_table_names()) == set(Base.metadata.tables)
    assert sum(len(model.__table__.columns) for model in models) == 51
    with app.state.session_factory() as session:
        for model in models:
            table = model.__table__
            actual = inspector.get_columns(table.name)
            assert [c['name'] for c in actual] == list(table.columns.keys())
            for field in actual:
                mapped=table.c[field['name']]
                expected_type=str(mapped.type.compile(dialect=engine.dialect)).split(' COLLATE')[0].split(' CHARACTER SET')[0]
                actual_type=str(field['type'].compile(dialect=engine.dialect)).split(' COLLATE')[0].split(' CHARACTER SET')[0]
                assert expected_type == actual_type
                if getattr(mapped.type,'collation',None):
                    assert mapped.type.collation == field['type'].collation
                assert mapped.nullable == field['nullable']
                expected=None if mapped.server_default is None else str(mapped.server_default.arg).strip("'")
                observed=None if field['default'] is None else str(field['default']).strip("'")
                assert expected == observed
            assert inspector.get_pk_constraint(table.name)['constrained_columns'] == [c.name for c in table.primary_key]
            actual_indexes = {i['name']:(i['column_names'],bool(i['unique'])) for i in inspector.get_indexes(table.name)}
            assert actual_indexes == {i.name:([c.name for c in i.columns],bool(i.unique)) for i in table.indexes}
            actual_fks = {f['name']:(f['constrained_columns'],f['referred_table'],f['referred_columns']) for f in inspector.get_foreign_keys(table.name)}
            assert actual_fks == {f.name:([e.parent.name for e in f.elements],f.referred_table.name,[e.column.name for e in f.elements]) for f in table.foreign_key_constraints}
            checks=inspector.get_check_constraints(table.name)
            assert {c['name'] for c in checks} == {c.name for c in table.constraints if c.__class__.__name__=='CheckConstraint'}
            count=session.scalar(select(func.count()).select_from(model))
            sample=session.scalars(select(model).limit(1)).first()
            assert sample is not None or count==0
            evidence['tables'][table.name]={'fields':len(table.columns),'rows':count,'orm_query':'passed','mapping':'passed'}
        evidence['mysql_version']=session.scalar(text('SELECT VERSION()'))
    output=Path(__file__).resolve().parents[2]/'outputs/admin-foundation-regression.json'
    output.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def test_real_uvicorn_startup():
    import socket
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port=sock.getsockname()[1]
    process=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        success=False
        for _ in range(60):
            if process.poll() is not None:
                break
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/openapi.json',timeout=1) as response:
                    assert response.status==200
                    assert set(json.load(response)['paths'])==EXPECTED_PATHS
                    success=True
                    break
            except (OSError,ValueError):
                time.sleep(0.1)
        assert success, 'Uvicorn did not serve OpenAPI successfully'
    finally:
        process.terminate()
        process.wait(timeout=10)
