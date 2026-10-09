from typing import Literal
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy.orm import Session
from app.api.users import require_admin
from app.database.session import get_db
from app.schemas.admin import AdminUsers, BatchList, AdminCourses
from app.services import admin as service

router=APIRouter(prefix='/api/admin',tags=['admin'])


@router.get('/users',response_model=AdminUsers,dependencies=[Depends(require_admin)])
def users(request: Request,page: int=Query(1,ge=1),page_size: int=Query(20,ge=1,le=100),db: Session=Depends(get_db)):
    if set(request.query_params)-{'page','page_size'}: raise HTTPException(422,'Unsupported query parameter')
    return service.list_users(db,page,page_size)


@router.get('/batches',response_model=BatchList,dependencies=[Depends(require_admin)])
def batches(request: Request):
    if request.query_params: raise HTTPException(422,'Unsupported query parameter')
    return service.batches()


@router.get('/courses',response_model=AdminCourses,dependencies=[Depends(require_admin)])
def courses(request:Request,page:int=Query(1,ge=1),page_size:int=Query(10,ge=1,le=100),
            q:str|None=Query(None,min_length=1,max_length=200),
            status:Literal['draft','published','offline','all']='all',db:Session=Depends(get_db)):
    if set(request.query_params)-{'page','page_size','q','status'}:
        raise HTTPException(422,'Unsupported query parameter')
    return service.list_courses(db,page,page_size,q,status)
