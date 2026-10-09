from fastapi import HTTPException
from sqlalchemy import select, func
from pydantic import ValidationError

from app.models import Resource, User
from app.services.users import utc_now
from app.services.course_presentation import visible_resource_clause
from app.schemas.resources import ResourceWrite


def lock_admin(db,user):
    current=db.scalar(select(User).where(User.id==user.id).with_for_update().execution_options(populate_existing=True))
    if current is None or current.status!='active':
        raise HTTPException(401,'Authentication required')
    if current.role!='admin':
        raise HTTPException(403,'Administrator role required')


def check_publication(values):
    if not values['tags'] or not ((values.get('content') or '').strip() or values.get('content_url')):
        raise HTTPException(422,'Published resource requires tags and content or URL')


def bump(resource):
    if resource.version_no>=4294967295:
        raise HTTPException(409,'Resource version limit reached')
    resource.version_no+=1
    resource.updated_at=utc_now()


def locked_resource(db,id):
    resource=db.scalar(select(Resource).where(Resource.id==id).with_for_update())
    if resource is None or resource.status=='deleted':
        raise HTTPException(404,'Resource not found')
    return resource


def create_resource(db,user,payload):
    lock_admin(db,user)
    stamp=utc_now()
    resource=Resource(**payload.model_dump(),status='draft',version_no=1,created_by=user.id,
                      published_at=None,created_at=stamp,updated_at=stamp)
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


def replace_resource(db,user,id,payload):
    lock_admin(db,user)
    resource=locked_resource(db,id)
    values=payload.model_dump()
    if resource.status=='published':
        check_publication(values)
    if any(getattr(resource,key)!=value for key,value in values.items()):
        bump(resource)
        for key,value in values.items():
            setattr(resource,key,value)
    db.commit()
    db.refresh(resource)
    return resource


def change_status(db,user,id,status):
    lock_admin(db,user)
    resource=locked_resource(db,id)
    if resource.status==status:
        db.commit()
        db.refresh(resource)
        return resource
    if (resource.status,status) not in {('draft','published'),('published','offline'),('offline','published')}:
        raise HTTPException(409,'Invalid resource status transition')
    if status=='published':
        try:
            ResourceWrite.model_validate({key:getattr(resource,key) for key in ResourceWrite.model_fields})
        except ValidationError:
            raise HTTPException(422,'Resource metadata is invalid for publication') from None
        check_publication({'tags':resource.tags,'content':resource.content,'content_url':resource.content_url})
        if resource.published_at is None:
            resource.published_at=utc_now()
    bump(resource)
    resource.status=status
    db.commit()
    db.refresh(resource)
    return resource


def detail_resource(db,user,id):
    query=select(Resource).where(Resource.id==id,Resource.status!='deleted')
    if user.role!='admin':
        query=query.where(Resource.status=='published', visible_resource_clause())
    resource=db.scalar(query)
    if resource is None:
        raise HTTPException(404,'Resource not found')
    return resource


def list_resources(db,user,page,page_size,q,category_code,resource_type,status):
    if user.role!='admin' and status not in (None,'published'):
        raise HTTPException(403,'Administrator role required for unpublished resources')
    query=select(Resource).where(Resource.status!='deleted')
    if user.role!='admin':
        query=query.where(visible_resource_clause())
    if status!='all':
        query=query.where(Resource.status==(status or 'published'))
    if q:
        query=query.where(Resource.title.contains(q,autoescape=True))
    if category_code:
        query=query.where(Resource.category_code==category_code)
    if resource_type:
        query=query.where(Resource.resource_type==resource_type)
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    items=db.scalars(query.order_by(Resource.id.desc()).offset((page-1)*page_size).limit(page_size)).all()
    return {'items':items,'total':total,'page':page,'page_size':page_size}
