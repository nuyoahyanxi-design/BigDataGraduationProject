from fastapi import APIRouter, Depends, Path, Query, Request, Response
from sqlalchemy.orm import Session
from app.api.users import current_user, require_admin
from app.database.session import get_db
from app.models import User
from app.schemas.courses import ChapterWrite, ChapterAction
from app.services import courses

router=APIRouter(prefix='/api',tags=['courses'])

@router.get('/resources/{id}/course')
def course(id:int=Path(ge=1,le=18446744073709551615),user:User=Depends(current_user),db:Session=Depends(get_db)):
    return courses.read_course(db,id,user)

@router.post('/resources/{id}/chapters',status_code=201)
def create(payload:ChapterWrite,id:int=Path(ge=1,le=18446744073709551615),user:User=Depends(require_admin),db:Session=Depends(get_db)):
    return courses.create_chapter(db,id,user,payload)

@router.post('/resources/{id}/chapters/{chapter_id}/events')
def record(payload:ChapterAction,request:Request,id:int=Path(ge=1,le=18446744073709551615),
           chapter_id:int=Path(ge=1,le=18446744073709551615),user:User=Depends(current_user),db:Session=Depends(get_db)):
    return courses.act(db,user.id,id,chapter_id,payload,request.state.event_received_at)

@router.get('/users/me/chapter-events')
def history(page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100),user:User=Depends(current_user),db:Session=Depends(get_db)):
    return courses.events(db,user.id,page,page_size)


@router.put('/resources/{id}/chapters/{chapter_id}')
def update(payload:ChapterWrite,id:int=Path(ge=1,le=18446744073709551615),
           chapter_id:int=Path(ge=1,le=18446744073709551615),
           user:User=Depends(require_admin),db:Session=Depends(get_db)):
    return courses.maintain_chapter(db,id,chapter_id,user,payload)


@router.delete('/resources/{id}/chapters/{chapter_id}',status_code=204)
def remove(id:int=Path(ge=1,le=18446744073709551615),
           chapter_id:int=Path(ge=1,le=18446744073709551615),
           user:User=Depends(require_admin),db:Session=Depends(get_db)):
    courses.maintain_chapter(db,id,chapter_id,user)
    return Response(status_code=204)
