from sqlalchemy import URL, create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi import Request

from app.core.config import Settings


def build_engine(settings: Settings):
    url = URL.create('mysql+pymysql', username=settings.user, password=settings.password,
                     host=settings.host, port=settings.port, database=settings.database,
                     query={'charset': settings.charset})
    engine = create_engine(url, pool_pre_ping=True, pool_recycle=1800,
                           echo=False, hide_parameters=True,
                           connect_args={'connect_timeout': 5, 'read_timeout': 10,
                                         'write_timeout': 10})

    @event.listens_for(engine, 'connect')
    def set_utc(connection, _record):
        with connection.cursor() as cursor:
            cursor.execute("SET time_zone = '+00:00'")

    return engine


def build_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db(request: Request):
    """Future sync route dependency; no automatic commit."""
    with request.app.state.session_factory() as session:
        yield session
