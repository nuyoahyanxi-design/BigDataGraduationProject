import ast
import json
import subprocess
from pathlib import Path
import pytest
from app.core.config import Settings
from app.database.session import build_engine
from app.schemas.courses import ChapterWrite
from tools.seed_formal_course_chapters import APPROVED, load_seed, verify_schema

SEED = load_seed()
@pytest.mark.parametrize('entry', [ch for course in SEED for ch in course['chapters']], ids=[f'{course["resource_id"]}-{ch["position"]}' for course in SEED for ch in course['chapters']])
def test_formal_chapter_has_complete_teaching_data(entry):
    ChapterWrite.model_validate(entry)
    assert len(entry['content']) >= 300
    assert all(mark in entry['content'] for mark in ('# ' + entry['title'], '详细讲解', '案例理解'))
    assert len(entry['learning_objectives']) >= 2 and entry['knowledge_tags']
    assert len(entry['exercises']) >= 2 and 1 <= len(entry['example_code'].splitlines()) <= 15
    assert entry['video_url'] == '/demo/video.mp4'

def test_only_two_formal_resources_and_never_browser_demo():
    assert {course['resource_id']: course['title'] for course in SEED} == APPROVED
    assert 406 not in APPROVED
    assert all('浏览器' not in c['title'] for c in SEED)

@pytest.mark.parametrize('change', ['demo_id', 'demo_title', 'missing_course', 'missing_video'])
def test_seed_scope_and_completeness_rejected_before_publication(tmp_path, change):
    data = json.loads(json.dumps(SEED))
    if change == 'demo_id': data[0]['resource_id'] = 406
    elif change == 'demo_title': data[0]['title'] = 'Spark真实浏览器联调演示资源'
    elif change == 'missing_course': data.pop()
    else: data[0]['chapters'][0]['video_url'] = None
    path = tmp_path / 'invalid.json'
    path.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(RuntimeError): load_seed(path)

def test_hdfs_shell_examples_parse_without_execution():
    for entry in next(c for c in SEED if c['resource_id'] == 1070)['chapters'][:4]:
        result = subprocess.run(['bash', '-n'], input=entry['example_code'], text=True, capture_output=True)
        assert result.returncode == 0
    ast.parse(next(c for c in SEED if c['resource_id'] == 1070)['chapters'][4]['example_code'])

def test_existing_migrations_verified_readonly():
    engine = build_engine(Settings.from_environment())
    try:
        with engine.connect() as connection:
            result = verify_schema(connection)
            assert result['migration_005_006_verified'] and not result['ddl_executed']
    finally: engine.dispose()
