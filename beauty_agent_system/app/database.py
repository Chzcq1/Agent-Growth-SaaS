from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine():
    """Lazily builds the engine so importing models/tests doesn't require
    NEON_DATABASE_URL to already be configured."""
    settings = get_settings()
    url = settings.neon_database_url or "sqlite:///./_unconfigured.db"
    return create_engine(url, pool_pre_ping=True, future=True)


@lru_cache
def get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
