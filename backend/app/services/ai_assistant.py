import hashlib
import json
import re
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from threading import RLock
from fastapi import HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from app.models.ai_qa import AIQARecord
from app.models import Resource, AICourseContext
from app.schemas.ai_assistant import Record
from app.services.agnes import AgnesProvider, PROMPT_VERSION
from app.services.course_presentation import HIDDEN_LEARNER_RESOURCE_IDS

provider = AgnesProvider()
reservation_lock = RLock()  # Supported deployment: exactly one application worker.


def now():
    value = datetime.now(timezone.utc).replace(tzinfo=None)
    return value.replace(microsecond=value.microsecond//1000*1000)


def fingerprint(payload, course_options=None):
    values = [payload.question, payload.mode, payload.resource_id, payload.consent_version]
    if course_options is not None:
        values += ['course-assistant-v1', course_options.get('chapter_id')]
    return hashlib.sha256(json.dumps(values, ensure_ascii=False, separators=(',',':')).encode()).hexdigest()


def public(db, row, settings):
    hidden = False
    if row.resource_id is not None:
        resource = db.get(Resource, row.resource_id)
        hidden = resource is None or resource.status != 'published' or row.resource_id in HIDDEN_LEARNER_RESOURCE_IDS or not settings.allows_resource(row.resource_id)
    course_context = db.get(AICourseContext, row.id) if row.mode == 'resource' else None
    if course_context:
        hidden = hidden or row.resource_id in HIDDEN_LEARNER_RESOURCE_IDS
    result = Record.model_validate({**{k:getattr(row,k) for k in Record.model_fields if k!='source'},
                                   'source':'资源片段（非完整检索）' if row.mode=='resource' else '通用模型回答，无本站资源依据'})
    if course_context:
        from app.services.course_ai_retrieval import FALLBACK
        result.source = '课程资料增强回答' if course_context.references else FALLBACK
    if hidden:
        result.question = '资源已不可用，关联问答已隐藏'
        result.answer = None
        result.error_code = 'resource_unavailable'
    return result


def owned(db, identity, request_uuid):
    row = db.scalar(select(AIQARecord).where(AIQARecord.request_uuid==request_uuid))
    if row is None or row.user_id != identity or row.created_at < now()-timedelta(days=30):
        raise HTTPException(404, 'Question unavailable')
    return row


def recover(db):
    stamp = now()
    db.execute(update(AIQARecord).where(AIQARecord.status=='pending', AIQARecord.created_at < stamp-timedelta(seconds=120))
               .values(status='unknown', error_code='process_interrupted', finished_at=stamp))


def reserve(factory, identity, payload, settings, course_options=None):
    with reservation_lock, factory() as db:
        recover(db)
        uuid = str(payload.request_uuid)
        previous = db.scalar(select(AIQARecord).where(AIQARecord.request_uuid==uuid))
        if previous:
            if previous.user_id != identity:
                db.commit()
                raise HTTPException(404, 'Question unavailable')
            if previous.request_fingerprint != fingerprint(payload, course_options):
                db.commit()
                raise HTTPException(409, 'Request UUID semantic conflict')
            result = public(db, previous, settings)
            db.commit()
            return result, None, False
        if not settings.ready:
            raise HTTPException(503, 'AI provider is not configured')
        if re.search(r'(?i)(?:bearer\s+\S+|(?:api[_-]?key|password|密码)\s*[:=]\s*\S+|-----BEGIN .*PRIVATE KEY)', payload.question):
            raise HTTPException(422, 'Remove credentials before sending')
        context = None
        version = None
        metadata = None
        if payload.mode == 'resource':
            resource = db.get(Resource, payload.resource_id)
            if resource is None or resource.status != 'published' or resource.id in HIDDEN_LEARNER_RESOURCE_IDS or not settings.allows_resource(resource.id):
                raise HTTPException(404, 'Resource is not approved for AI processing')
            version = resource.version_no
            if course_options is None:
                context = resource.title[:200]+'\n'+(resource.content or resource.summary)[:6000]
            else:
                from app.services.course_ai_retrieval import build
                context, metadata = build(db, payload, course_options, settings)
        stamp = now()
        midnight = stamp.replace(hour=0, minute=0, second=0, microsecond=0)
        query = select(func.count()).select_from(AIQARecord).where(AIQARecord.created_at>=midnight)
        reset_in=max(1,int((midnight+timedelta(days=1)-stamp).total_seconds())+1)
        if db.scalar(query)>=settings.global_limit:
            raise HTTPException(429, 'Daily AI request limit reached',headers={'X-AI-Limit-Source':'global_daily','Retry-After':str(reset_in)})
        if db.scalar(query.where(AIQARecord.user_id==identity))>=settings.user_limit:
            raise HTTPException(429, 'Daily AI request limit reached',headers={'X-AI-Limit-Source':'user_daily','Retry-After':str(reset_in)})
        if db.scalar(select(func.count()).select_from(AIQARecord).where(AIQARecord.status=='pending'))>=settings.concurrency:
            raise HTTPException(429, 'AI is busy; try later',headers={'X-AI-Limit-Source':'concurrency','Retry-After':'5'})
        row = AIQARecord(request_uuid=uuid, user_id=identity, mode=payload.mode, resource_id=payload.resource_id,
                         resource_version=version, request_fingerprint=fingerprint(payload, course_options), question=payload.question,
                         status='pending', provider='agnes', model=settings.model, prompt_version=PROMPT_VERSION,
                         consent_version=payload.consent_version, created_at=stamp)
        db.add(row)
        try:
            if metadata is not None:
                db.flush()
                db.add(AICourseContext(qa_record_id=row.id, created_at=stamp, **metadata))
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = owned(db, identity, uuid)
            if existing.request_fingerprint != fingerprint(payload, course_options):
                raise HTTPException(409, 'Request UUID semantic conflict') from None
            return public(db, existing, settings), None, False
        return public(db, row, settings), context, True


def finish(factory, identity, uuid, settings, answer, error, latency):
    with factory() as db:
        row = owned(db, identity, uuid)
        if row.status != 'pending':
            return public(db, row, settings)
        row.finished_at = now()
        row.latency_ms = latency
        if error:
            row.status = 'unknown' if error.uncertain else 'failed'
            row.error_code = error.code
        else:
            row.status = 'succeeded'
            row.error_code = ('answer_truncated' if answer.truncated else
                              'provider_output_limited' if answer.output_limited else
                              'answer_format_incomplete' if answer.format_incomplete else None)
            row.answer = answer.text
            row.provider_request_id = answer.request_id
            row.input_tokens, row.output_tokens = answer.input_tokens, answer.output_tokens
        db.commit()
        summary = error.summary if error else answer.summary
        if summary is not None:
            # Sidecar metadata, linked to the persisted record; no provider body.
            try:
                path = Path(__file__).resolve().parents[3] / 'outputs' / 'ai-provider-response-summaries.jsonl'
                with reservation_lock:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with path.open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps({'request_uuid': str(uuid), 'status': row.status,
                                                 'error_code': row.error_code, 'summary': summary})+'\n')
            except OSError:
                logging.getLogger(__name__).warning('AI response summary write failed')
        return public(db, row, settings)


def read_record(factory, identity, uuid, settings):
    with reservation_lock, factory() as db:
        recover(db)
        result = public(db, owned(db, identity, uuid), settings)
        db.commit()
        return result


def history(factory, identity, page, page_size, settings):
    with reservation_lock, factory() as db:
        recover(db)
        query = select(AIQARecord).where(AIQARecord.user_id==identity, AIQARecord.created_at>=now()-timedelta(days=30))
        total = db.scalar(select(func.count()).select_from(query.subquery()))
        rows = db.scalars(query.order_by(AIQARecord.created_at.desc(),AIQARecord.id.desc()).offset((page-1)*page_size).limit(page_size))
        result = {'items':[public(db,row,settings) for row in rows], 'total':total, 'page':page, 'page_size':page_size}
        db.commit()
        return result
