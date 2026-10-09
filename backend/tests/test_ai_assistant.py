import asyncio
import json
import secrets
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, func, inspect
from app.main import app
from app.models import User, Resource, AIQARecord, LearningEvent
from app.core.ai_config import AISettings
from app.services import ai_assistant as service
from app.services.agnes import AgnesProvider, Answer, ProviderError
from conftest import SafeTestContext


@pytest.fixture(scope='module')
def ctx():
    ids, resources = [], []
    prefix = 'ai_'+secrets.token_hex(6)
    password = secrets.token_urlsafe(24)
    with TestClient(app) as client:
        with app.state.session_factory() as db:
            before = db.scalar(select(func.count()).select_from(LearningEvent))
        try:
            headers=[]
            for i in range(2):
                result=client.post('/api/auth/register', json={'username':prefix+str(i),'password':password})
                assert result.status_code==201
                ids.append(result.json()['id'])
            with app.state.session_factory() as db:
                db.get(User,ids[1]).role='admin'; db.commit()
            for i in range(2):
                result=client.post('/api/auth/login',json={'username':prefix+str(i),'password':password})
                assert result.status_code==200
                headers.append({'Authorization':'Bearer '+result.json()['access_token']})
            result=client.post('/api/resources',headers=headers[1],json={'title':prefix,'summary':'自编AI测试资料',
                'resource_type':'document','category_code':'data-engineering','tags':['spark'],'difficulty':1,'content':'Spark处理学习行为。'})
            assert result.status_code==201
            resources.append(result.json()['id'])
            assert client.patch(f'/api/resources/{resources[0]}/status',headers=headers[1],json={'status':'published'}).status_code==200
            yield SafeTestContext({'client':client,'headers':headers,'ids':ids,'resource':resources[0]})
        finally:
            with app.state.session_factory() as db:
                db.execute(delete(AIQARecord).where(AIQARecord.user_id.in_(ids)))
                db.execute(delete(Resource).where(Resource.id.in_(resources)))
                db.execute(delete(User).where(User.id.in_(ids))); db.commit()
                assert db.scalar(select(func.count()).select_from(LearningEvent))==before
            (Path(__file__).resolve().parents[2]/'outputs/ai-fixture-verification.json').write_text(json.dumps({'temporary_users':len(ids),'temporary_resources':len(resources),'cleanup':'passed','learning_events_unchanged':True}))


@pytest.fixture(autouse=True)
def optional_config(monkeypatch):
    monkeypatch.setenv('AI_ASSISTANT_ENABLED','true')
    monkeypatch.setenv('AGNES_API_KEY','unit-test-placeholder-not-a-real-key')
    monkeypatch.setenv('AGNES_MODEL','test-model')
    monkeypatch.setenv('AI_ALLOWED_RESOURCE_IDS','')
    async def answer(settings, question, context):
        return Answer('Spark 是数据处理框架。', 'test-response', 10, 20)
    monkeypatch.setattr(service.provider,'answer',answer)


def payload(**changes):
    return dict(request_uuid=str(uuid4()),question='什么是Spark？',mode='general',resource_id=None,consent_version='agnes-external-v1',**changes)


def post(ctx, data=None):
    return ctx['client'].post('/api/ai/questions',headers=ctx['headers'][0],json=data or payload())


@pytest.mark.parametrize('path',['/api/ai/capabilities','/api/ai/history','/api/ai/questions/'+str(uuid4())])
def test_ai_anonymous_reads(ctx,path):
    assert ctx['client'].get(path).status_code==401


def test_ai_anonymous_post(ctx):
    assert ctx['client'].post('/api/ai/questions',json=payload()).status_code==401


def test_ai_disabled_preserves_mvp(ctx,monkeypatch):
    monkeypatch.setenv('AI_ASSISTANT_ENABLED','false')
    monkeypatch.setenv('AGNES_BASE_URL','http://invalid')
    monkeypatch.delenv('AGNES_API_KEY')
    assert not ctx['client'].get('/api/ai/capabilities',headers=ctx['headers'][0]).json()['enabled']
    assert post(ctx).status_code==503
    assert ctx['client'].get('/api/users/me',headers=ctx['headers'][0]).status_code==200
    assert ctx['client'].get('/api/resources',headers=ctx['headers'][0]).status_code==200


