from fastapi import HTTPException
from sqlalchemy import select, func
from app.models import AIQARecord, AICourseContext, Resource
from app.services import ai_assistant as shared
from app.schemas.course_ai import CourseRecord


def result(db, row, metadata, settings):
    record = shared.public(db, row, settings)
    hidden = record.error_code == 'resource_unavailable'
    return CourseRecord(**record.model_dump(), course_id=row.resource_id,
                        course_title=None if hidden else metadata.course_title,
                        references=[] if hidden else [{k: v for k, v in ref.items() if k != 'fragment_hash'} for ref in metadata.references],
                        retrieval_version=metadata.retrieval_version)


def read(factory, identity, course_id, uuid, settings):
    with shared.reservation_lock, factory() as db:
        shared.recover(db)
        row = shared.owned(db, identity, uuid)
        metadata = db.get(AICourseContext, row.id)
        if row.resource_id != course_id or metadata is None:
            raise HTTPException(404, 'Course question unavailable')
        output = result(db, row, metadata, settings)
        db.commit()
        return output


def history(factory, identity, course_id, page, page_size, settings):
    from datetime import timedelta
    with shared.reservation_lock, factory() as db:
        shared.recover(db)
        from app.services.course_presentation import HIDDEN_LEARNER_RESOURCE_IDS
        resource = db.get(Resource, course_id)
        if resource is None or resource.status != 'published' or course_id in HIDDEN_LEARNER_RESOURCE_IDS or not settings.allows_resource(course_id):
            raise HTTPException(404, 'Course is not approved for AI processing')
        query = select(AIQARecord, AICourseContext).join(AICourseContext, AIQARecord.id==AICourseContext.qa_record_id).where(
            AIQARecord.user_id==identity, AIQARecord.resource_id==course_id, AIQARecord.created_at>=shared.now()-timedelta(days=30))
        total = db.scalar(select(func.count()).select_from(query.subquery()))
        rows = db.execute(query.order_by(AIQARecord.created_at.desc(), AIQARecord.id.desc()).offset((page-1)*page_size).limit(page_size)).all()
        output = {'items':[result(db, row, meta, settings) for row, meta in rows], 'total':total,'page':page,'page_size':page_size}
        db.commit()
        return output
