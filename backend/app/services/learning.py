import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError, OperationalError

from app.models import User, Resource, LearningProgress, Favorite, LearningEvent
from app.schemas.learning import EventReceipt
from app.services.users import utc_now


def event_time():
    stamp=utc_now()
    return stamp.replace(microsecond=stamp.microsecond//1000*1000)


def fingerprint(user_id,resource_id,event_type):
    raw=json.dumps([1,user_id,resource_id,event_type],separators=(',',':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def existing_receipt(db,event_uuid,semantic):
    event=db.scalar(select(LearningEvent).where(LearningEvent.event_uuid==event_uuid))
    if event is None:
        return None
    if event.request_fingerprint!=semantic:
        raise HTTPException(409,'Event UUID conflicts with request semantics')
    return EventReceipt.model_validate(event)


def _append_event(db,**values):
    record=LearningEvent(**values)
    db.add(record)
    db.flush()
    return record


def _perform(db,user_id,resource_id,kind,payload,received_at,semantic):
    # A new transaction avoids the snapshot opened by the authentication lookup.
    actor=db.scalar(select(User).where(User.id==user_id).with_for_update(read=kind=='resource_view')
                    .execution_options(populate_existing=True))
    if actor is None or actor.status!='active':
        raise HTTPException(401,'Authentication required')
    original=existing_receipt(db,str(payload.event_uuid),semantic)
    if original is not None:
        return original
    resource=db.scalar(select(Resource).where(Resource.id==resource_id).with_for_update(read=True))
    if resource is None:
        raise HTTPException(404,'Resource not found')
    favorite=None
    if kind in ('favorite_add','favorite_remove'):
        favorite=db.get(Favorite,(user_id,resource_id))
    if resource.status!='published' and not (kind=='favorite_remove' and favorite is not None):
        raise HTTPException(404,'Resource not found')
    progress=None
    if kind in ('learning_start','learning_complete'):
        progress=db.get(LearningProgress,(user_id,resource_id))
    stamp=max(event_time(),received_at)
    if progress is not None:
        stamp=max(stamp,progress.updated_at)
    if favorite is not None:
        stamp=max(stamp,favorite.created_at)
    effective=1;before=None;after=None
    if kind=='learning_start':
        before=progress.status if progress else 'not_started'
        if progress is None:
            after='in_progress'
            db.add(LearningProgress(user_id=user_id,resource_id=resource_id,status=after,
                                   first_started_at=stamp,completed_at=None,updated_at=stamp))
        else:
            after=before;effective=0
    elif kind=='learning_complete':
        if progress is None:
            raise HTTPException(409,'Start learning before completing a resource')
        from app.models.courses import CourseChapter,ChapterProgress
        total=db.scalar(select(func.count()).select_from(CourseChapter).where(CourseChapter.resource_id==resource_id))
        done=db.scalar(select(func.count()).select_from(ChapterProgress).join(CourseChapter).where(CourseChapter.resource_id==resource_id,ChapterProgress.user_id==user_id,ChapterProgress.completed_at.is_not(None))) if total else 0
        if total and done!=total:
            raise HTTPException(409,'Complete all course chapters first')
        before=progress.status;after='completed'
        if before=='completed':
            effective=0
        else:
            # Chapter courses cannot bypass completion through the legacy endpoint.
            # Previously completed records and resources without chapters retain their semantics.
            from app.models.courses import CourseChapter, ChapterProgress
            chapter_count=db.scalar(select(func.count()).select_from(CourseChapter).where(CourseChapter.resource_id==resource_id))
            completed_count=db.scalar(select(func.count()).select_from(ChapterProgress).join(CourseChapter)
                .where(CourseChapter.resource_id==resource_id,ChapterProgress.user_id==user_id,ChapterProgress.completed_at.is_not(None))) if chapter_count else 0
            if chapter_count and completed_count!=chapter_count:
                raise HTTPException(409,'Complete all course chapters first')
            progress.status=after;progress.completed_at=stamp;progress.updated_at=stamp
    elif kind=='favorite_add':
        before='favorited' if favorite else 'not_favorited';after='favorited'
        if favorite:
            effective=0
        else:
            db.add(Favorite(user_id=user_id,resource_id=resource_id,created_at=stamp))
    elif kind=='favorite_remove':
        before='favorited' if favorite else 'not_favorited';after='not_favorited'
        if favorite:
            db.delete(favorite)
        else:
            effective=0
    db.flush()  # Persist state inside the transaction before attempting the event insert.
    record=_append_event(db,event_uuid=str(payload.event_uuid),user_id=user_id,resource_id=resource_id,
                         event_type=kind,event_source='client' if kind=='resource_view' else 'server',
                         schema_version=1,resource_version=resource.version_no,
                         session_id=str(payload.session_id) if payload.session_id else None,
                         occurred_at=stamp,received_at=received_at,
                         client_occurred_at=getattr(payload,'client_occurred_at',None),
                         is_effective=effective,state_before=before,state_after=after,
                         request_fingerprint=semantic)
    db.commit()
    db.refresh(record)
    return EventReceipt.model_validate(record)


def record_behavior(db,user_id,resource_id,kind,payload,received_at):
    semantic=fingerprint(user_id,resource_id,kind)
    original=existing_receipt(db,str(payload.event_uuid),semantic)
    if original is not None:
        return original
    db.rollback()
    for attempt in range(3):
        try:
            return _perform(db,user_id,resource_id,kind,payload,received_at,semantic)
        except IntegrityError as error:
            db.rollback()
            if error.orig.args[0]==1062:
                original=existing_receipt(db,str(payload.event_uuid),semantic)
                if original is not None:
                    return original
            raise
        except OperationalError as error:
            db.rollback()
            if error.orig.args[0] in (1205,1213):
                if attempt<2:
                    continue
                raise HTTPException(503,'Operation temporarily unavailable; retry with the same event UUID') from None
            raise
        except Exception:
            db.rollback()
            raise


def paginate(db,query,page,page_size):
    total=db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    items=db.scalars(query.offset((page-1)*page_size).limit(page_size)).all()
    return {'items':items,'total':total,'page':page,'page_size':page_size}


def progress_page(db,user_id,page,page_size,resource_id,status):
    from app.services.course_presentation import effective_progress_status
    if status=='not_started' and resource_id is None:
        raise HTTPException(422,'resource_id required for not_started query')
    derived=effective_progress_status(user_id)
    from app.services.course_presentation import effective_progress_time
    query=select(LearningProgress.resource_id,derived.label('status'),effective_progress_time(user_id,'first_started_at').label('first_started_at'),
                 effective_progress_time(user_id,'completed_at').label('completed_at'),effective_progress_time(user_id,'updated_at').label('updated_at')).where(LearningProgress.user_id==user_id)
    if resource_id is not None:
        query=query.where(LearningProgress.resource_id==resource_id)
        if db.scalar(select(LearningProgress.resource_id).where(LearningProgress.user_id==user_id,LearningProgress.resource_id==resource_id)) is None:
            resource=db.get(Resource,resource_id)
            if resource is None or resource.status!='published':
                raise HTTPException(404,'Resource not found')
            item={'resource_id':resource_id,'status':'not_started','first_started_at':None,
                  'completed_at':None,'updated_at':None}
            visible=status in (None,'not_started')
            return {'items':[item] if visible and page==1 else [],'total':int(visible),'page':page,'page_size':page_size}
    if status:
        query=query.where(derived==status)
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    items=[dict(row) for row in db.execute(query.order_by(LearningProgress.updated_at.desc(),LearningProgress.resource_id.desc())
                                          .offset((page-1)*page_size).limit(page_size)).mappings()]
    return {'items':items,'total':total,'page':page,'page_size':page_size}


def favorites_page(db,user_id,page,page_size):
    return paginate(db,select(Favorite).where(Favorite.user_id==user_id)
                    .order_by(Favorite.created_at.desc(),Favorite.resource_id.desc()),page,page_size)


def events_page(db,user_id,page,page_size,resource_id,event_type,is_effective):
    query=select(LearningEvent).where(LearningEvent.user_id==user_id)
    if resource_id is not None:query=query.where(LearningEvent.resource_id==resource_id)
    if event_type is not None:query=query.where(LearningEvent.event_type==event_type.lower())
    if is_effective is not None:query=query.where(LearningEvent.is_effective==is_effective)
    return paginate(db,query.order_by(LearningEvent.occurred_at.desc(),LearningEvent.id.desc()),page,page_size)
