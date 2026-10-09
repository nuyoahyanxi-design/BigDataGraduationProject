from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.api.users import require_admin
from app.database.session import get_db
from app.models import User
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard import overview
router = APIRouter(prefix='/api/dashboard',tags=['dashboard'])

@router.get('/overview',response_model=DashboardResponse)
def dashboard(request: Request,user: User=Depends(require_admin),db: Session=Depends(get_db)):
    if request.query_params: raise HTTPException(422,'Unsupported query parameter')
    return overview(db)
