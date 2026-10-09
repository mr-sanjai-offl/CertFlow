"""
Integration tests for the Job API.
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.enums import JobStatus, RecipientStatus
from app.db.models.job import GenerationJob
from app.db.models.recipient import CertificateRecipient

VALID_PAYLOAD = {
    "event": {"name": "Test Event", "organization": "Test Org", "date": "2026-10-08"},
    "recipients": [
        {"name": "Alice", "email": "alice@example.com"},
        {"name": "Bob", "email": "bob@example.com"},
    ],
}


def test_create_job_success(client: TestClient, db_session: Session):
    """Test successful job creation returns 202 Accepted and persists data."""
    response = client.post("/api/v1/jobs", json=VALID_PAYLOAD)
    assert response.status_code == 202

    data = response.json()
    assert "id" in data
    assert data["status"] == "QUEUED"
    assert data["total_count"] == 2

    job_id = uuid.UUID(data["id"])

    # Verify database persistence
    job = db_session.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    assert job is not None
    assert job.status == JobStatus.QUEUED
    assert job.total_count == 2
    assert job.success_count == 0
    assert job.failed_count == 0

    # Verify recipients persistence
    recipients = (
        db_session.query(CertificateRecipient).filter(CertificateRecipient.job_id == job_id).all()
    )
    assert len(recipients) == 2
    assert all(r.status == RecipientStatus.PENDING for r in recipients)


def test_create_job_validation_error(client: TestClient):
    """Test request validation fails gracefully on bad input."""
    bad_payload = {
        "event": {"name": "Test Event", "organization": "Test Org", "date": "not-a-date"},
        "recipients": [],
    }
    response = client.post("/api/v1/jobs", json=bad_payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    # Check that it caught both the date error and the empty list error
    assert any("date" in err["loc"] for err in errors)
    assert any("recipients" in err["loc"] for err in errors)


def test_create_job_idempotency(client: TestClient, db_session: Session):
    """Test idempotency key prevents duplicate jobs and returns existing job."""
    headers = {"Idempotency-Key": "my-unique-key-123"}

    # First request
    response1 = client.post("/api/v1/jobs", json=VALID_PAYLOAD, headers=headers)
    assert response1.status_code == 202
    job1_id = response1.json()["id"]

    # Second request with identical key
    response2 = client.post("/api/v1/jobs", json=VALID_PAYLOAD, headers=headers)
    assert response2.status_code == 202
    job2_id = response2.json()["id"]

    # The IDs must be identical
    assert job1_id == job2_id

    # Verify only one job exists in DB with this key
    jobs = (
        db_session.query(GenerationJob)
        .filter(GenerationJob.idempotency_key == "my-unique-key-123")
        .all()
    )
    assert len(jobs) == 1

    # Verify we only have 2 recipients total for this key, not 4
    recipients = (
        db_session.query(CertificateRecipient)
        .filter(CertificateRecipient.job_id == uuid.UUID(job1_id))
        .all()
    )
    assert len(recipients) == 2


def test_create_job_different_idempotency_keys(client: TestClient):
    """Test different idempotency keys create distinct jobs."""
    response1 = client.post(
        "/api/v1/jobs", json=VALID_PAYLOAD, headers={"Idempotency-Key": "key-A"}
    )
    response2 = client.post(
        "/api/v1/jobs", json=VALID_PAYLOAD, headers={"Idempotency-Key": "key-B"}
    )

    assert response1.status_code == 202
    assert response2.status_code == 202
    assert response1.json()["id"] != response2.json()["id"]


def test_create_job_without_idempotency_key(client: TestClient):
    """Test creating jobs without an idempotency key creates distinct jobs."""
    response1 = client.post("/api/v1/jobs", json=VALID_PAYLOAD)
    response2 = client.post("/api/v1/jobs", json=VALID_PAYLOAD)

    assert response1.status_code == 202
    assert response2.status_code == 202
    assert response1.json()["id"] != response2.json()["id"]
