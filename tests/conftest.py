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

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def app():
    """Create a fresh FastAPI application for each test."""
    return create_app()


@pytest.fixture
def client(app):
    """Provide a TestClient connected to the test application.

    TestClient uses HTTPX under the hood and allows making HTTP requests
    to the FastAPI app without starting a real server.
    """
    with TestClient(app) as c:
        yield c
