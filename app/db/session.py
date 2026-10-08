"""
Database session management.

This module creates the SQLAlchemy engine and session factory.
It also provides the `get_db` dependency used by FastAPI route handlers
to get a database session that is automatically closed after each request.

Interview note:
  - The engine is created at module import time. This is fine because
    SQLAlchemy only opens actual connections when they're first used,
    not when create_engine() is called.
  - `pool_pre_ping=True` sends a lightweight query before reusing a
    pooled connection to detect stale/dropped connections.
  - In tests, we override the `get_db` dependency to use a test database.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Detect stale connections before using them
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: provides a database session per request.

    The session is opened when the dependency is resolved and closed
    in the finally block after the request completes, regardless of
    whether the request succeeded or raised an exception.

    Usage in a route:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
