from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.database.session import build_engine, build_session_factory
from app.core.security import AuthSettings
from app.core.media import build_video_files
from app.api.users import router
from app.api.resources import router as resources_router
from app.api.learning import router as learning_router
from app.api.recommendations import router as recommendations_router
from app.api.dashboard import router as dashboard_router
from app.api.admin import router as admin_router
from app.api.ai_assistant import router as ai_router
from app.api.courses import router as courses_router
from app.api.course_ai import router as course_ai_router
from app.services.learning import event_time


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.auth_settings = AuthSettings.from_environment()
    engine = build_engine(Settings.from_environment())
    def verify_connection():
        with engine.connect() as connection:
            connection.execute(text('SELECT 1'))
    try:
        try:
            await run_in_threadpool(verify_connection)
        except Exception:
            raise RuntimeError('Database startup check failed; verify configuration and service') from None
        app.state.engine = engine
        app.state.session_factory = build_session_factory(engine)
        yield
    finally:
        await run_in_threadpool(engine.dispose)


app = FastAPI(title='Spark Learning Backend', version='0.1.0', lifespan=lifespan)
app.include_router(router)
app.include_router(resources_router)
app.include_router(learning_router)
app.include_router(recommendations_router)
app.include_router(dashboard_router)
app.include_router(admin_router)
app.include_router(ai_router)
app.include_router(courses_router)
app.include_router(course_ai_router)
app.mount('/videos', build_video_files(), name='course-videos')


@app.middleware('http')
async def record_receive_time(request: Request, call_next):
    request.state.event_received_at = event_time()
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def safe_validation_error(_request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={'detail':[
        {'loc':list(e['loc']), 'type':e['type'], 'msg':'Invalid request value'}
        for e in exc.errors()]})


@app.exception_handler(SQLAlchemyError)
async def safe_database_error(_request: Request, _exc: SQLAlchemyError):
    return JSONResponse(status_code=503, content={'detail':'Database operation unavailable'})
