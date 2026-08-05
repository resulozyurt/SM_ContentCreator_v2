"""
Database engine and session management.

The engine is built lazily from settings.database_url (Railway injects
DATABASE_URL), so importing this module never requires a configured database.
Use `session_scope()` for a transactional block that commits/rolls back
automatically, or `get_sessionmaker()` for a plain session factory.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def _resolve_url() -> str:
    url = get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not set. See .env.example.")
    # Normalize legacy / bare schemes to what SQLAlchemy + psycopg v3 expect.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


@lru_cache
def get_engine() -> Engine:
    """Return a cached engine, created on first use."""
    return create_engine(_resolve_url(), pool_pre_ping=True, future=True)


@lru_cache
def get_sessionmaker() -> sessionmaker:
    """Return a cached session factory bound to the engine."""
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope: commit on success, rollback on error."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
