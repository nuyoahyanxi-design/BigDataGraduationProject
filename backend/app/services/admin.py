import json
import re
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select, func
from app.models import User, Resource, CourseChapter
from app.schemas.resources import ResourceSummary
from app.schemas.admin import BatchInfo, BatchList

ROOT = Path(__file__).resolve().parents[3]
OUTPUTS = ROOT / 'outputs'
STAGES = [
    ('数据管道','spark-data-pipeline-latest.json','清洗输出行为条数'),
    ('用户画像','user-profile-latest.json','画像行数'),
    ('推荐计算','recommendation-latest.json','推荐行数'),
    ('看板统计','dashboard-latest.json','趋势自然日行数'),
]


def list_users(db,page,page_size):
    return {'items':db.scalars(select(User).order_by(User.id.desc()).offset((page-1)*page_size).limit(page_size)).all(),
            'total':db.scalar(select(func.count()).select_from(User)), 'page':page,'page_size':page_size}


def read_json(path):
    with path.open('rb') as stream: raw=stream.read(2*1024*1024+1)
    if len(raw)>2*1024*1024: raise ValueError('Oversize publication')
    result=json.loads(raw)
    if not isinstance(result,dict): raise ValueError('Invalid publication')
    return result


def utc(value):
    if value is None: return None
    if not isinstance(value,str): raise ValueError('Invalid time')
    stamp=datetime.fromisoformat(value.replace('Z','+00:00'))
    if stamp.tzinfo is None: stamp=stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc).isoformat().replace('+00:00','Z')


def batches():
    items=[]
    for stage,filename,label in STAGES:
        item=BatchInfo(stage=stage,status='not_available',count_label=label,source=filename)
        try:
            record=read_json(OUTPUTS/filename)
            identity=record['batch_id']
            if not isinstance(identity,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,160}',identity): raise ValueError('Invalid batch')
            if record['status']!='completed': raise ValueError('Incomplete publication')
            stamp=record.get('generated_at'); cutoff=record.get('as_of_utc'); message=None
            if stage=='数据管道':
                quality=read_json(OUTPUTS/'spark-data-pipeline'/identity/'quality-report.json')
                if quality['batch_id']!=identity: raise ValueError('Wrong quality batch')
                count=quality['output_count']; cutoff=quality['snapshot_at']
                message='旧管道产物未记录生成时间；仅展示真实快照截止时间'
            elif stage=='用户画像': count=record['rows']
            elif stage=='推荐计算': count=record['counts']['output_rows']
            else: count=len(record['metrics']['behavior']['daily'])
            if type(count) is not int or count<0: raise ValueError('Invalid count')
            item=BatchInfo(stage=stage,batch_id=identity,status='completed',generated_at=utc(stamp),as_of_utc=utc(cutoff),
                data_count=count,count_label=label,source=filename,message=message)
        except FileNotFoundError: item.message='尚无该阶段已发布记录或配套报告'
        except (OSError,ValueError,KeyError,TypeError):
            item.status='unavailable'; item.message='发布记录不完整或不可读，请核查阶段产物'
        items.append(item)
    return BatchList(items=items)


# Only the course-management catalogue excludes these fixtures. Other views stay unchanged.
COURSE_TEST_IDS = frozenset({1,2,3,4,5,6,406})
COURSE_TEST_TITLES = frozenset('数据库验收资源'+str(i) for i in range(1,7))

def list_courses(db,page,page_size,q,status):
    from app.schemas.admin import AdminCourseSummary
    counts=select(CourseChapter.resource_id,func.count().label('chapter_count')).group_by(CourseChapter.resource_id).subquery()
    query=select(Resource,func.coalesce(counts.c.chapter_count,0)).outerjoin(counts,counts.c.resource_id==Resource.id).where(
        Resource.status!='deleted',Resource.id.not_in(COURSE_TEST_IDS),Resource.title.not_in(COURSE_TEST_TITLES))
    if status!='all':query=query.where(Resource.status==status)
    if q:query=query.where(Resource.title.contains(q,autoescape=True))
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    rows=db.execute(query.order_by(Resource.id.desc()).offset((page-1)*page_size).limit(page_size)).all()
    return {'items':[AdminCourseSummary(**ResourceSummary.model_validate(resource).model_dump(),chapter_count=count)
                     for resource,count in rows], 'total':total,'page':page,'page_size':page_size}
