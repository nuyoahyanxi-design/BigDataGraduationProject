import secrets
from uuid import uuid4
from types import SimpleNamespace
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, func
import pytest
from app.main import app
from app.models import User, Resource, CourseChapter, AIQARecord, AICourseContext, LearningEvent, ChapterEvent
from app.services import ai_assistant as shared
from app.services import course_ai_retrieval as retrieval
from app.services.agnes import Answer, ProviderError
from conftest import SafeTestContext


@pytest.fixture(scope='module')
def course_ctx():
    prefix='cai_'+secrets.token_hex(6); password=secrets.token_urlsafe(24)
    users=[];resources=[];headers=[];chapters=[]
    with TestClient(app) as client:
        with app.state.session_factory() as db:
            baseline=[db.scalar(select(func.count()).select_from(model)) for model in (LearningEvent,ChapterEvent)]
        try:
            for i in range(2):
                response=client.post('/api/auth/register',json={'username':prefix+str(i),'password':password})
                assert response.status_code==201;users.append(response.json()['id'])
            with app.state.session_factory() as db:db.get(User,users[1]).role='admin';db.commit()
            for i in range(2):
                response=client.post('/api/auth/login',json={'username':prefix+str(i),'password':password})
                assert response.status_code==200;headers.append({'Authorization':'Bearer '+response.json()['access_token']})
            for i in range(2):
                response=client.post('/api/resources',headers=headers[1],json={'title':prefix+str(i),'summary':'课程AI测试简介',
                    'resource_type':'document','category_code':'data-engineering','tags':['spark'],'difficulty':1,'content':'测试课程'})
                assert response.status_code==201;resources.append(response.json()['id'])
                assert client.patch(f'/api/resources/{resources[-1]}/status',headers=headers[1],json={'status':'published'}).status_code==200
            for index,title in enumerate(['RDD与Lineage','SELECT查询、条件筛选与排序','Python列表','HDFS副本机制']):
                response=client.post(f'/api/resources/{resources[0]}/chapters',headers=headers[1],json={'title':title,'position':index+1,
                    'content':title+'是本章的知识点。','learning_objectives':[title],'knowledge_tags':['spark'],
                    'example_code':'print(1)','exercises':[title+'练习'],'video_url':'/demo/video.mp4'})
                assert response.status_code==201;chapters.append(response.json()['id'])
            yield SafeTestContext({'client':client,'headers':headers,'users':users,'resources':resources,'chapters':chapters})
        finally:
            with app.state.session_factory() as db:
                qa=select(AIQARecord.id).where(AIQARecord.user_id.in_(users))
                db.execute(delete(AICourseContext).where(AICourseContext.qa_record_id.in_(qa)))
                db.execute(delete(AIQARecord).where(AIQARecord.user_id.in_(users)))
                db.execute(delete(CourseChapter).where(CourseChapter.resource_id.in_(resources)))
                db.execute(delete(Resource).where(Resource.id.in_(resources)))
                db.execute(delete(User).where(User.id.in_(users)));db.commit()
                assert baseline==[db.scalar(select(func.count()).select_from(model)) for model in (LearningEvent,ChapterEvent)]


@pytest.fixture(autouse=True)
def config(monkeypatch,course_ctx):
    for key,value in {'AI_ASSISTANT_ENABLED':'true','AGNES_API_KEY':'test-placeholder','AGNES_MODEL':'test-model',
                      'AI_ALLOWED_RESOURCE_IDS':','.join(map(str,course_ctx['resources'])),
                      'AI_USER_DAILY_REQUEST_LIMIT':'100','AI_GLOBAL_DAILY_REQUEST_LIMIT':'1000'}.items():monkeypatch.setenv(key,value)
    async def answer(settings,question,context=None):return Answer('教学回答')
    monkeypatch.setattr(shared.provider,'answer',answer)


def body(ctx,question='SELECT条件筛选',**changes):
    return {'request_uuid':str(uuid4()),'question':question,'chapter_id':ctx['chapters'][1],
            'consent_version':'agnes-external-v1',**changes}


def post(ctx,data=None,course=None,headers=None):
    return ctx['client'].post(f"/api/resources/{course or ctx['resources'][0]}/ai/questions",json=data or body(ctx),
                              headers=ctx['headers'][0] if headers is None else headers)


