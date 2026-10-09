from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.api.users import current_user
from app.database.session import get_db
from app.models import User
from app.schemas.recommendations import Algorithm, RecommendationsResponse
from app.services.recommendations import recommendations_for_user

router = APIRouter(prefix='/api/recommendations', tags=['recommendations'])


@router.get('/me', response_model=RecommendationsResponse)
def me(request: Request, algorithm: Algorithm = 'content_v1',
       user: User = Depends(current_user), db: Session = Depends(get_db)):
    if set(request.query_params) - {'algorithm'}:
        raise HTTPException(422, 'Unsupported query parameter')
    return recommendations_for_user(db, user, algorithm)
