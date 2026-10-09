import asyncio
import hashlib
import re
from types import SimpleNamespace
from uuid import uuid4
import pytest
from fastapi import HTTPException, Response
from app.services import course_ai_retrieval as retrieval


@pytest.fixture
def mysql_course():
    resource = SimpleNamespace(title='MySQL数据库基础', summary='学习关系型数据库设计、SQL查询、事务和索引。',
                               category_code='database', tags=['mysql', 'sql'])
    titles = ['MySQL与关系型数据库基础', '数据表、字段与约束设计', 'SELECT查询、条件筛选与排序',
              '聚合查询与表连接', '事务、回滚与索引基础']
    chapters = [SimpleNamespace(id=54+i, position=i+1, title=title,
                               learning_objectives=['掌握'+title], knowledge_tags=[title, 'mysql'],
                               content='NOT_OVERVIEW_BODY '+title,
                               example_code='NOT_OVERVIEW_CODE', exercises=['NOT_OVERVIEW_EXERCISE'])
                for i, title in enumerate(titles)]
    return resource, chapters


@pytest.mark.parametrize('question', [
    '这门课程主要学习什么？', '课程内容是什么', '有哪些章节？',
    '学完能掌握什么？', '教学目标是什么？', '请问这门课程主要学习什么？',
    'MySQL数据库基础的教学目标是什么？', '学习完本课程后可以掌握什么？',
])
def test_overview_has_real_course_directory_and_objectives(mysql_course, question):
    resource, chapters = mysql_course
    context, refs = retrieval.retrieve(resource, list(reversed(chapters)), question, chapter_id=58)
    assert context and resource.title in context and resource.summary in context
    assert len(context) <= retrieval.MAX_CONTEXT
    assert [ref['chapter_id'] for ref in refs] == [54, 55, 56]
    for chapter in chapters:
        assert chapter.title in context
        assert chapter.learning_objectives[0] in context
        assert chapter.knowledge_tags[0] in context
    assert 'NOT_OVERVIEW_BODY' not in context
    assert 'NOT_OVERVIEW_CODE' not in context
    assert 'NOT_OVERVIEW_EXERCISE' not in context


def test_overview_reference_hashes_match_actual_context(mysql_course):
    resource, chapters = mysql_course
    context, refs = retrieval.retrieve(resource, chapters, '有哪些章节')
    actual = {ch.id: ch for ch in chapters}
    for ref in refs:
        chapter = actual[ref['chapter_id']]
        assert ref['course_name'] == resource.title
        assert ref['chapter_name'] == chapter.title
        assert ref['position'] == chapter.position
        pattern = r'\n参考章节\d+：[^\n]*（ID='+str(chapter.id)+r'）\n.*?(?=\n参考章节|$)'
        block = re.search(pattern, context, re.S).group(0)
        assert hashlib.sha256(block.encode()).hexdigest() == ref['fragment_hash']


def test_knowledge_question_preserves_original_retrieval(mysql_course):
    resource, chapters = mysql_course
    context, refs = retrieval.retrieve(resource, chapters, '索引是什么？')
    assert retrieval.MIN_RELEVANCE == .12
    assert context and refs
    assert [ref['chapter_id'] for ref in refs] == [58]
    assert 'NOT_OVERVIEW_BODY' in context and 'NOT_OVERVIEW_CODE' in context


@pytest.mark.parametrize('question', [
    'MySQL如何训练深度学习模型？', '如何使用MySQL进行图像识别？',
    '深度学习有哪些章节？', '课程内容是什么，能训练深度学习模型吗？',
])
def test_unrelated_and_mixed_questions_do_not_bypass_threshold(mysql_course, question):
    resource, chapters = mysql_course
    assert not retrieval.is_course_overview(resource, question)
    assert retrieval.retrieve(resource, chapters, question, chapter_id=54) == (None, [])


def test_current_chapter_boost_still_cannot_cross_floor(mysql_course, monkeypatch):
    resource, chapters = mysql_course
    monkeypatch.setattr(retrieval, 'score', lambda ch, q: retrieval.MIN_RELEVANCE-.001)
    assert retrieval.retrieve(resource, chapters, '索引是什么？', chapter_id=58) == (None, [])
    monkeypatch.setattr(retrieval, 'score', lambda ch, q: retrieval.MIN_RELEVANCE)
    assert retrieval.retrieve(resource, chapters, '索引是什么？', chapter_id=58)[1]


def test_overview_without_chapters_preserves_fallback(mysql_course):
    assert retrieval.retrieve(mysql_course[0], [], '教学目标是什么') == (None, [])


def test_overview_respects_context_budget(mysql_course):
    resource, chapters = mysql_course
    expanded = [SimpleNamespace(**{**vars(chapters[0]), 'id':1000+i, 'position':i+1,
                                   'title':'章节'+str(i)+'标题'*100,
                                   'learning_objectives':['目标'*3000], 'knowledge_tags':['知识'*3000]})
                for i in range(100)]
    context, refs = retrieval.retrieve(resource, expanded, '有哪些章节')
    assert context and len(context) <= retrieval.MAX_CONTEXT
    assert 1 <= len(refs) <= 3
    assert all(f"ID={ref['chapter_id']}" in context for ref in refs)


def test_overview_keeps_credential_filter(mysql_course):
    resource, chapters = mysql_course
    chapters[0].learning_objectives = ['API_KEY=placeholder']
    with pytest.raises(HTTPException) as error:
        retrieval.retrieve(resource, chapters, '教学目标是什么')
    assert error.value.status_code == 422


@pytest.mark.parametrize('question, fallback', [
    ('这门课程主要学习什么？', False), ('索引是什么？', False),
    ('MySQL如何训练深度学习模型？', True),
])
def test_course_execution_only_adds_fallback_when_context_absent(mysql_course, monkeypatch, question, fallback):
    from app.api import ai_assistant as api
    from app.core.ai_config import AISettings
    from app.services.agnes import Answer
    resource, chapters = mysql_course
    context, refs = retrieval.retrieve(resource, chapters, question)
    uuid = str(uuid4())
    captured = []
    monkeypatch.setattr(api, 'settings', lambda: AISettings(enabled=True))
    monkeypatch.setattr(api.ai_diagnostics, 'log', lambda *args, **kwargs: None)
    monkeypatch.setattr(api.service, 'reserve', lambda *args: (SimpleNamespace(request_uuid=uuid), context, True))
    async def answer(settings, sent_question, sent_context):
        captured.append(sent_context)
        return Answer('本课程学习MySQL、SQL查询、事务与索引。')
    monkeypatch.setattr(api.service.provider, 'answer', answer)
    def finish(factory, identity, request_uuid, settings, result, error, latency):
        assert error is None
        return result.text
    monkeypatch.setattr(api.service, 'finish', finish)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(session_factory=object())))
    payload = SimpleNamespace(question=question, mode='resource')
    result = asyncio.run(api.execute_question(payload, request, Response(), SimpleNamespace(id=1),
                                             SimpleNamespace(close=lambda: None), {'chapter_id':54}))
    assert result.startswith(retrieval.FALLBACK) == fallback
    assert captured == [context]
    if not fallback:
        assert refs and context