def test_course_answer_real_references_and_shared_provider(course_ctx,monkeypatch):
    ctx=course_ctx;calls=[]
    async def answer(settings,question,context=None):
        calls.append(context);return Answer('SELECT用于查询。模型声称不存在的第999章，不作为引用。')
    monkeypatch.setattr(shared.provider,'answer',answer)
    response=post(ctx);assert response.status_code==200
    data=response.json();assert data['answer'] and data['status']=='succeeded'
    assert data['references']==[{'course_name':data['course_title'],'chapter_name':'SELECT查询、条件筛选与排序',
                                'chapter_id':ctx['chapters'][1],'position':2}]
    assert 'SELECT' in calls[0] and f"ID={ctx['chapters'][1]}" in calls[0] and len(calls[0])<=6000
    assert '分类：data-engineering' in calls[0] and '课程AI测试简介' in calls[0]


def test_nonexistent_knowledge_has_no_fake_references(course_ctx,monkeypatch):
    calls=[]
    async def answer(settings,question,context=None):calls.append(context);return Answer('通用知识解答')
    monkeypatch.setattr(shared.provider,'answer',answer)
    response=post(course_ctx,body(course_ctx,'Kubernetes Ingress',chapter_id=None))
    assert response.status_code==200 and response.json()['references']==[]
    assert response.json()['answer'].startswith(retrieval.FALLBACK) and calls==[None]


def test_no_matching_selected_chapter_does_not_forge_hit(course_ctx):
    response=post(course_ctx,body(course_ctx,'Kubernetes Ingress'))
    assert response.json()['references']==[]


def test_replay_frozen_after_edit_and_conflict(course_ctx,monkeypatch):
    ctx=course_ctx;data=body(ctx);calls=[]
    async def answer(settings,question,context=None):calls.append(context);return Answer('原回答')
    monkeypatch.setattr(shared.provider,'answer',answer)
    first=post(ctx,data).json()
    with app.state.session_factory() as db:
        ch=db.get(CourseChapter,ctx['chapters'][1]);original=ch.title;ch.title='临时测试更新标题';db.commit()
    try:
        assert post(ctx,data).json()==first and len(calls)==1
        conflict={**data,'question':'不同问题'};assert post(ctx,conflict).status_code==409
        read=ctx['client'].get(f"/api/resources/{ctx['resources'][0]}/ai/questions/{data['request_uuid']}",headers=ctx['headers'][0])
        assert read.json()['references']==first['references']
    finally:
        with app.state.session_factory() as db:db.get(CourseChapter,ctx['chapters'][1]).title=original;db.commit()


def test_old_resource_uuid_conflicts_with_course(course_ctx):
    ctx=course_ctx;data=body(ctx)
    assert post(ctx,data).status_code==200
    legacy={k:v for k,v in data.items() if k!='chapter_id'};legacy.update(mode='resource',resource_id=ctx['resources'][0])
    assert ctx['client'].post('/api/ai/questions',headers=ctx['headers'][0],json=legacy).status_code==409


@pytest.mark.parametrize('kind',['post','history','record'])
def test_anonymous_rejected(course_ctx,kind):
    ctx=course_ctx;path=f"/api/resources/{ctx['resources'][0]}/ai"
    response=post(ctx,headers={}) if kind=='post' else ctx['client'].get(path+('/history' if kind=='history' else '/questions/'+str(uuid4())))
    assert response.status_code==401


def test_nonexistent_course_and_foreign_chapter(course_ctx):
    assert post(course_ctx,course=18446744073709551614).status_code==404
    assert post(course_ctx,course=course_ctx['resources'][1]).status_code==422
    assert post(course_ctx,body(course_ctx,question='   ')).status_code==422


def test_unapproved_or_hidden(course_ctx,monkeypatch):
    monkeypatch.setenv('AI_ALLOWED_RESOURCE_IDS','')
    assert post(course_ctx).status_code==404
    assert post(course_ctx,course=406).status_code==404


def test_offline_course_masks_old_answer_and_references(course_ctx):
    ctx=course_ctx;data=body(ctx);assert post(ctx,data).status_code==200
    with app.state.session_factory() as db:
        db.get(Resource,ctx['resources'][0]).status='offline';db.commit()
    try:
        assert post(ctx).status_code==404
        response=ctx['client'].get(f"/api/resources/{ctx['resources'][0]}/ai/questions/{data['request_uuid']}",headers=ctx['headers'][0]).json()
        assert response['answer'] is None and response['references']==[] and response['course_title'] is None
    finally:
        with app.state.session_factory() as db:db.get(Resource,ctx['resources'][0]).status='published';db.commit()


