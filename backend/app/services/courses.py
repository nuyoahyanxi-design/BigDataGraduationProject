import hashlib
import json
from uuid import uuid5, NAMESPACE_URL
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError, OperationalError
from app.models import User, Resource, LearningProgress, CourseChapter, ChapterProgress, ChapterEvent
from app.services import learning
from app.services.resources import lock_admin, bump
from app.services.course_presentation import HIDDEN_LEARNER_RESOURCE_IDS, chapter_status
from app.core.resource_scope import visible_metadata
from app.core.video_catalog import playback_chapter, discovered_url

def visible(db, resource_id, user):
    resource = db.get(Resource,resource_id)
    if resource is None or ((resource.status!='published' or not visible_metadata(resource)) and user.role!='admin'):
        raise HTTPException(404,'Resource not found')
    return resource

def read_course(db, resource_id, user):
    resource=visible(db,resource_id,user)
    chapters=db.scalars(select(CourseChapter).where(CourseChapter.resource_id==resource_id).order_by(CourseChapter.position)).all()
    rows={p.chapter_id:p for p in db.scalars(select(ChapterProgress).join(CourseChapter,CourseChapter.id==ChapterProgress.chapter_id)
          .where(CourseChapter.resource_id==resource_id,ChapterProgress.user_id==user.id))}
    progress=db.get(LearningProgress,(user.id,resource_id))
    return {'resource_id':resource_id,'title':resource.title,'content':resource.content,'status':resource.status,
            'course_status':chapter_status(sum(bool(p.completed_at) for p in rows.values()),len(chapters),len(rows)) if chapters else (progress.status if progress else 'not_started'),
            'chapters':[{**playback_chapter(ch, discover=user.role!='admin'),
                         'started':ch.id in rows, 'completed':bool(rows.get(ch.id) and rows[ch.id].completed_at)} for ch in chapters]}

def create_chapter(db, resource_id, user, payload):
    try:
        resource=lock_course(db,resource_id,user)
        if syllabus_started(db,resource_id):
            raise HTTPException(409,'Course syllabus is frozen after chapter learning starts')
        chapter=CourseChapter(resource_id=resource_id,created_at=learning.event_time(),**payload.model_dump())
        db.add(chapter);db.flush();identity=chapter.id;bump(resource);db.commit()
        return {'id':identity,'resource_id':resource_id,**payload.model_dump()}
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Chapter position already exists') from None
    except Exception:
        db.rollback();raise

def bridge(db, user_id, resource, progress, kind, stamp, received_at, source_uuid):
    before='not_started' if kind=='learning_start' else 'in_progress'
    after='in_progress' if kind=='learning_start' else 'completed'
    if kind=='learning_start':
        progress=LearningProgress(user_id=user_id,resource_id=resource.id,status=after,
            first_started_at=stamp,completed_at=None,updated_at=stamp)
        db.add(progress)
    else:
        progress.status=after;progress.completed_at=stamp;progress.updated_at=stamp
    db.flush()
    learning._append_event(db,event_uuid=str(uuid5(NAMESPACE_URL,f'course:{source_uuid}:{kind}')),
        user_id=user_id,resource_id=resource.id,event_type=kind,event_source='server',schema_version=1,
        resource_version=resource.version_no,session_id=None,occurred_at=stamp,received_at=received_at,
        client_occurred_at=None,is_effective=1,state_before=before,state_after=after,
        request_fingerprint=learning.fingerprint(user_id,resource.id,kind))
    return progress

def append_chapter_event(db, **values):
    record=ChapterEvent(**values);db.add(record);db.flush();return record

