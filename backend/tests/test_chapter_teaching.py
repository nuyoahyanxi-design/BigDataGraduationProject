import ast
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from app.schemas.courses import ChapterWrite
from test_courses import ctx, setup, chapter

ROOT = Path(__file__).resolve().parents[2]

def test_teaching_fields_round_trip_and_existing_defaults(ctx):
    rid, ids = setup(ctx, 1)
    old = ctx['client'].get(f'/api/resources/{rid}/course', headers=ctx['learner']).json()['chapters'][0]
    assert old['learning_objectives'] == [] and old['example_code'] is None and old['exercises'] == []
    payload = {**chapter(2), 'learning_objectives': ['识别RDD'], 'example_code': 'print("safe example")',
               'exercises': ['解释惰性求值'], 'video_url': '/demo/video.mp4'}
    response = ctx['client'].post(f'/api/resources/{rid}/chapters', headers=ctx['admin'], json=payload)
    assert response.status_code == 201
    result = ctx['client'].get(f'/api/resources/{rid}/course', headers=ctx['learner']).json()['chapters'][1]
    for name in ('learning_objectives', 'example_code', 'exercises', 'video_url'):
        assert result[name] == payload[name]
    assert not result['completed']

@pytest.mark.parametrize('field,value', [
    ('learning_objectives', [' ']), ('learning_objectives', ['x' * 1001]),
    ('learning_objectives', ['goal'] * 9), ('exercises', ['']),
    ('exercises', ['x' * 1001]), ('exercises', ['exercise'] * 9),
    ('example_code', 'x' * 10001), ('video_url', '/demo/../video.mp4'),
    ('video_url', '/demo/other.mp4'), ('video_url', 'https://example.com/video.mp4')
])
def test_teaching_validation_preserves_limits(field, value):
    with pytest.raises(ValidationError): ChapterWrite.model_validate({**chapter(), field: value})

DATA = json.loads((ROOT / 'database/seeds/course-teaching-content.json').read_text(encoding='utf-8'))
@pytest.mark.parametrize('entry', [c for course in DATA for c in course['chapters']], ids=[f'{i+1}-{c["position"]}' for i, course in enumerate(DATA) for c in course['chapters']])
def test_each_seed_chapter_is_complete_and_code_compiles(entry):
    ChapterWrite.model_validate(entry)
    assert len(entry['content']) >= 300
    assert len(entry['learning_objectives']) >= 2 and len(entry['exercises']) >= 2
    assert 1 <= len(entry['example_code'].splitlines()) <= 15
    ast.parse(entry['example_code'])
    assert entry['video_url'] == '/demo/video.mp4'
    assert '核心知识' in entry['content'] and '常见误区' in entry['content']

def test_seed_scope_matches_existing_chapter_identities():
    original = json.loads((ROOT / 'database/seeds/course-chapters.json').read_text(encoding='utf-8'))
    assert len(DATA) == 3
    for old_course, new_course in zip(original, DATA, strict=True):
        assert old_course['title'] == new_course['title']
        assert len(new_course['chapters']) == 5
        for old, new in zip(old_course['chapters'], new_course['chapters'], strict=True):
            for field in ('title', 'position', 'knowledge_tags'): assert old[field] == new[field]