def test_disabled_and_credential_question_do_not_call_model(course_ctx,monkeypatch):
    async def forbidden(*args):raise AssertionError('Provider must not be called')
    monkeypatch.setattr(shared.provider,'answer',forbidden)
    assert post(course_ctx,body(course_ctx,'API_KEY=placeholder')).status_code==422
    monkeypatch.setenv('AI_ASSISTANT_ENABLED','false')
    assert post(course_ctx).status_code==503


def test_no_chapters_falls_back_without_reference(course_ctx):
    response=post(course_ctx,body(course_ctx,chapter_id=None),course=course_ctx['resources'][1])
    assert response.status_code==200 and response.json()['references']==[]
    assert response.json()['answer'].startswith(retrieval.FALLBACK)


def test_development_wildcard_preserves_security(course_ctx,monkeypatch):
    monkeypatch.setenv('APP_ENV','development');monkeypatch.setenv('AI_ALLOWED_RESOURCE_IDS','*')
    assert post(course_ctx).status_code==200
    assert post(course_ctx,headers={}).status_code==401
    assert post(course_ctx,course=406).status_code==404
    assert post(course_ctx,body(course_ctx,'API_KEY=placeholder')).status_code==422
    ctx=course_ctx;data=body(ctx);assert post(ctx,data).status_code==200
    path=f"/api/resources/{ctx['resources'][0]}/ai/questions/{data['request_uuid']}"
    assert ctx['client'].get(path,headers=ctx['headers'][1]).status_code==404
    with app.state.session_factory() as db:db.get(Resource,ctx['resources'][0]).status='offline';db.commit()
    try:assert post(ctx).status_code==404
    finally:
        with app.state.session_factory() as db:db.get(Resource,ctx['resources'][0]).status='published';db.commit()


def test_production_wildcard_and_numeric_policy(course_ctx,monkeypatch):
    monkeypatch.setenv('APP_ENV','production');monkeypatch.setenv('AI_ALLOWED_RESOURCE_IDS','*')
    assert post(course_ctx).status_code==503
    monkeypatch.setenv('AI_ALLOWED_RESOURCE_IDS',str(course_ctx['resources'][0]))
    assert post(course_ctx).status_code==200
    assert post(course_ctx,body(course_ctx,chapter_id=None),course=course_ctx['resources'][1]).status_code==404


def test_ownership_and_history(course_ctx):
    ctx=course_ctx;data=body(ctx);first=post(ctx,data).json()
    path=f"/api/resources/{ctx['resources'][0]}/ai"
    assert ctx['client'].get(path+'/questions/'+data['request_uuid'],headers=ctx['headers'][1]).status_code==404
    assert post(ctx,data,headers=ctx['headers'][1]).status_code==404
    history=ctx['client'].get(path+'/history',headers=ctx['headers'][0]).json()
    assert any(r['request_uuid']==first['request_uuid'] and r['references']==first['references'] for r in history['items'])
    assert ctx['client'].get(path+'/history',headers=ctx['headers'][1]).json()['items']==[]


def test_common_quotas_and_general_mode(course_ctx,monkeypatch):
    ctx=course_ctx;monkeypatch.setenv('AI_USER_DAILY_REQUEST_LIMIT','1')
    assert post(ctx).status_code==429
    response=ctx['client'].post('/api/ai/questions',headers=ctx['headers'][0],json={'request_uuid':str(uuid4()),
        'question':'通用问题','mode':'general','resource_id':None,'consent_version':'agnes-external-v1'})
    assert response.status_code==429
    monkeypatch.setenv('AI_USER_DAILY_REQUEST_LIMIT','100')
    assert ctx['client'].post('/api/ai/questions',headers=ctx['headers'][0],json={'request_uuid':str(uuid4()),
        'question':'通用问题','mode':'general','resource_id':None,'consent_version':'agnes-external-v1'}).json()['status']=='succeeded'


def test_failure_record_uses_existing_timeout_logic(course_ctx,monkeypatch):
    async def answer(*args):raise ProviderError('provider_timeout',504,True)
    monkeypatch.setattr(shared.provider,'answer',answer)
    data=body(course_ctx);response=post(course_ctx,data)
    assert response.status_code==504 and response.json()['error_code']=='provider_timeout'
    assert response.json()['references'][0]['chapter_id']==course_ctx['chapters'][1]


