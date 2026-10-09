from app.core.security import get_api_key


def test_missing_api_key(client, app, monkeypatch):
    # Remove the dependency override so the actual security logic runs
    app.dependency_overrides.pop(get_api_key, None)

    monkeypatch.setenv("API_KEY", "real-secret-key")
    import app.core.config

    app.core.config.get_settings.cache_clear()

    # Send request without header
    response = client.get("/api/v1/jobs/123e4567-e89b-12d3-a456-426614174000")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_invalid_api_key(client, app, monkeypatch):
    app.dependency_overrides.pop(get_api_key, None)

    # Ensure config has a known valid key
    monkeypatch.setenv("API_KEY", "real-secret-key")
    import app.core.config

    app.core.config.get_settings.cache_clear()

    response = client.get(
        "/api/v1/jobs/123e4567-e89b-12d3-a456-426614174000", headers={"X-API-Key": "wrong-key"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_valid_api_key(client, app, monkeypatch):
    app.dependency_overrides.pop(get_api_key, None)

    monkeypatch.setenv("API_KEY", "real-secret-key")
    import app.core.config

    app.core.config.get_settings.cache_clear()

    # Valid key (should return 404 because job doesn't exist, not 401)
    response = client.get(
        "/api/v1/jobs/123e4567-e89b-12d3-a456-426614174000",
        headers={"X-API-Key": "real-secret-key"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_missing_api_key_configuration(client, app, monkeypatch):
    app.dependency_overrides.pop(get_api_key, None)

    # Simulate missing environment variable
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("API_KEY", "")  # Just in case it defaults
    import app.core.config

    app.core.config.get_settings.cache_clear()

    response = client.get(
        "/api/v1/jobs/123e4567-e89b-12d3-a456-426614174000", headers={"X-API-Key": "some-key"}
    )

    # Should fail closed
    assert response.status_code == 500
    assert response.json()["detail"] == "API authentication is not properly configured."


def test_health_endpoints_unprotected(client, app):
    app.dependency_overrides.pop(get_api_key, None)

    response = client.get("/health")
    assert response.status_code == 200