def test_ai_missing_key_no_record(ctx,monkeypatch):
    monkeypatch.delenv('AGNES_API_KEY')
    data=payload()
    assert post(ctx,data).status_code==503
    assert ctx['client'].get('/api/ai/questions/'+data['request_uuid'],headers=ctx['headers'][0]).status_code==404


def test_ai_success_history_ownership_and_replay(ctx,monkeypatch):
    calls=[]
    async def answer(settings,question,context):
        calls.append(context)
        return Answer('<script>alert(1)</script>只是普通文本。')
    monkeypatch.setattr(service.provider,'answer',answer)
    data=payload()
    result=post(ctx,data)
    assert result.status_code==200 and result.json()['status']=='succeeded'
    assert result.json()['answer'].startswith('<script>')  # API text; Vue must render interpolation.
    assert post(ctx,data).json()==result.json()
    assert len(calls)==1 and calls==[None]
    uuid=data['request_uuid']
    assert ctx['client'].get('/api/ai/questions/'+uuid,headers=ctx['headers'][1]).status_code==404
    assert ctx['client'].post('/api/ai/questions',headers=ctx['headers'][1],json=data).status_code==404
    history=ctx['client'].get('/api/ai/history',headers=ctx['headers'][0]).json()
    assert any(r['request_uuid']==uuid for r in history['items'])
    assert set(history['items'][0])=={'request_uuid','mode','resource_id','resource_version','question','answer','status','model','created_at','finished_at','error_code','source'}
    assert ctx['client'].get('/api/ai/history',headers=ctx['headers'][1]).json()['total']==0
    assert ctx['client'].get('/api/ai/history?user_id=1',headers=ctx['headers'][1]).status_code==422
    data['question']='不同的问题'
    assert post(ctx,data).status_code==409


@pytest.mark.parametrize('changes',[{'question':'   '},{'question':'a'*2001},{'consent_version':'invalid'},
    {'mode':'resource','resource_id':None},{'mode':'general','resource_id':1},{'user_id':1},{'question':'password=secret'}])
def test_ai_input_validation(ctx,changes):
    data=payload();data.update(changes)
    assert post(ctx,data).status_code==422


def test_ai_resource_permission_and_history_mask(ctx,monkeypatch):
    data=payload();data.update(mode='resource',resource_id=ctx['resource'])
    assert post(ctx,data).status_code==404
    monkeypatch.setenv('AI_ALLOWED_RESOURCE_IDS',str(ctx['resource']))
    contexts=[]
    async def answer(settings,question,context):
        contexts.append(context);return Answer('依据指定片段作答。')
    monkeypatch.setattr(service.provider,'answer',answer)
    result=post(ctx,data)
    assert result.status_code==200 and result.json()['resource_version']==2
    assert 'Spark处理学习行为' in contexts[0]
    try:
        assert ctx['client'].patch(f'/api/resources/{ctx["resource"]}/status',headers=ctx['headers'][1],json={'status':'offline'}).status_code==200
        assert ctx['client'].get('/api/ai/questions/'+data['request_uuid'],headers=ctx['headers'][0]).json()['answer'] is None
        data['request_uuid']=str(uuid4());assert post(ctx,data).status_code==404
    finally:
        ctx['client'].patch(f'/api/resources/{ctx["resource"]}/status',headers=ctx['headers'][1],json={'status':'published'})


@pytest.mark.parametrize('code,status,uncertain',[('provider_auth',502,False),('provider_rate_limit',502,False),('provider_timeout',504,True)])
def test_ai_provider_failure_is_recorded(ctx,monkeypatch,code,status,uncertain):
    calls=[]
    async def answer(*args):
        calls.append(1);raise ProviderError(code,status,uncertain)
    monkeypatch.setattr(service.provider,'answer',answer)
    data=payload();result=post(ctx,data)
    assert result.status_code==status
    assert result.json()['status']==('unknown' if uncertain else 'failed')
    assert post(ctx,data).status_code==200 and len(calls)==1
    assert ctx['client'].get('/api/users/me',headers=ctx['headers'][0]).status_code==200


def test_ai_user_daily_limit(ctx,monkeypatch):
    monkeypatch.setenv('AI_USER_DAILY_REQUEST_LIMIT','1')
    response=post(ctx);assert response.status_code==429
    assert response.headers['X-AI-Limit-Source']=='user_daily'
    assert 1<=int(response.headers['Retry-After'])<=86401


