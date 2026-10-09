from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.orm import Session

from app.api.users import current_user
from app.database.session import get_db
from app.models import User
from app.schemas.learning import BehaviorRequest, ViewRequest, EventReceipt, EventPage, ProgressPage, FavoritePage, EventType, ProgressStatus
from app.services.learning import record_behavior, progress_page, favorites_page, events_page

router=APIRouter(prefix='/api',tags=['learning'])


def perform(request,db,user,id,kind,payload):
    return record_behavior(db,user.id,id,kind,payload,request.state.event_received_at)


@router.post('/resources/{id}/view',response_model=EventReceipt)
def view(payload: ViewRequest,request: Request,id: int=Path(ge=1,le=18446744073709551615),user: User=Depends(current_user),db: Session=Depends(get_db)):
    return perform(request,db,user,id,'resource_view',payload)


@router.post('/resources/{id}/start',response_model=EventReceipt)
def start(payload: BehaviorRequest,request: Request,id: int=Path(ge=1,le=18446744073709551615),user: User=Depends(current_user),db: Session=Depends(get_db)):
    return perform(request,db,user,id,'learning_start',payload)


@router.post('/resources/{id}/complete',response_model=EventReceipt)
def complete(payload: BehaviorRequest,request: Request,id: int=Path(ge=1,le=18446744073709551615),user: User=Depends(current_user),db: Session=Depends(get_db)):
    return perform(request,db,user,id,'learning_complete',payload)


@router.post('/resources/{id}/favorite',response_model=EventReceipt)
def favorite(payload: BehaviorRequest,request: Request,id: int=Path(ge=1,le=18446744073709551615),user: User=Depends(current_user),db: Session=Depends(get_db)):
    return perform(request,db,user,id,'favorite_add',payload)


@router.delete('/resources/{id}/favorite',response_model=EventReceipt)
def unfavorite(payload: BehaviorRequest,request: Request,id: int=Path(ge=1,le=18446744073709551615),user: User=Depends(current_user),db: Session=Depends(get_db)):
    return perform(request,db,user,id,'favorite_remove',payload)


@router.get('/users/me/progress',response_model=ProgressPage)
def progress(page: int=Query(1,ge=1),page_size: int=Query(20,ge=1,le=100),
             resource_id: int | None=Query(None,ge=1,le=18446744073709551615),status: ProgressStatus | None=None,
             user: User=Depends(current_user),db: Session=Depends(get_db)):
    return progress_page(db,user.id,page,page_size,resource_id,status)


@router.get('/users/me/favorites',response_model=FavoritePage)
def favorites(page: int=Query(1,ge=1),page_size: int=Query(20,ge=1,le=100),user: User=Depends(current_user),db: Session=Depends(get_db)):
    return favorites_page(db,user.id,page,page_size)


@router.get('/users/me/events',response_model=EventPage)
def events(page: int=Query(1,ge=1),page_size: int=Query(20,ge=1,le=100),
           resource_id: int | None=Query(None,ge=1,le=18446744073709551615),event_type: EventType | None=None,
           is_effective: int | None=Query(None,ge=0,le=1),user: User=Depends(current_user),db: Session=Depends(get_db)):
    return events_page(db,user.id,page,page_size,resource_id,event_type,is_effective)