def test_metadata_reservation_rolls_back_atomically(course_ctx,monkeypatch):
    from sqlalchemy import event
    def fail(*args):raise RuntimeError('fixture metadata write failure')
    event.listen(AICourseContext,'before_insert',fail)
    data=body(course_ctx)
    try:
        with pytest.raises(RuntimeError):post(course_ctx,data)
        with app.state.session_factory() as db:assert db.scalar(select(AIQARecord).where(AIQARecord.request_uuid==data['request_uuid'])) is None
    finally:event.remove(AICourseContext,'before_insert',fail)


def test_retrieval_top3_budget_and_unclosed_code():
    resource=SimpleNamespace(title='Spark课程',summary='课程简介',category_code='data-engineering',tags=['spark'])
    chapters=[SimpleNamespace(id=i,title='RDD '+str(i),position=i,content='RDD正文\n\n'+'x'*20000+'\n\n```python\n未闭合',
        knowledge_tags=['rdd'],learning_objectives=['学习RDD'],example_code='print(1)',exercises=['RDD练习']) for i in range(1,6)]
    context,refs=retrieval.retrieve(resource,chapters,'RDD')
    assert len(refs)==3 and len(context)<=6000 and [r['chapter_id'] for r in refs]==[1,2,3]
    from app.services.agnes import unfinished_fence_offset
    assert unfinished_fence_offset(context) is None and '未闭合' not in context


def test_credential_material_not_sent():
    resource=SimpleNamespace(title='Spark',summary='简介',category_code='data-engineering',tags=['spark'])
    chapter=SimpleNamespace(id=1,title='RDD',position=1,content='RDD\n\nAPI_KEY=placeholder',knowledge_tags=['rdd'],
        learning_objectives=[],example_code='',exercises=[])
    with pytest.raises(Exception) as error:retrieval.retrieve(resource,[chapter],'RDD')
    assert getattr(error.value,'status_code',None)==422


@pytest.mark.parametrize('mode',['course','general'])
def test_final_acceptance_anonymous_modes_do_not_call_provider(course_ctx,monkeypatch,mode):
    async def forbidden(*args):raise AssertionError('Anonymous requests must not call provider')
    monkeypatch.setattr(shared.provider,'answer',forbidden)
    if mode=='course':
        response=post(course_ctx,headers={})
    else:
        response=course_ctx['client'].post('/api/ai/questions',json={'request_uuid':str(uuid4()),
            'question':'Spark RDD是什么','mode':'general','resource_id':None,'consent_version':'agnes-external-v1'})
    assert response.status_code==401


def test_final_acceptance_denial_has_no_qa_write(course_ctx,monkeypatch):
    ctx=course_ctx;monkeypatch.setenv('APP_ENV','production')
    monkeypatch.setenv('AI_ALLOWED_RESOURCE_IDS',str(ctx['resources'][1]))
    async def forbidden(*args):raise AssertionError('Unapproved material must not be sent')
    monkeypatch.setattr(shared.provider,'answer',forbidden)
    data=body(ctx)
    assert post(ctx,data).status_code==404
    with app.state.session_factory() as db:
        assert db.scalar(select(AIQARecord.id).where(AIQARecord.request_uuid==data['request_uuid'])) is None


def test_final_acceptance_course_ai_does_not_emit_learning_events(course_ctx,monkeypatch):
    ctx=course_ctx;captured=[]
    async def answer(settings,question,context=None):captured.append(context);return Answer('教学回答')
    monkeypatch.setattr(shared.provider,'answer',answer)
    with app.state.session_factory() as db:
        before=[db.scalar(select(func.count()).select_from(model)) for model in (LearningEvent,ChapterEvent)]
    response=post(ctx);assert response.status_code==200
    refs=response.json()['references'];assert refs
    assert all(f"ID={ref['chapter_id']}" in captured[0] and ref['chapter_name'] in captured[0] for ref in refs)
    with app.state.session_factory() as db:
        assert before==[db.scalar(select(func.count()).select_from(model)) for model in (LearningEvent,ChapterEvent)]


def test_development_continuous_course_and_general_after_twenty_requests(course_ctx,monkeypatch):
    ctx=course_ctx;monkeypatch.setenv('APP_ENV','development')
    monkeypatch.setenv('AI_ALLOWED_RESOURCE_IDS','*')
    monkeypatch.delenv('AI_USER_DAILY_REQUEST_LIMIT',raising=False)
    monkeypatch.delenv('AI_GLOBAL_DAILY_REQUEST_LIMIT',raising=False)
    calls=[]
    async def answer(settings,question,context=None):calls.append(context);return Answer('测试回答')
    monkeypatch.setattr(shared.provider,'answer',answer)
    data=body(ctx)
    for i in range(22):
        if i%2==0:response=post(ctx,data if i==0 else body(ctx))
        else:response=ctx['client'].post('/api/ai/questions',headers=ctx['headers'][0],json={'request_uuid':str(uuid4()),
            'question':'通用学习问题','mode':'general','resource_id':None,'consent_version':'agnes-external-v1'})
        assert response.status_code==200
    assert len(calls)==22
    assert post(ctx,data).status_code==200 and len(calls)==22


