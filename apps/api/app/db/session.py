"""PostgreSQL engine and session management.

A single engine is created for the process; ``SessionLocal`` is a factory bound
to it. ``get_session`` is a generator suitable for FastAPI dependency injection
and guarantees the session is closed after each request.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
    echo=settings.db_echo,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Yield a database session and ensure it is closed afterwards."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def check_connection() -> None:
    """Run a trivial query to verify the database is reachable."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
