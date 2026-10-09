import datetime
from unittest.mock import patch

import pytest

from app.core.exceptions import DispatchError
from app.db.models.enums import JobStatus
from app.db.models.job import GenerationJob
from app.schemas.job import EventInfo, JobCreate, RecipientCreate
from app.services.job_service import create_job

VALID_PAYLOAD = JobCreate(
    event=EventInfo(
        name="Dispatch Test Event",
        organization="Test Org",
        date=datetime.date(2026, 10, 8),
    ),
    recipients=[RecipientCreate(name="Alice", email="alice@example.com")],
)


def test_dispatch_called_on_success(db_session, mock_celery_dispatch):
    """Test that dispatch is called after successful commit."""
    job = create_job(db=db_session, job_in=VALID_PAYLOAD)

    # Verify the job exists in the DB
    assert job.id is not None

    # Verify dispatch was called
    mock_celery_dispatch.assert_called_once_with(str(job.id))


def test_dispatch_failure_raises_error_but_keeps_job(db_session):
    """Test that if Redis is down, DispatchError is raised but the job stays in the DB."""
    with patch(
        "app.workers.tasks.process_generation_job.delay", side_effect=Exception("Redis down")
    ):
        with pytest.raises(DispatchError, match="failed to queue"):
            create_job(db=db_session, job_in=VALID_PAYLOAD)

    # The job should still be saved in the database
    job = db_session.query(GenerationJob).first()
    assert job is not None
    assert job.status == JobStatus.QUEUED


def test_dispatch_called_on_idempotent_retry_if_queued(db_session, mock_celery_dispatch):
    """Test that if a request is retried and the job is still QUEUED, it dispatches again."""
    idempotency_key = "test-idem-key"

    # First request
    job1 = create_job(db=db_session, job_in=VALID_PAYLOAD, idempotency_key=idempotency_key)
    assert mock_celery_dispatch.call_count == 1

    # Second request (retry)
    job2 = create_job(db=db_session, job_in=VALID_PAYLOAD, idempotency_key=idempotency_key)

    assert job1.id == job2.id
    assert mock_celery_dispatch.call_count == 2


def test_dispatch_skipped_on_idempotent_retry_if_processing(db_session, mock_celery_dispatch):
    """Test that if a request is retried and the job is already PROCESSING, it skips dispatch."""
    idempotency_key = "test-idem-key-2"

    # First request
    job1 = create_job(db=db_session, job_in=VALID_PAYLOAD, idempotency_key=idempotency_key)
    assert mock_celery_dispatch.call_count == 1

    # Manually mark as processing
    job1.status = JobStatus.PROCESSING
    db_session.commit()

    # Second request
    job2 = create_job(db=db_session, job_in=VALID_PAYLOAD, idempotency_key=idempotency_key)

    assert job1.id == job2.id
    # Call count should STILL be 1 because it skipped dispatch
    assert mock_celery_dispatch.call_count == 1