def test_ai_global_daily_limit(ctx,monkeypatch):
    monkeypatch.setenv('AI_GLOBAL_DAILY_REQUEST_LIMIT','1')
    response=post(ctx);assert response.status_code==429
    assert response.headers['X-AI-Limit-Source']=='global_daily'


def test_ai_disabled_user(ctx):
    with app.state.session_factory() as db:
        db.get(User,ctx['ids'][0]).status='disabled';db.commit()
    try:
        assert post(ctx).status_code==401
    finally:
        with app.state.session_factory() as db:
            db.get(User,ctx['ids'][0]).status='active';db.commit()


def test_ai_pending_replay_and_recovery(ctx):
    data=payload()
    from app.schemas.ai_assistant import Question
    settings=AISettings.from_environment()
    first,_,_=service.reserve(app.state.session_factory,ctx['ids'][0],Question(**data),settings)
    assert post(ctx,data).status_code==202
    with app.state.session_factory() as db:
        row=db.scalar(select(AIQARecord).where(AIQARecord.request_uuid==data['request_uuid']))
        row.created_at=service.now()-timedelta(seconds=121);db.commit()
    result=ctx['client'].get('/api/ai/questions/'+first.request_uuid,headers=ctx['headers'][0])
    assert result.json()['status']=='unknown'


def test_ai_schema_mapping(ctx):
    inspector=inspect(app.state.engine)
    assert len(inspector.get_columns('ai_qa_records'))==21
    assert len(inspector.get_foreign_keys('ai_qa_records'))==2
    assert 'uk_ai_qa_request_uuid' in {i['name'] for i in inspector.get_indexes('ai_qa_records')}


def test_ai_inflight_duplicate_and_concurrency_limit(ctx,monkeypatch):
    entered, released = Event(), Event()
    calls=[]
    async def answer(*args):
        calls.append(1);entered.set()
        await asyncio.to_thread(released.wait,5)
        return Answer('并发控制测试回答')
    monkeypatch.setattr(service.provider,'answer',answer)
    monkeypatch.setenv('AI_MAX_CONCURRENT_REQUESTS','1')
    data=payload()
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(post,ctx,data)
        try:
            assert entered.wait(3)
            assert post(ctx,data).status_code==202
            limited=post(ctx);assert limited.status_code==429
            assert limited.headers['X-AI-Limit-Source']=='concurrency'
            assert limited.headers['Retry-After']=='5'
            assert ctx['client'].get('/api/users/me',headers=ctx['headers'][0]).status_code==200
        finally:
            released.set()
        assert pending.result(timeout=5).status_code==200
    assert len(calls)==1


def test_ai_configuration_host_and_secret(monkeypatch):
    value=AISettings.from_environment()
    assert value.api_key not in repr(value)
    monkeypatch.setenv('AGNES_BASE_URL','https://evil.example/v1')
    with pytest.raises(RuntimeError):AISettings.from_environment()


@pytest.mark.parametrize('kind',['success','missing_usage','tools','empty','malformed','unauthorized','rate','redirect','large','timeout','length'])
def test_agnes_wire_protocol(monkeypatch,kind):
    real_client=httpx.AsyncClient
    calls=[]
    def handler(request):
        calls.append(request)
        body=json.loads(request.content)
        assert request.url==httpx.URL('https://apihub.agnes-ai.com/v1/chat/completions')
        assert body['stream'] is False and body['max_tokens']==2048 and 'tools' not in body
        assert body['temperature'] == 0.3 and 'stop' not in body
        assert request.headers['Authorization'].startswith('Bearer ')
        if kind=='timeout':raise httpx.ReadTimeout('test',request=request)
        if kind=='malformed':return httpx.Response(200,content=b'invalid')
        if kind=='large':return httpx.Response(200,content=b'x'*131073)
        if kind in ('unauthorized','rate','redirect'):return httpx.Response({'unauthorized':401,'rate':429,'redirect':302}[kind])
        data={'id':'test','choices':[{'message':{'role':'assistant','content':'回答'},'finish_reason':'stop'}]}
        if kind=='tools':data['choices'][0]['message']['tool_calls']=[{}]
        if kind=='empty':data['choices'][0]['message']['content']=''
        if kind=='length':data['choices'][0]['finish_reason']='length'
        if kind=='success':data['usage']={'prompt_tokens':2,'completion_tokens':3}
        return httpx.Response(200,json=data)
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:real_client(transport=httpx.MockTransport(handler),**kwargs))
    settings=AISettings.from_environment()
    if kind in ('success','missing_usage','length'):
        result=asyncio.run(AgnesProvider().answer(settings,'学习问题'))
        assert result.text=='回答' and result.input_tokens==(2 if kind=='success' else None)
        assert not result.truncated
        assert result.output_limited == (kind == 'length')
    else:
        with pytest.raises(ProviderError) as error:asyncio.run(AgnesProvider().answer(settings,'学习问题'))
        assert 'unit-test-placeholder' not in str(error.value)
        if kind=='timeout':assert error.value.uncertain
    assert len(calls)==1


