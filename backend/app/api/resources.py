from typing import Literal
from fastapi import APIRouter, Depends, Path, Query, HTTPException
from sqlalchemy.orm import Session

from app.api.users import current_user, require_admin
from app.database.session import get_db
from app.models import User
from app.schemas.resources import ResourceWrite, ResourceStatus, ResourceDetail, ResourceList, ResourceType, CATEGORIES
from app.services import resources as service

router=APIRouter(prefix='/api/resources',tags=['resources'])


@router.post('',response_model=ResourceDetail,status_code=201)
def create(payload: ResourceWrite,user: User=Depends(require_admin),db: Session=Depends(get_db)):
    return service.create_resource(db,user,payload)


@router.get('',response_model=ResourceList)
def listing(page: int=Query(1,ge=1),page_size: int=Query(20,ge=1,le=100),
            q: str | None=Query(None,min_length=1,max_length=200),
            category_code: str | None=Query(None,max_length=40),
            resource_type: ResourceType | None=None,
            status: Literal['draft','published','offline','all'] | None=None,
            user: User=Depends(current_user),db: Session=Depends(get_db)):
    if category_code is not None and category_code not in CATEGORIES:
        raise HTTPException(422,'Unsupported category')
    return service.list_resources(db,user,page,page_size,q,category_code,resource_type,status)


@router.get('/{id}',response_model=ResourceDetail)
def detail(id: int=Path(ge=1,le=18446744073709551615),user: User=Depends(current_user),db: Session=Depends(get_db)):
    return service.detail_resource(db,user,id)


@router.put('/{id}',response_model=ResourceDetail)
def replace(payload: ResourceWrite,id: int=Path(ge=1,le=18446744073709551615),
            user: User=Depends(require_admin),db: Session=Depends(get_db)):
    return service.replace_resource(db,user,id,payload)


@router.patch('/{id}/status',response_model=ResourceDetail)
def status(payload: ResourceStatus,id: int=Path(ge=1,le=18446744073709551615),
           user: User=Depends(require_admin),db: Session=Depends(get_db)):
    return service.change_status(db,user,id,payload.status)