def test_limit_diagnostic_logs_are_allowlisted(course_ctx,monkeypatch,tmp_path):
    import json
    from app.services import ai_diagnostics
    path=tmp_path/'metadata.jsonl';monkeypatch.setattr(ai_diagnostics,'PATH',path)
    ctx=course_ctx;monkeypatch.setenv('AI_USER_DAILY_REQUEST_LIMIT','1')
    assert post(ctx).status_code==429
    logs=[json.loads(line) for line in path.read_text().splitlines()]
    assert logs[-1]['source']=='user_daily' and logs[-1]['mode']=='course'
    assert logs[-1]['http_status']==429 and logs[-1]['user_id']==ctx['users'][0]
    assert set(logs[-1])=={'at_utc','event','user_id','mode','source','http_status','latency_ms'}
    assert 'SELECT' not in path.read_text() and 'test-placeholder' not in path.read_text()


@pytest.mark.parametrize('question,expected', [
    ('MySQL索引为什么可以提高查询速度？', True),
    ('MySQL如何训练深度学习模型？', False),
    ('MySQL如何训练一个深度学习模型？', False),
])
def test_formal_mysql_relevance_boundary(course_ctx, monkeypatch, question, expected):
    monkeypatch.setenv('AI_ALLOWED_RESOURCE_IDS','1071')
    calls=[]
    async def answer(settings, question, context=None):
        calls.append(context)
        return Answer('模型提及不存在章节也不能成为references。')
    monkeypatch.setattr(shared.provider,'answer',answer)
    with app.state.session_factory() as db:
        chapters=db.scalars(select(CourseChapter).where(CourseChapter.resource_id==1071)).all()
        first=min(chapters,key=lambda ch:ch.position).id
        actual={ch.id:ch.title for ch in chapters}
    response=post(course_ctx,body(course_ctx,question,chapter_id=first),course=1071)
    assert response.status_code==200
    data=response.json()
    if expected:
        assert data['references'] and calls[0]
        assert all(actual[r['chapter_id']]==r['chapter_name'] and f"ID={r['chapter_id']}" in calls[0] for r in data['references'])
    else:
        assert data['references']==[] and calls==[None]
        assert data['source']==retrieval.FALLBACK
        assert data['answer'].startswith(retrieval.FALLBACK)


def test_current_chapter_boost_cannot_cross_relevance_floor(monkeypatch):
    resource=SimpleNamespace(title='课程',summary='简介',category_code='test',tags=[])
    ch=SimpleNamespace(id=1,position=1,title='章节',content='正文',knowledge_tags=[],learning_objectives=[],example_code='',exercises=[])
    monkeypatch.setattr(retrieval,'score',lambda ch,q:retrieval.MIN_RELEVANCE-.001)
    assert retrieval.retrieve(resource,[ch],'问题',chapter_id=1)==(None,[])
    monkeypatch.setattr(retrieval,'score',lambda ch,q:retrieval.MIN_RELEVANCE)
    assert len(retrieval.retrieve(resource,[ch],'问题',chapter_id=1)[1])==1


@pytest.mark.parametrize('rid,question', [
    (1068,'什么是RDD？'),(1068,'RDD缓存与血缘如何帮助容错？'),
    (1069,'DataFrame如何筛选和聚合？'),(1069,'Parquet如何读写？'),
    (1070,'HDFS数据块和副本是什么？'),
    (1071,'什么是关系型数据库？'),(1071,'SELECT如何筛选并排序？'),
    (1071,'事务如何提交和回滚？'),(1072,'如何划分训练集和测试集？'),
])
def test_normal_formal_course_questions_still_have_context(course_ctx,rid,question):
    with app.state.session_factory() as db:
        resource=db.get(Resource,rid)
        chapters=db.scalars(select(CourseChapter).where(CourseChapter.resource_id==rid)).all()
        context,refs=retrieval.retrieve(resource,chapters,question)
        assert context and refs
