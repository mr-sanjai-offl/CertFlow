import datetime
import uuid

from app.db.models.certificate import Certificate
from app.db.models.enums import JobStatus, RecipientStatus
from app.db.models.job import GenerationJob
from app.db.models.recipient import CertificateRecipient


def test_download_certificate_success(client, db_session, tmp_path, monkeypatch):
    # Setup mock job and recipient
    job_id = uuid.uuid4()
    job = GenerationJob(
        id=job_id,
        status=JobStatus.COMPLETED,
        event_name="Test Event",
        event_organization="Test Org",
        event_date=datetime.date(2026, 1, 1),
        total_count=1,
        success_count=1,
        failed_count=0,
    )
    recipient = CertificateRecipient(
        id=uuid.uuid4(),
        job_id=job_id,
        name="John Doe",
        email="john@example.com",
        status=RecipientStatus.SUCCESS,
    )

    cert_id = uuid.uuid4()
    cert = Certificate(
        id=cert_id,
        recipient_id=recipient.id,
        file_name="John_Doe_Certificate.pdf",
        storage_path="mock-file.pdf",
        file_size=12,
    )

    db_session.add(job)
    db_session.add(recipient)
    db_session.add(cert)
    db_session.commit()

    # Mock storage service using monkeypatch
    class MockStorage:
        def __init__(self, *args, **kwargs):
            pass

        def open_artifact(self, relative_path):
            if relative_path == "mock-file.pdf":

                def file_iterator():
                    yield b"mock pdf content"

                return file_iterator()
            from app.services.storage import StorageError

            raise StorageError("Not found")

    monkeypatch.setattr("app.api.v1.certificates.LocalStorageService", MockStorage)

    response = client.get(f"/api/v1/certificates/{cert_id}/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert f"certificate-{cert_id}.pdf" in response.headers["content-disposition"]
    assert response.content == b"mock pdf content"


def test_download_certificate_not_found(client):
    response = client.get(f"/api/v1/certificates/{uuid.uuid4()}/download")
    assert response.status_code == 404
    assert response.json()["detail"] == "Certificate not found"


def test_download_certificate_missing_artifact(client, db_session, monkeypatch):
    job_id = uuid.uuid4()
    job = GenerationJob(
        id=job_id,
        status=JobStatus.COMPLETED,
        event_name="Test Event",
        event_organization="Test Org",
        event_date=datetime.date(2026, 1, 1),
        total_count=1,
        success_count=1,
        failed_count=0,
    )
    recipient = CertificateRecipient(
        id=uuid.uuid4(),
        job_id=job_id,
        name="John Doe",
        email="john@example.com",
        status=RecipientStatus.SUCCESS,
    )

    cert_id = uuid.uuid4()
    cert = Certificate(
        id=cert_id,
        recipient_id=recipient.id,
        file_name="John_Doe_Certificate.pdf",
        storage_path="missing-file.pdf",
        file_size=12,
    )

    db_session.add(job)
    db_session.add(recipient)
    db_session.add(cert)
    db_session.commit()

    # Mock storage service to raise StorageError
    class MockStorage:
        def __init__(self, *args, **kwargs):
            pass

        def open_artifact(self, relative_path):
            from app.services.storage import StorageError

            raise StorageError("Not found")

    monkeypatch.setattr("app.api.v1.certificates.LocalStorageService", MockStorage)

    response = client.get(f"/api/v1/certificates/{cert_id}/download")
    assert response.status_code == 404
    assert response.json()["detail"] == "Certificate artifact not found"
