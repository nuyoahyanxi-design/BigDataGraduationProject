"""Isolated display fixtures plus a read-only check of existing Spark publication."""
import json
import secrets
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, delete, func, inspect
from app.main import app
from app.models import User, Resource, LearningProgress, Favorite, LearningEvent, UserProfile, RecommendationResult
from app.core.security import issue_token
from app.services.recommendations import DEFAULT_MANIFEST, load_publication
from conftest import SafeTestContext

MODELS = [User, Resource, LearningProgress, Favorite, LearningEvent, UserProfile, RecommendationResult]


@pytest.fixture(scope='module')
def display(tmp_path_factory):
    folder = tmp_path_factory.mktemp('recommendation-display')
    manifest = folder / 'latest.json'
    prefix = 'rd_' + secrets.token_hex(6)
    batch = prefix + '_recommendation'; profile_batch = prefix + '_profile'
    generated = datetime(2026, 10, 5, 0, 0)
    publication = {'status': 'completed', 'mysql_publication': 'passed', 'batch_id': batch,
        'profile_batch_id': profile_batch, 'generated_at': generated.isoformat(), 'as_of_utc': generated.isoformat()}
    manifest.write_text(json.dumps(publication), encoding='utf-8')
    users = []; resources = []; password = secrets.token_urlsafe(24)
    with TestClient(app) as client:
        with app.state.session_factory() as db:
            before = {m.__tablename__: db.scalar(select(func.count()).select_from(m)) for m in MODELS}
        try:
            headers = []
            for suffix in ['admin', 'a', 'b', 'empty']:
                response = client.post('/api/auth/register', json={'username': prefix + suffix, 'password': password, 'interest_tags': ['python'] if suffix == 'a' else ['spark']})
                assert response.status_code == 201
                users.append(response.json()['id'])
            with app.state.session_factory() as db:
                db.get(User, users[0]).role = 'admin'; db.commit()
            for suffix in ['admin', 'a', 'b', 'empty']:
                response = client.post('/api/auth/login', json={'username': prefix + suffix, 'password': password})
                assert response.status_code == 200
                headers.append({'Authorization': 'Bearer ' + response.json()['access_token']})
            for i in range(3):
                response = client.post('/api/resources', headers=headers[0], json={'title': prefix + str(i), 'resource_type': 'document', 'category_code': 'data-engineering', 'tags': ['python'] if i == 0 else ['spark'], 'summary': '展示测试资源', 'content': '仅测试正文'})
                assert response.status_code == 201
                resource_id = response.json()['id']; resources.append(resource_id)
                assert client.patch(f'/api/resources/{resource_id}/status', headers=headers[0], json={'status': 'published'}).status_code == 200
            assert client.patch(f'/api/resources/{resources[2]}/status', headers=headers[0], json={'status': 'offline'}).status_code == 200
            with app.state.session_factory() as db:
                for user_id, tag in [(users[1], 'python'), (users[2], 'spark')]:
                    db.add(UserProfile(user_id=user_id, batch_id=profile_batch, generated_at=generated,
                        interest_profile={'weights': {tag: 1.0}, 'evidence': 'explicit_only'},
                        activity_profile={'active_days': 0, 'event_counts': {key: 0 for key in ['resource_view','learning_start','learning_complete','favorite_add','favorite_remove']}},
                        learning_preference={'started_resources': 0, 'completed_resources': 0, 'completion_rate': None, 'type_weights': {}},
                        metric_explanations={'as_of_utc': generated.isoformat()}))
                for algorithm in ['content_v1', 'popular_v1']:
                    for rank, resource_id in enumerate(resources, 1):
                        db.add(RecommendationResult(user_id=users[1], resource_id=resource_id, batch_id=batch, algorithm=algorithm, score=Decimal('0.8') if algorithm == 'content_v1' else Decimal('8'), rank=rank, reason='与你设置的兴趣标签匹配：python' if algorithm == 'content_v1' else '历史行为热度推荐'))
                    db.add(RecommendationResult(user_id=users[2], resource_id=resources[1], batch_id=batch, algorithm=algorithm, score=Decimal('0.9') if algorithm == 'content_v1' else Decimal('9'), rank=1, reason='与你设置的兴趣标签匹配：spark'))
                # An unpublished/stale batch must never be selected by lexical max.
                db.add(RecommendationResult(user_id=users[1], resource_id=resources[0], batch_id='zz_unpublished_' + prefix, algorithm='content_v1', score=Decimal('1'), rank=1, reason='不应展示的未发布历史批次'))
                db.commit()
            yield SafeTestContext({'client': client, 'headers': headers, 'users': users, 'resources': resources,
                'manifest': manifest, 'publication': publication, 'batch': batch, 'profile_batch': profile_batch})
        finally:
            with app.state.session_factory() as db:
                created_counts = {m.__tablename__: db.scalar(select(func.count()).select_from(m).where(m.user_id.in_(users))) for m in [UserProfile, RecommendationResult, LearningProgress, Favorite, LearningEvent]}
                for model in [RecommendationResult, UserProfile, LearningEvent, Favorite, LearningProgress]:
                    db.execute(delete(model).where(model.user_id.in_(users)))
                db.execute(delete(Resource).where(Resource.id.in_(resources)))
                db.execute(delete(User).where(User.id.in_(users))); db.commit()
                after = {m.__tablename__: db.scalar(select(func.count()).select_from(m)) for m in MODELS}
                assert before == after
            (Path(__file__).resolve().parents[2] / 'outputs/recommendation-display-fixture-verification.json').write_text(json.dumps({'mode': 'explicitly_simulated_display_results_in_isolated_fixture', 'created_users': len(users), 'created_resources': len(resources), 'fixture_rows_before_cleanup': created_counts, 'before': before, 'after': after, 'cleanup': 'passed'}, indent=2) + '\n')


