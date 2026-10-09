"""
Shared test fixtures for CertFlow.

This module provides:
  - A FastAPI test client (no real database or Redis needed for basic tests)
  - Overrides for the get_db dependency (will be extended in Phase 2+)

Design decision:
  For Phase 1, the test client connects to the real FastAPI app but
  does NOT require a running PostgreSQL or Redis instance for basic
  tests (like the health liveness check).

  Integration tests that need a real database will get their own
  fixtures in later phases. Those will either:
    - Use a separate PostgreSQL test database
    - Use SQLite for simple unit-level tests where compatible

  This separation is documented in the README.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.models  # Ensure all models are registered on Base
from app.db.models.base import Base
from app.main import create_app

# Use an in-memory SQLite database for unit tests
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables in the test database once per session."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def mock_celery_dispatch():
    """Mock Celery task dispatch to avoid requiring Redis during normal tests."""
    with patch("app.workers.tasks.process_generation_job.delay") as mock_delay:
        yield mock_delay


@pytest.fixture
def db_session():
    """Yield a database session for a single test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def app(db_session):
    """Create a fresh FastAPI application for each test."""
    application = create_app()

    def override_get_db():
        yield db_session

    from app.db.session import get_db
    from app.core.security import get_api_key

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_api_key] = lambda: "test-secret-key"
    return application


@pytest.fixture
def client(app):
    """Provide a TestClient connected to the test application."""
    with TestClient(app) as c:
        yield c
