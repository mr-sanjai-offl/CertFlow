"""
Unit tests for database models.

These tests verify the core persistence layer, including:
  - Model creation and default values
  - Enum validations
  - Relationships (1-to-many, 1-to-1)
  - Integrity constraints (e.g. uniqueness)
"""

import datetime
import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models.certificate import Certificate
from app.db.models.enums import JobStatus, RecipientStatus
from app.db.models.job import GenerationJob
from app.db.models.recipient import CertificateRecipient


class TestGenerationJob:
    def test_create_job(self, db_session):
        """A GenerationJob can be created with default values and progress counters."""
        job = GenerationJob(
            total_count=100,
            event_name="Test",
            event_organization="Org",
            event_date=datetime.date(2026, 10, 8)
        )
        db_session.add(job)
        db_session.commit()

        assert job.id is not None
        assert job.status == JobStatus.QUEUED
        assert job.total_count == 100
        assert job.success_count == 0
        assert job.failed_count == 0
        assert job.created_at is not None
        assert job.idempotency_key is None

    def test_idempotency_key_uniqueness(self, db_session):
        """Idempotency key must be unique across all jobs."""
        job1 = GenerationJob(
            idempotency_key="key-123",
            event_name="Test",
            event_organization="Org",
            event_date=datetime.date(2026, 10, 8)
        )
        db_session.add(job1)
        db_session.commit()

        job2 = GenerationJob(
            idempotency_key="key-123",
            event_name="Test2",
            event_organization="Org2",
            event_date=datetime.date(2026, 10, 8)
        )
        db_session.add(job2)

        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()


class TestCertificateRecipient:
    def test_recipient_belongs_to_job(self, db_session):
        """A Recipient can be added to a job, and the relationship is established."""
        job = GenerationJob(
            event_name="Test Event",
            event_organization="Test Org",
            event_date=datetime.date(2026, 10, 8)
        )
        db_session.add(job)
        db_session.commit()

        recipient1 = CertificateRecipient(
            job_id=job.id, name="Alice", email="alice@example.com", status=RecipientStatus.PENDING
        )
        recipient2 = CertificateRecipient(
            job_id=job.id, name="Bob", email="bob@example.com", status=RecipientStatus.PENDING
        )
        db_session.add_all([recipient1, recipient2])
        db_session.commit()

        # Test Job -> Recipients
        assert len(job.recipients) == 2

        # Test Recipient -> Job
        assert recipient1.job == job
        assert recipient2.job == job

    def test_recipient_failure_information(self, db_session):
        """Failure information (code and message) can be persisted."""
        job = GenerationJob(
            event_name="Test Event",
            event_organization="Test Org",
            event_date=datetime.date(2026, 10, 8)
        )
        db_session.add(job)
        db_session.commit()

        recipient = CertificateRecipient(
            job_id=job.id,
            name="Charlie",
            email="charlie@example.com",
            status=RecipientStatus.FAILED,
            error_code="RENDER_ERROR",
            error_message="Failed to render PDF template",
        )
        db_session.add(recipient)
        db_session.commit()

        assert recipient.error_code == "RENDER_ERROR"
        assert recipient.error_message == "Failed to render PDF template"


class TestCertificate:
    def test_certificate_belongs_to_recipient(self, db_session):
        """A Certificate belongs to a single Recipient."""
        job = GenerationJob(
            event_name="Test Event",
            event_organization="Test Org",
            event_date=datetime.date(2026, 10, 8)
        )
        db_session.add(job)
        db_session.commit()

        recipient = CertificateRecipient(
            job_id=job.id, name="Dave", email="dave@example.com", status=RecipientStatus.SUCCESS
        )
        db_session.add(recipient)
        db_session.commit()

        cert = Certificate(
            recipient_id=recipient.id,
            file_name="dave_cert.pdf",
            storage_path="/storage/dave_cert.pdf",
            file_size=1024,
            checksum="abc123hash",
        )
        db_session.add(cert)
        db_session.commit()

        # Test Recipient -> Certificate
        assert recipient.certificate == cert

        # Test Certificate -> Recipient
        assert cert.recipient == recipient

        # Test metadata
        assert cert.file_size == 1024
        assert cert.file_name == "dave_cert.pdf"

    def test_certificate_unique_recipient(self, db_session):
        """A Recipient can only have one Certificate (1-to-1 relationship enforced)."""
        job = GenerationJob(
            event_name="Test Event",
            event_organization="Test Org",
            event_date=datetime.date(2026, 10, 8)
        )
        db_session.add(job)
        db_session.commit()

        recipient = CertificateRecipient(job_id=job.id, name="Eve", email="eve@example.com")
        db_session.add(recipient)
        db_session.commit()

        cert1 = Certificate(
            recipient_id=recipient.id,
            file_name="eve1.pdf",
            storage_path="/storage/eve1.pdf",
            file_size=1024,
        )
        db_session.add(cert1)
        db_session.commit()

        cert2 = Certificate(
            recipient_id=recipient.id,
            file_name="eve2.pdf",
            storage_path="/storage/eve2.pdf",
            file_size=2048,
        )
        db_session.add(cert2)

        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()
