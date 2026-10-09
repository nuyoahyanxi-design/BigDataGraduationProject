"""CRUD tests only touch isolated fixtures; existing courses are not edited."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from sqlalchemy import select,func
from app.main import app
from app.models import Resource,CourseChapter,ChapterProgress,ChapterEvent
from app.services import courses
from test_courses import ctx,setup,action,chapter,snapshot


def put(ctx,rid,cid,payload,actor='admin'):
    return ctx['client'].put(f'/api/resources/{rid}/chapters/{cid}',headers=ctx[actor],json=payload)

def remove(ctx,rid,cid,actor='admin'):
    return ctx['client'].delete(f'/api/resources/{rid}/chapters/{cid}',headers=ctx[actor])

def test_create_update_delete_without_learning(ctx):
    rid,cids=setup(ctx,1)
    payload={**chapter(),'title':'完整教学章节','position':3,'content':'# 更新\n教学正文','learning_objectives':['解释RDD'],
             'example_code':'print("example")','exercises':['完成练习'],'video_url':'/demo/video.mp4'}
    response=put(ctx,rid,cids[0],payload)
    assert response.status_code==200 and response.json()['position']==3
    course=ctx['client'].get(f'/api/resources/{rid}/course',headers=ctx['learner']).json()
    assert course['chapters'][0]['content']==payload['content']
    assert course['chapters'][0]['learning_objectives']==payload['learning_objectives']
    assert remove(ctx,rid,cids[0]).status_code==204
    assert ctx['client'].get(f'/api/resources/{rid}/course',headers=ctx['admin']).json()['chapters']==[]
    assert remove(ctx,rid,cids[0]).status_code==404

@pytest.mark.parametrize('method',['post','put','delete'])
@pytest.mark.parametrize('actor',['anonymous','learner'])
def test_mutation_admin_only(ctx,method,actor):
    rid,cids=setup(ctx,1)
    url=f'/api/resources/{rid}/chapters'+('' if method=='post' else f'/{cids[0]}')
    kwargs={'headers':{} if actor=='anonymous' else ctx['learner']}
    if method!='delete':kwargs['json']=chapter(2)
    assert ctx['client'].request(method,url,**kwargs).status_code==(401 if actor=='anonymous' else 403)


def test_chapter_must_belong_to_resource(ctx):
    rid,cids=setup(ctx,1);other,_=setup(ctx,0)
    assert put(ctx,other,cids[0],chapter()).status_code==404
    assert remove(ctx,other,cids[0]).status_code==404
    assert put(ctx,rid,18446744073709551615,chapter()).status_code==404


def test_conflicting_order_rolls_back(ctx):
    rid,cids=setup(ctx,2)
    with app.state.session_factory() as db:before=db.get(Resource,rid).version_no
    assert put(ctx,rid,cids[0],chapter(2)).status_code==409
    course=ctx['client'].get(f'/api/resources/{rid}/course',headers=ctx['admin']).json()
    assert [ch['position'] for ch in course['chapters']]==[1,2]
    with app.state.session_factory() as db:assert db.get(Resource,rid).version_no==before


def test_learning_allows_content_edit_but_freezes_structure(ctx):
    rid,cids=setup(ctx,2)
    action(ctx,rid,cids[0]);action(ctx,rid,cids[0],'chapter_complete')
    before=snapshot(ctx,rid)
    with app.state.session_factory() as db:
        events=[(r.id,r.result,r.request_fingerprint) for r in db.scalars(select(ChapterEvent).where(ChapterEvent.resource_id==rid))]
    updated={**chapter(),'title':'教学内容修订','content':'# 安全修订','learning_objectives':['新说明'],'exercises':['练习'],'example_code':'print(1)','video_url':'/demo/video.mp4'}
    assert put(ctx,rid,cids[0],updated).status_code==200
    assert snapshot(ctx,rid)==before
    assert put(ctx,rid,cids[0],{**updated,'position':3}).status_code==409
    assert remove(ctx,rid,cids[0]).status_code==409
    assert remove(ctx,rid,cids[1]).status_code==409
    assert ctx['client'].post(f'/api/resources/{rid}/chapters',headers=ctx['admin'],json=chapter(3)).status_code==409
    with app.state.session_factory() as db:
        assert [(r.id,r.result,r.request_fingerprint) for r in db.scalars(select(ChapterEvent).where(ChapterEvent.resource_id==rid))]==events
    action(ctx,rid,cids[1]);assert action(ctx,rid,cids[1],'chapter_complete').json()['course_status']=='completed'


def test_rollback_on_update_failure(ctx,monkeypatch):
    rid,cids=setup(ctx,1)
    def fail(resource):raise RuntimeError('injected update failure')
    with monkeypatch.context() as patch:
        patch.setattr(courses,'bump',fail)
        with pytest.raises(RuntimeError):put(ctx,rid,cids[0],{**chapter(),'title':'不应保存'})
    with app.state.session_factory() as db:assert db.get(CourseChapter,cids[0]).title==chapter()['title']
    with monkeypatch.context() as patch:
        patch.setattr(courses,'bump',fail)
        with pytest.raises(RuntimeError):remove(ctx,rid,cids[0])
    with app.state.session_factory() as db:assert db.get(CourseChapter,cids[0]) is not None

@pytest.mark.parametrize('values',[{'title':' '},{'position':0},{'content':''},{'video_url':'https://example.com/x.mp4'},
                                  {'video_url':'/videos/../x.mp4'},{'learning_objectives':[' ']},{'exercises':['x'*1001]},
                                  {'resource_id':406},{'knowledge_tags':['RDD','RDD']}])
def test_update_validation(ctx,values):
    rid,cids=setup(ctx,1)
    assert put(ctx,rid,cids[0],{**chapter(),**values}).status_code==422


def test_parallel_add_same_position_and_stable_noop(ctx):
    rid,cids=setup(ctx,1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:ctx['client'].post(f'/api/resources/{rid}/chapters',headers=ctx['admin'],json=chapter(2)),range(2)))
    assert sorted(r.status_code for r in results)==[201,409]
    with app.state.session_factory() as db:before=db.get(Resource,rid).version_no
    assert put(ctx,rid,cids[0],chapter()).status_code==200
    with app.state.session_factory() as db:assert db.get(Resource,rid).version_no==before


def test_deleted_course_rejects_chapter_mutation(ctx):
    rid,cids=setup(ctx,1)
    with app.state.session_factory() as db:db.get(Resource,rid).status='deleted';db.commit()
    assert put(ctx,rid,cids[0],chapter()).status_code==404
    assert remove(ctx,rid,cids[0]).status_code==404
    assert ctx['client'].post(f'/api/resources/{rid}/chapters',headers=ctx['admin'],json=chapter(2)).status_code==404


def test_course_metadata_and_visibility_lifecycle(ctx):
    c=ctx['client']
    response=c.post('/api/resources',headers=ctx['admin'],json={'title':'后台创建课程','summary':'课程简介','resource_type':'course','category_code':'data-engineering','tags':['spark'],'content':'课程介绍'})
    assert response.status_code==201
    rid=response.json()['id'];ctx['rids'].append(rid)
    data={key:response.json()[key] for key in ('title','summary','resource_type','category_code','tags','difficulty','content','content_url','source_name','license_note')}
    data['title']='后台修订课程'
    assert c.put(f'/api/resources/{rid}',headers=ctx['admin'],json=data).status_code==200
    assert c.patch(f'/api/resources/{rid}/status',headers=ctx['admin'],json={'status':'published'}).status_code==200
    assert c.get(f'/api/resources/{rid}',headers=ctx['learner']).status_code==200
    assert c.patch(f'/api/resources/{rid}/status',headers=ctx['admin'],json={'status':'offline'}).status_code==200
    assert c.get(f'/api/resources/{rid}',headers=ctx['learner']).status_code==404
    assert c.get(f'/api/resources/{rid}',headers=ctx['admin']).status_code==200
    assert any(row['id']==rid for row in c.get('/api/resources',headers=ctx['admin'],params={'resource_type':'course','status':'all','q':'后台修订课程'}).json()['items'])