def act(db, user_id, resource_id, chapter_id, payload, received_at):
    seconds=round(payload.playback_seconds,3) if payload.playback_seconds is not None else None
    if seconds is not None and payload.event_type!='video_play':
        raise HTTPException(422,'Playback position only applies to video events')
    semantic=hashlib.sha256(json.dumps([user_id,resource_id,chapter_id,payload.event_type,seconds],separators=(',',':')).encode()).hexdigest()
    uuid=str(payload.event_uuid)
    db.rollback()
    for attempt in range(3):
        try:
            user=db.scalar(select(User).where(User.id==user_id).with_for_update().execution_options(populate_existing=True))
            if user is None or user.status!='active': raise HTTPException(401,'Authentication required')
            existing=db.scalar(select(ChapterEvent).where(ChapterEvent.event_uuid==uuid))
            if existing:
                if existing.request_fingerprint!=semantic: raise HTTPException(409,'Event UUID semantic conflict')
                return existing.result
            resource=db.scalar(select(Resource).where(Resource.id==resource_id).with_for_update(read=True))
            chapter=db.get(CourseChapter,chapter_id)
            if resource is None or resource.status!='published' or chapter is None or chapter.resource_id!=resource_id:
                raise HTTPException(404,'Published chapter not found')
            progress=db.get(LearningProgress,(user_id,resource_id))
            cp=db.get(ChapterProgress,(user_id,chapter_id))
            stamp=max(learning.event_time(),received_at,progress.updated_at if progress else received_at)
            if payload.event_type!='chapter_view' and cp is None:
                raise HTTPException(409,'Open the chapter before learning actions')
            if payload.event_type=='video_play' and not (chapter.video_url or discovered_url(resource_id, chapter_id)):
                raise HTTPException(409,'This chapter has no video')
            if cp is None:
                cp=ChapterProgress(user_id=user_id,chapter_id=chapter_id,first_started_at=stamp)
                db.add(cp)
            if progress is None:
                progress=bridge(db,user_id,resource,progress,'learning_start',stamp,received_at,uuid)
            effective=1
            if payload.event_type=='chapter_complete':
                effective=int(cp.completed_at is None)
                if effective:cp.completed_at=stamp
            db.flush()
            total=db.scalar(select(func.count()).select_from(CourseChapter).where(CourseChapter.resource_id==resource_id))
            completed=db.scalar(select(func.count()).select_from(ChapterProgress).join(CourseChapter)
                .where(ChapterProgress.user_id==user_id,CourseChapter.resource_id==resource_id,ChapterProgress.completed_at.is_not(None)))
            if completed==total and total>0 and progress.status!='completed':
                progress=bridge(db,user_id,resource,progress,'learning_complete',stamp,received_at,uuid)
            result={'event_uuid':uuid,'resource_id':resource_id,'chapter_id':chapter_id,'event_type':payload.event_type,
                    'is_effective':effective,'chapter_completed':cp.completed_at is not None,
                    'completed_chapters':completed,'total_chapters':total,'course_status':chapter_status(completed,total,1)}
            append_chapter_event(db,event_uuid=uuid,user_id=user_id,resource_id=resource_id,chapter_id=chapter_id,
                event_type=payload.event_type,occurred_at=stamp,playback_seconds=seconds,is_effective=effective,
                request_fingerprint=semantic,result=result)
            db.commit();return result
        except (IntegrityError, OperationalError) as error:
            db.rollback()
            if error.orig.args[0] in (1062,1205,1213) and attempt<2:continue
            raise HTTPException(503,'Retry with the same event UUID') from None
        except Exception:
            db.rollback();raise

def events(db,user_id,page,page_size):
    query=select(ChapterEvent).where(ChapterEvent.user_id==user_id)
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    rows=db.scalars(query.order_by(ChapterEvent.id.desc()).offset((page-1)*page_size).limit(page_size)).all()
    return {'total':total,'page':page,'page_size':page_size,'items':[
        {key:getattr(row,key) for key in ('event_uuid','resource_id','chapter_id','event_type','occurred_at','playback_seconds','is_effective')} for row in rows]}


def lock_course(db, resource_id, user):
    lock_admin(db,user)
    resource=db.scalar(select(Resource).where(Resource.id==resource_id).with_for_update())
    if resource is None or resource.status=='deleted':
        raise HTTPException(404,'Resource not found')
    return resource


def syllabus_started(db, resource_id):
    progress=db.scalar(select(ChapterProgress.chapter_id).join(CourseChapter).where(
        CourseChapter.resource_id==resource_id).limit(1))
    event=db.scalar(select(ChapterEvent.id).where(ChapterEvent.resource_id==resource_id).limit(1))
    return progress is not None or event is not None


def maintain_chapter(db,resource_id,chapter_id,user,payload=None):
    try:
        resource=lock_course(db,resource_id,user)
        chapter=db.scalar(select(CourseChapter).where(CourseChapter.id==chapter_id,
            CourseChapter.resource_id==resource_id).with_for_update())
        if chapter is None:
            raise HTTPException(404,'Chapter not found')
        frozen=syllabus_started(db,resource_id)
        if payload is None:
            if frozen:
                raise HTTPException(409,'Course syllabus is frozen: chapters cannot be deleted after learning starts')
            db.delete(chapter);bump(resource);db.flush();db.commit()
            return
        values=payload.model_dump()
        if frozen and values['position']!=chapter.position:
            raise HTTPException(409,'Course syllabus is frozen: chapter order cannot change after learning starts')
        if any(getattr(chapter,key)!=value for key,value in values.items()):
            for key,value in values.items():setattr(chapter,key,value)
            bump(resource)
        db.flush()
        result={'id':chapter.id,'resource_id':resource_id,**values}
        db.commit()
        return result
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,'Chapter order conflicts or chapter has learning records') from None
    except Exception:
        db.rollback();raise