@pytest.mark.parametrize('reason', [None, 'stop', 'length', 'tool_calls', 'function_call', 'content_filter', 'unexpected-secret-value'])
def test_agnes_finish_reason_and_safe_summary(monkeypatch, reason):
    real_client = httpx.AsyncClient
    def handler(request):
        return httpx.Response(200, json={'choices':[{'message':{'role':'assistant','content':'private-answer'},
                                                     'finish_reason':reason}],
                                       'usage':{'prompt_tokens':5,'completion_tokens':7,'total_tokens':12,
                                                'sensitive':'never-store'}})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    if reason in (None, 'stop', 'length'):
        answer = asyncio.run(AgnesProvider().answer(AISettings.from_environment(), 'question'))
        assert not answer.truncated
        assert answer.output_limited == (reason == 'length')
        summary = answer.summary
    else:
        with pytest.raises(ProviderError) as failure:
            asyncio.run(AgnesProvider().answer(AISettings.from_environment(), 'question'))
        summary = failure.value.summary
    assert summary['completion_tokens'] == 7 and summary['content_present']
    assert summary['finish_reason'] == ('other' if reason == 'unexpected-secret-value' else reason)
    assert all(value not in json.dumps(summary) for value in ('private-answer','never-store','unexpected-secret-value'))


def test_truncated_answer_saved_and_failure_summary_linked(ctx, monkeypatch, tmp_path):
    # Redirect only the sidecar path; the real ORM/API and transaction remain tested.
    class SidecarPath:
        def __init__(self, value): self.parents = [None, None, None, tmp_path]
    monkeypatch.setattr(service, 'Path', lambda value: type('Resolved', (), {'resolve': lambda self: SidecarPath(value)})())
    async def truncated(*args):
        return Answer('部分回答', 'test-response', 5, 7, True, {'finish_reason':'length'})
    monkeypatch.setattr(service.provider, 'answer', truncated)
    data = payload()
    response = post(ctx, data)
    assert response.status_code == 200
    assert response.json()['answer'] == '部分回答' and response.json()['status'] == 'succeeded'
    assert response.json()['error_code'] == 'answer_truncated'
    assert post(ctx, data).json() == response.json()
    assert ctx['client'].get('/api/ai/questions/'+data['request_uuid'], headers=ctx['headers'][0]).json() == response.json()
    async def failed(*args):
        raise ProviderError('provider_incomplete_answer', summary={'finish_reason':'content_filter','http_status':200})
    monkeypatch.setattr(service.provider, 'answer', failed)
    failed_data = payload()
    assert post(ctx, failed_data).status_code == 502
    saved = [json.loads(line) for line in (tmp_path/'outputs'/'ai-provider-response-summaries.jsonl').read_text().splitlines()]
    assert saved[-1]['request_uuid'] == failed_data['request_uuid']
    assert saved[-1]['summary']['finish_reason'] == 'content_filter'
    assert saved[0]['error_code'] == 'answer_truncated'


@pytest.mark.parametrize('message', [
    {'role':'assistant','content':'text','tool_calls':[{'private':'not-logged'}]},
    {'role':'assistant','content':'text','function_call':{'private':'not-logged'}},
    {'role':'assistant','content':''},
    {'role':'user','content':'text'},
])
def test_length_preserves_text_and_tool_safety(monkeypatch, message):
    real_client = httpx.AsyncClient
    def handler(request):
        return httpx.Response(200, json={'choices':[{'message':message,'finish_reason':'length'}]})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    with pytest.raises(ProviderError) as failure:
        asyncio.run(AgnesProvider().answer(AISettings.from_environment(), 'question'))
    assert failure.value.code == 'provider_invalid_response'
    assert 'not-logged' not in json.dumps(failure.value.summary)


