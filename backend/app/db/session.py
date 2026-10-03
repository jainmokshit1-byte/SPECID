"""Database engine and session factory (SQLAlchemy 2.0, psycopg 3)."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.settings import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )


def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def ping(engine: Engine) -> bool:
    """True when the database answers `SELECT 1`."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request. Routers commit after the service call;
    anything not committed is rolled back when the session closes."""
    with get_session_factory()() as session:
        yield session
