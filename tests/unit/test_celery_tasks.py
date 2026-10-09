import datetime
import uuid
from unittest.mock import MagicMock, patch

from app.db.models.enums import JobStatus
from app.db.models.job import GenerationJob
from app.db.models.recipient import CertificateRecipient
from app.workers.tasks import process_generation_job


# Note: We patch SessionLocal because the Celery task creates its own DB session
# using SessionLocal(). We want it to use our test db_session.
@patch("app.workers.tasks.process_generation_job.retry")
@patch("app.workers.tasks.SessionLocal")
@patch("app.workers.tasks.LocalStorageService")
@patch("app.workers.tasks.process_recipient")
def test_task_processes_all_recipients_success(
    mock_process, mock_storage, mock_session_local, mock_retry, db_session
):
    """Test job transitions to COMPLETED when all recipients succeed."""
    mock_db = MagicMock(wraps=db_session)
    mock_db.close.return_value = None
    mock_session_local.return_value = mock_db
    mock_process.return_value = True  # All succeed

    job_id = uuid.uuid4()
    job = GenerationJob(
        id=job_id,
        status=JobStatus.QUEUED,
        event_name="Event",
        event_organization="Org",
        event_date=datetime.date(2026, 1, 1),
    )
    rec1 = CertificateRecipient(id=uuid.uuid4(), job_id=job_id, name="A", email="a@a.com")
    rec2 = CertificateRecipient(id=uuid.uuid4(), job_id=job_id, name="B", email="b@b.com")
    db_session.add_all([job, rec1, rec2])
    db_session.commit()

    # Run the task directly (synchronously)
    process_generation_job(str(job_id))

    db_session.refresh(job)
    assert job.status == JobStatus.COMPLETED
    assert job.success_count == 2
    assert job.failed_count == 0
    assert mock_process.call_count == 2


@patch("app.workers.tasks.process_generation_job.retry")
@patch("app.workers.tasks.SessionLocal")
@patch("app.workers.tasks.LocalStorageService")
@patch("app.workers.tasks.process_recipient")
def test_task_processes_all_recipients_failed(
    mock_process, mock_storage, mock_session_local, mock_retry, db_session
):
    """Test job transitions to FAILED when all recipients fail."""
    mock_db = MagicMock(wraps=db_session)
    mock_db.close.return_value = None
    mock_session_local.return_value = mock_db
    mock_process.return_value = False  # All fail

    job_id = uuid.uuid4()
    job = GenerationJob(
        id=job_id,
        status=JobStatus.QUEUED,
        event_name="Event",
        event_organization="Org",
        event_date=datetime.date(2026, 1, 1),
    )
    rec1 = CertificateRecipient(id=uuid.uuid4(), job_id=job_id, name="A", email="a@a.com")
    db_session.add_all([job, rec1])
    db_session.commit()

    process_generation_job(str(job_id))

    db_session.refresh(job)
    assert job.status == JobStatus.FAILED
    assert job.success_count == 0
    assert job.failed_count == 1


@patch("app.workers.tasks.process_generation_job.retry")
@patch("app.workers.tasks.SessionLocal")
@patch("app.workers.tasks.LocalStorageService")
@patch("app.workers.tasks.process_recipient")
def test_task_processes_mixed_outcomes(
    mock_process, mock_storage, mock_session_local, mock_retry, db_session
):
    """Test job transitions to COMPLETED_WITH_ERRORS on mixed outcomes."""
    mock_db = MagicMock(wraps=db_session)
    mock_db.close.return_value = None
    mock_session_local.return_value = mock_db
    mock_process.side_effect = [True, False]  # First succeeds, second fails

    job_id = uuid.uuid4()
    job = GenerationJob(
        id=job_id,
        status=JobStatus.QUEUED,
        event_name="Event",
        event_organization="Org",
        event_date=datetime.date(2026, 1, 1),
    )
    rec1 = CertificateRecipient(id=uuid.uuid4(), job_id=job_id, name="A", email="a@a.com")
    rec2 = CertificateRecipient(id=uuid.uuid4(), job_id=job_id, name="B", email="b@b.com")
    db_session.add_all([job, rec1, rec2])
    db_session.commit()

    process_generation_job(str(job_id))

    db_session.refresh(job)
    assert job.status == JobStatus.COMPLETED_WITH_ERRORS
    assert job.success_count == 1
    assert job.failed_count == 1
