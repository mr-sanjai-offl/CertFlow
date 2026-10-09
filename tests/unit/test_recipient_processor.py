import datetime
import uuid
from unittest.mock import patch

import pytest

from app.db.models.certificate import Certificate
from app.db.models.enums import RecipientStatus
from app.db.models.job import GenerationJob
from app.db.models.recipient import CertificateRecipient
from app.services.recipient_processor import process_recipient
from app.services.storage import LocalStorageService


@pytest.fixture
def test_data(db_session):
    job_id = uuid.uuid4()
    job = GenerationJob(
        id=job_id,
        event_name="Test Event",
        event_organization="Org",
        event_date=datetime.date(2026, 1, 1),
    )
    recipient = CertificateRecipient(
        id=uuid.uuid4(),
        job_id=job_id,
        name="Alex",
        email="alex@example.com",
    )
    db_session.add_all([job, recipient])
    db_session.commit()
    return job, recipient


def test_process_recipient_success(db_session, tmp_path, test_data):
    """Test successful recipient processing generates and stores certificate."""
    job, recipient = test_data
    storage_service = LocalStorageService(storage_dir=tmp_path / "storage")

    result = process_recipient(db_session, job, recipient.id, storage_service)

    assert result is True

    db_session.refresh(recipient)
    assert recipient.status == RecipientStatus.SUCCESS
    assert recipient.attempt_count == 1

    cert = db_session.query(Certificate).filter_by(recipient_id=recipient.id).first()
    assert cert is not None
    assert cert.file_name == "Alex_Certificate.pdf"
    assert cert.file_size > 0


def test_process_recipient_already_success(db_session, tmp_path, test_data):
    """Test processing a recipient that is already SUCCESS skips generation."""
    job, recipient = test_data
    recipient.status = RecipientStatus.SUCCESS
    db_session.commit()

    storage_service = LocalStorageService(storage_dir=tmp_path / "storage")

    with patch("app.services.recipient_processor.generate_and_store_certificate") as mock_generate:
        result = process_recipient(db_session, job, recipient.id, storage_service)

    assert result is True
    assert mock_generate.call_count == 0


def test_process_recipient_generation_failure(db_session, tmp_path, test_data):
    """Test handling generation failure updates recipient to FAILED."""
    job, recipient = test_data
    storage_service = LocalStorageService(storage_dir=tmp_path / "storage")

    with patch(
        "app.services.recipient_processor.generate_and_store_certificate",
        side_effect=Exception("Render error"),
    ):
        result = process_recipient(db_session, job, recipient.id, storage_service)

    assert result is False

    db_session.refresh(recipient)
    assert recipient.status == RecipientStatus.FAILED
    assert recipient.error_code == "GENERATION_ERROR"
    assert "Render error" in recipient.error_message