@pytest.fixture
def ctx(display, monkeypatch):
    monkeypatch.setenv('RECOMMENDATION_MANIFEST_PATH', str(display['manifest']))
    return display


def fetch(ctx, actor=1, **params):
    return ctx['client'].get('/api/recommendations/me', headers=ctx['headers'][actor], params=params)


def test_current_user_recommendations_and_matching_profile(ctx):
    response = fetch(ctx); assert response.status_code == 200
    result = response.json()
    assert result['batch_id'] == ctx['batch'] and result['algorithm'] == 'content_v1'
    assert [r['resource_id'] for r in result['items']] == ctx['resources'][:2]
    assert all(r['reason'] == '与你设置的兴趣标签匹配：python' for r in result['items'])
    assert all(isinstance(r['score'], str) and 'resource' in r for r in result['items'])
    assert result['profile']['batch_id'] == ctx['profile_batch']
    assert result['profile']['interest_weights'] == {'python': 1.0}
    assert result['profile']['completion_rate'] is None
    assert result['generated_at'].endswith('Z')


def test_different_users_are_isolated(ctx):
    a = fetch(ctx).json(); b = fetch(ctx, 2).json()
    assert a['items'][0]['resource_id'] != b['items'][0]['resource_id']
    assert b['profile']['interest_weights'] == {'spark': 1.0}
    assert len(b['items']) == 1 and 'spark' in b['items'][0]['reason']


def test_unauthenticated_and_invalid_token_rejected(ctx):
    assert ctx['client'].get('/api/recommendations/me').status_code == 401
    assert ctx['client'].get('/api/recommendations/me', headers={'Authorization': 'Bearer invalid-test-value'}).status_code == 401


def test_target_user_parameter_cannot_change_identity(ctx):
    assert fetch(ctx, user_id=ctx['users'][2]).status_code == 422
    assert fetch(ctx, algorithm='unknown').status_code == 422


def test_disabled_user_rejected(ctx):
    with app.state.session_factory() as db:
        db.get(User, ctx['users'][3]).status = 'disabled'; db.commit()
    try:
        assert fetch(ctx, 3).status_code == 401
    finally:
        with app.state.session_factory() as db:
            db.get(User, ctx['users'][3]).status = 'active'; db.commit()


def test_popular_algorithm_explicitly_selected(ctx):
    result = fetch(ctx, algorithm='popular_v1').json()
    assert result['algorithm'] == 'popular_v1'
    assert all(item['algorithm'] == 'popular_v1' for item in result['items'])
    assert result['items'][0]['score'] == '8.000000000000'


def test_empty_user_receives_friendly_message(ctx):
    result = fetch(ctx, 3).json()
    assert result['items'] == [] and result['profile'] is None
    assert result['explicit_interest_tags'] == ['spark']
    assert '暂无' in result['message']


def test_completed_resources_filtered_without_rewriting_rank(ctx):
    from uuid import uuid4
    resource_id = ctx['resources'][0]
    for action in ['start', 'complete']:
        assert ctx['client'].post(f'/api/resources/{resource_id}/{action}', headers=ctx['headers'][1], json={'event_uuid': str(uuid4())}).status_code == 200
    result = fetch(ctx).json()
    assert [r['resource_id'] for r in result['items']] == [ctx['resources'][1]]
    assert result['items'][0]['rank'] == 2


