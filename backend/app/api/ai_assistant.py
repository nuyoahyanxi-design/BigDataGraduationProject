import asyncio
from time import monotonic
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from app.api.users import current_user
from app.database.session import get_db
from app.core.ai_config import AISettings
from app.schemas.ai_assistant import Question, Record, History, CONSENT_VERSION
from app.services import ai_assistant as service
from app.services.agnes import ProviderError
from app.services import ai_diagnostics

router = APIRouter(prefix='/api/ai', tags=['ai-assistant'])


def settings():
    try:
        value = AISettings.from_environment()
    except RuntimeError:
        raise HTTPException(503, 'AI configuration unavailable') from None
    if not value.enabled:
        raise HTTPException(503, 'AI assistant is disabled')
    return value


@router.get('/capabilities')
def capabilities(user=Depends(current_user)):
    try:
        value = AISettings.from_environment()
        return {'enabled':value.enabled, 'ready':value.ready, 'max_question_chars':2000,
                'consent_version':CONSENT_VERSION, 'notice':'问题及所选资源片段将发送至Agnes AI，请勿提交密码或个人敏感信息。'}
    except RuntimeError:
        return {'enabled':False, 'ready':False, 'max_question_chars':2000, 'consent_version':CONSENT_VERSION,
                'notice':'AI配置暂不可用，现有学习功能不受影响。'}


@router.post('/questions', response_model=Record)
async def ask(payload: Question, request: Request, response: Response, user=Depends(current_user), db: Session=Depends(get_db)):
    return await execute_question(payload, request, response, user, db)


async def execute_question(payload, request, response, user, db, course_options=None):
    value = settings()
    identity = user.id
    mode='course' if course_options is not None else 'general' if payload.mode=='general' else 'resource'
    ai_diagnostics.log('request_enter',identity,mode)
    db.close()  # Release the authentication read transaction before any external await.
    factory = request.app.state.session_factory
    try:
        record, context, is_new = await run_in_threadpool(service.reserve, factory, identity, payload, value, course_options)
    except HTTPException as problem:
        if problem.status_code==429:
            ai_diagnostics.log('rate_limit_rejected',identity,mode,(problem.headers or {}).get('X-AI-Limit-Source'),429)
        raise
    if not is_new:
        ai_diagnostics.log('request_replay',identity,mode,http_status=202 if record.status=='pending' else 200)
        response.status_code = 202 if record.status=='pending' else 200
        return record
    started = monotonic()
    answer = error = None
    try:
        answer = await service.provider.answer(value, payload.question, context)
        if course_options is not None and context is None:
            from dataclasses import replace
            from app.services.course_ai_retrieval import FALLBACK
            from app.services.agnes import MAX_ANSWER_CHARS, complete_fenced_text
            text = FALLBACK+'\n\n'+answer.text
            complete, incomplete = complete_fenced_text(text[:MAX_ANSWER_CHARS])
            answer = replace(answer, text=complete, truncated=answer.truncated or len(text)>MAX_ANSWER_CHARS,
                             format_incomplete=answer.format_incomplete or incomplete)
    except ProviderError as problem:
        error = problem
    except asyncio.CancelledError:
        # No second provider request. Recovery marks abandoned pending rows unknown.
        raise
    except Exception:
        error = ProviderError('provider_unexpected', 502, True)
    result = await run_in_threadpool(service.finish, factory, identity, record.request_uuid, value,
                                    answer, error, int((monotonic()-started)*1000))
    if error:
        response.status_code = error.http_status
        if error.code=='provider_rate_limit':response.headers['X-AI-Limit-Source']='provider_rate_limit'
    ai_diagnostics.log('provider_result',identity,mode,error.code if error else 'provider_success',
                       (error.summary or {}).get('http_status') if error else (answer.summary or {}).get('http_status'),
                       int((monotonic()-started)*1000))
    return result


@router.get('/questions/{request_uuid}', response_model=Record)
def question(request_uuid: UUID, request: Request, response: Response, user=Depends(current_user)):
    result = service.read_record(request.app.state.session_factory, user.id, str(request_uuid), settings())
    response.status_code = 202 if result.status=='pending' else 200
    return result


@router.get('/history', response_model=History)
def history(request: Request, page: int=Query(1,ge=1), page_size: int=Query(20,ge=1,le=50), user=Depends(current_user)):
    if set(request.query_params)-{'page','page_size'}:
        raise HTTPException(422, 'Unexpected history parameter')
    return service.history(request.app.state.session_factory, user.id, page, page_size, settings())
