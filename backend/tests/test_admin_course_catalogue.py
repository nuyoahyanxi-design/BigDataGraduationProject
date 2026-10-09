"""Catalogue correction: real formal data read-only and isolated CRUD fixtures."""
import json
from pathlib import Path
import pytest
from app.main import app
from app.models import Resource
from app.services import admin
from test_courses import ctx,setup,chapter


def query(ctx,**params):
    return ctx['client'].get('/api/admin/courses',headers=ctx['admin'],params=params)


def test_all_five_existing_formal_courses_have_correct_counts(ctx):
    response=query(ctx,page_size=100)
    assert response.status_code==200
    result=response.json()
    expected=set(range(1068,1073))
    # Administrators can now create additional real courses. Preserve those data;
    # the five seeded courses must still all be present with their original chapters.
    formal = [row for row in result['items'] if row['id'] in expected]
    assert {row['id'] for row in formal}==expected
    assert result['total']>=5
    assert all(row['chapter_count']==5 and row['resource_type']=='document' and row['updated_at'] for row in formal)
    Path('../outputs/admin-course-list-real-query.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))

@pytest.mark.parametrize('resource_type',['document','course','exercise'])
def test_all_types_and_zero_chapter_first_chapter_creation(ctx,resource_type):
    rid,_=setup(ctx,0)
    with app.state.session_factory() as db:
        row=db.get(Resource,rid);row.resource_type=resource_type;db.commit()
    result=query(ctx,q='课程验收',page_size=100).json()
    row=next(row for row in result['items'] if row['id']==rid)
    assert row['chapter_count']==0 and row['resource_type']==resource_type
    assert ctx['client'].post(f'/api/resources/{rid}/chapters',headers=ctx['admin'],json=chapter()).status_code==201
    row=next(row for row in query(ctx,q='课程验收',page_size=100).json()['items'] if row['id']==rid)
    assert row['chapter_count']==1
    with app.state.session_factory() as db:assert db.get(Resource,rid).resource_type==resource_type


def test_exclusions_before_search_and_pagination_resource_admin_retains_tests(ctx):
    assert query(ctx,q='数据库验收资源').json()['total']==0
    assert query(ctx,q='联调演示资源').json()['items']==[]
    c=ctx['client']
    resources=c.get('/api/resources',headers=ctx['admin'],params={'status':'all','q':'数据库验收资源','page_size':100}).json()
    assert {r['id'] for r in resources['items']}==set(range(1,7))
    assert c.get('/api/resources/406',headers=ctx['admin']).status_code==200
    pages=[query(ctx,page=page,page_size=2).json() for page in range(1,6)]
    ids=[row['id'] for page in pages for row in page['items']]
    assert not set(ids)&set(admin.COURSE_TEST_IDS)
    assert len(ids)==len(set(ids))
    assert all(page['total']==pages[0]['total'] for page in pages)


def test_exact_test_title_filter_not_general_database_keyword(ctx):
    rid,_=setup(ctx,0)
    with app.state.session_factory() as db:db.get(Resource,rid).title='数据库验收资源1';db.commit()
    assert not any(row['id']==rid for row in query(ctx,q='数据库验收资源',page_size=100).json()['items'])
    with app.state.session_factory() as db:db.get(Resource,rid).title='数据库正式课程';db.commit()
    assert any(row['id']==rid for row in query(ctx,q='数据库正式课程',page_size=100).json()['items'])


def test_published_offline_search_and_counts(ctx):
    rid,_=setup(ctx,2)
    assert any(row['id']==rid and row['chapter_count']==2 for row in query(ctx,q='课程验收',status='published',page_size=100).json()['items'])
    assert ctx['client'].patch(f'/api/resources/{rid}/status',headers=ctx['admin'],json={'status':'offline'}).status_code==200
    assert not any(row['id']==rid for row in query(ctx,status='published',page_size=100).json()['items'])
    assert any(row['id']==rid and row['chapter_count']==2 for row in query(ctx,status='offline',page_size=100).json()['items'])

@pytest.mark.parametrize('actor',['anonymous','learner'])
def test_only_admin_can_read_catalogue(ctx,actor):
    response=ctx['client'].get('/api/admin/courses',headers={} if actor=='anonymous' else ctx['learner'])
    assert response.status_code==(401 if actor=='anonymous' else 403)

@pytest.mark.parametrize('params',[{'resource_type':'course'},{'user_id':1},{'page':0},{'page_size':101},{'status':'deleted'},{'q':''}])
def test_invalid_catalogue_parameters_rejected(ctx,params):
    assert query(ctx,**params).status_code==422