def test_missing_publication_is_empty(ctx, monkeypatch, tmp_path):
    monkeypatch.setenv('RECOMMENDATION_MANIFEST_PATH', str(tmp_path / 'absent.json'))
    result = fetch(ctx).json()
    assert result['items'] == [] and result['batch_id'] is None and result['profile'] is None


@pytest.mark.parametrize('content', ['{broken', json.dumps({'status': 'prepared'})])
def test_invalid_publication_is_not_reported_as_normal_empty(ctx, monkeypatch, tmp_path, content):
    file = tmp_path / 'bad.json'; file.write_text(content)
    monkeypatch.setenv('RECOMMENDATION_MANIFEST_PATH', str(file))
    assert fetch(ctx).status_code == 503


def test_existing_analytics_models_match_database(ctx):
    inspector = inspect(app.state.engine)
    for model in [UserProfile, RecommendationResult]:
        table = model.__table__; columns = inspector.get_columns(table.name)
        assert len(columns) == 7
        assert [c['name'] for c in columns] == list(table.columns.keys())
        assert inspector.get_pk_constraint(table.name)['constrained_columns'] == [c.name for c in table.primary_key]
        assert {i['name']: (i['column_names'], bool(i['unique'])) for i in inspector.get_indexes(table.name)} == {i.name: ([c.name for c in i.columns], bool(i.unique)) for i in table.indexes}
        assert {c['name'] for c in inspector.get_check_constraints(table.name)} == {c.name for c in table.constraints if c.__class__.__name__ == 'CheckConstraint'}
        for actual in columns:
            mapped = table.c[actual['name']]
            assert mapped.nullable == actual['nullable']
            assert str(mapped.type.compile(dialect=app.state.engine.dialect)).split(' COLLATE')[0].split(' CHARACTER SET')[0] == str(actual['type'].compile(dialect=app.state.engine.dialect)).split(' COLLATE')[0].split(' CHARACTER SET')[0]
        assert {f['name']: (f['constrained_columns'], f['referred_table'], f['referred_columns']) for f in inspector.get_foreign_keys(table.name)} == {f.name: ([e.parent.name for e in f.elements], f.referred_table.name, [e.column.name for e in f.elements]) for f in table.foreign_key_constraints}


def test_existing_spark_publication_read_only(ctx, monkeypatch):
    monkeypatch.delenv('RECOMMENDATION_MANIFEST_PATH')
    publication = load_publication(); assert publication is not None
    with app.state.session_factory() as db:
        user = db.scalar(select(User).join(RecommendationResult, User.id == RecommendationResult.user_id).where(RecommendationResult.batch_id == publication.batch_id, User.status == 'active').order_by(User.id).limit(1))
        assert user is not None
        token = issue_token(user, app.state.auth_settings)
    response = ctx['client'].get('/api/recommendations/me', headers={'Authorization': 'Bearer ' + token})
    assert response.status_code == 200
    result = response.json()
    assert result['batch_id'] == publication.batch_id and result['profile']['batch_id'] == publication.profile_batch_id
    assert len(result['items']) > 0 and all(item['reason'] for item in result['items'])
    (Path(__file__).resolve().parents[2] / 'outputs/recommendation-display-published-batch-verification.json').write_text(json.dumps({'source': 'existing_spark_mysql_publication_read_only', 'batch_id': result['batch_id'], 'profile_batch_id': result['profile']['batch_id'], 'algorithm': result['algorithm'], 'returned_items': len(result['items']), 'profile_available': True, 'http_status': response.status_code}, indent=2) + '\n')

def test_hidden_recommendation_filtered_without_changing_stored_results(ctx,monkeypatch):
    from app.services import course_presentation
    before=fetch(ctx).json()
    hidden=ctx['resources'][1]
    monkeypatch.setattr(course_presentation,'HIDDEN_LEARNER_RESOURCE_IDS',frozenset({406,hidden}))
    after=fetch(ctx).json()
    assert hidden not in {item['resource_id'] for item in after['items']}
    assert after['items']==[item for item in before['items'] if item['resource_id']!=hidden]
    with app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(RecommendationResult).where(RecommendationResult.resource_id==hidden,RecommendationResult.batch_id==ctx['batch']))>0
