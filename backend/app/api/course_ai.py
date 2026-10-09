from uuid import UUID
from fastapi import APIRouter, Depends, Request, Response, Path, Query, HTTPException
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from app.api.users import current_user
from app.api.ai_assistant import execute_question, settings
from app.database.session import get_db
from app.schemas.course_ai import CourseQuestion, CourseRecord, CourseHistory
from app.services import course_ai_records

router = APIRouter(prefix='/api/resources/{course_id}/ai', tags=['course-ai'])


@router.post('/questions', response_model=CourseRecord)
async def ask(payload: CourseQuestion, request: Request, response: Response,
              course_id: int=Path(ge=1, le=18446744073709551615), user=Depends(current_user), db: Session=Depends(get_db)):
    record = await execute_question(payload.existing_question(course_id), request, response, user, db,
                                    {'chapter_id':payload.chapter_id})
    return await run_in_threadpool(course_ai_records.read, request.app.state.session_factory, user.id,
                                  course_id, record.request_uuid, settings())


@router.get('/questions/{request_uuid}', response_model=CourseRecord)
def read(request_uuid: UUID, request: Request, response: Response, course_id: int=Path(ge=1,le=18446744073709551615), user=Depends(current_user)):
    result = course_ai_records.read(request.app.state.session_factory, user.id, course_id, str(request_uuid), settings())
    response.status_code = 202 if result.status=='pending' else 200
    return result


@router.get('/history', response_model=CourseHistory)
def history(request: Request, course_id: int=Path(ge=1,le=18446744073709551615), page: int=Query(1,ge=1), page_size: int=Query(20,ge=1,le=50), user=Depends(current_user)):
    if set(request.query_params)-{'page','page_size'}:
        raise HTTPException(422, 'Unexpected history parameter')
    return course_ai_records.history(request.app.state.session_factory, user.id, course_id, page, page_size, settings())