@pytest.mark.parametrize('size,reason', [(100,'stop'), (16001,'stop'), (30000,'stop'), (30001,'stop'), (40000,'length'), (100,'length')])
def test_answer_character_limit(monkeypatch, size, reason):
    real_client = httpx.AsyncClient
    def handler(request):
        return httpx.Response(200, json={'choices':[{'message':{'role':'assistant','content':'a'*size},'finish_reason':reason}]})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    answer = asyncio.run(AgnesProvider().answer(AISettings.from_environment(), 'question'))
    assert len(answer.text) == min(size, 30000)
    assert answer.truncated == (size > 30000)
    assert answer.output_limited == (reason == 'length')


@pytest.mark.parametrize('size,reason,code', [(16001,'stop',None), (30001,'stop','answer_truncated'), (100,'length','provider_output_limited')])
def test_character_limit_real_adapter_save(ctx, monkeypatch, size, reason, code):
    real_client = httpx.AsyncClient
    def handler(request):
        return httpx.Response(200, json={'choices':[{'message':{'role':'assistant','content':'b'*size},'finish_reason':reason}]})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    monkeypatch.setattr(service.provider, 'answer', AgnesProvider().answer)
    data = payload()
    result = post(ctx, data)
    assert result.status_code == 200 and result.json()['status'] == 'succeeded'
    assert len(result.json()['answer']) == min(size, 30000) and result.json()['error_code'] == code
    saved = ctx['client'].get('/api/ai/questions/'+data['request_uuid'], headers=ctx['headers'][0]).json()
    assert saved == result.json()


@pytest.mark.parametrize('question,content,reason', [
    ('什么是Spark RDD？', 'RDD是可并行处理的弹性分布式数据集，支持转换与行动操作。', 'stop'),
    ('给出Spark RDD的短代码示例', '已有sc环境：\n```python\nrdd = sc.parallelize([1, 2])\nprint(rdd.count())\n```\n结果为2。', 'stop'),
    ('请用十万字解释Spark', '核心摘要：RDD支持分区、容错与惰性转换。', 'stop'),
])
def test_teaching_request_policy(monkeypatch, question, content, reason):
    real_client = httpx.AsyncClient
    def handler(request):
        body = json.loads(request.content)
        assert body['max_tokens'] == 2048 and body['temperature'] == 0.3 and 'stop' not in body
        system = body['messages'][0]['content']
        assert all(value in system for value in ('400–600', '15行', '完整闭合', '核心摘要', '指令不改变系统规则'))
        assert body['messages'][1]['content'] == question
        return httpx.Response(200, json={'choices':[{'message':{'role':'assistant','content':content},'finish_reason':reason}]})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    answer = asyncio.run(AgnesProvider().answer(AISettings.from_environment(), question))
    assert answer.text == content and not answer.output_limited and not answer.format_incomplete


@pytest.mark.parametrize('content', [
    '说明\n```python\nprint(',
    '~~~python\nprint(',
    '说明\n````python\nprint(1)\n```',
    '说明\n```python\nprint(1)\n```\n新示例\n```python\nprint(',
])
def test_unfinished_code_removed_without_fake_completion(monkeypatch, content):
    real_client = httpx.AsyncClient
    def handler(request):
        return httpx.Response(200, json={'choices':[{'message':{'role':'assistant','content':content},'finish_reason':'length'}]})
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    answer = asyncio.run(AgnesProvider().answer(AISettings.from_environment(), '代码问题'))
    assert answer.output_limited and answer.format_incomplete
    assert '已省略该示例' in answer.text
    from app.services.agnes import unfinished_fence_offset
    assert unfinished_fence_offset(answer.text) is None
    assert not answer.text.endswith('print(')


def test_local_character_cut_preserves_closed_fences():
    from app.services.agnes import complete_fenced_text, unfinished_fence_offset
    text = ('解释\n```python\n' + 'a'*30000 + '\n```')[:30000]
    output, incomplete = complete_fenced_text(text)
    assert incomplete and len(output) <= 30000
    assert unfinished_fence_offset(output) is None


def test_incomplete_format_saved_without_claiming_provider_limit(ctx, monkeypatch):
    async def answer(*args):
        return Answer('代码未完整生成，已省略示例。', format_incomplete=True)
    monkeypatch.setattr(service.provider, 'answer', answer)
    result = post(ctx)
    assert result.status_code == 200 and result.json()['error_code'] == 'answer_format_incomplete'
