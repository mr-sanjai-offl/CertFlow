"""
Tests for health check endpoints.

These verify that:
  1. GET /health returns 200 with {"status": "healthy"} — always,
     regardless of database or Redis connectivity.
  2. GET /health/ready checks dependencies and returns appropriate status.
"""


class TestHealthEndpoint:
    """Tests for the liveness probe."""

    def test_health_returns_200(self, client):
        """The liveness endpoint should always return 200 if the process is running."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_body(self, client):
        """The response body should contain status: healthy."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"


class TestReadinessEndpoint:
    """Tests for the readiness probe.

    Note: In Phase 1, the readiness endpoint will likely return 503
    because PostgreSQL and Redis are not running during unit tests.
    This is expected and correct — the readiness check is doing its job
    by reporting that dependencies are unavailable.
    """

    def test_readiness_returns_json(self, client):
        """The readiness endpoint should return a JSON response."""
        response = client.get("/health/ready")
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "redis" in data

    def test_readiness_unavailable_without_deps(self, client, monkeypatch):
        """Without running DB/Redis, readiness should report not_ready."""

        # Mock the database check to fail
        def mock_execute(*args, **kwargs):
            raise Exception("DB Down")

        # We need to mock the Session's execute method for this request
        from sqlalchemy.orm import Session

        monkeypatch.setattr(Session, "execute", mock_execute)

        response = client.get("/health/ready")
        # When deps are down, we expect 503
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
