"""
Service layer for GenerationJob operations.
"""

import logging
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import DatabaseError, DispatchError
from app.db.models.enums import JobStatus, RecipientStatus
from app.db.models.job import GenerationJob
from app.db.models.recipient import CertificateRecipient
from app.schemas.job import JobCreate
from app.workers.tasks import process_generation_job

logger = logging.getLogger(__name__)


def _dispatch_job(job_id: str) -> None:
    try:
        process_generation_job.delay(job_id)
        logger.info(f"Dispatched job {job_id} to Celery.")
    except Exception as e:
        logger.error(f"Failed to dispatch job {job_id} to Celery: {e}")
        raise DispatchError(
            f"Job {job_id} is created but failed to queue for background processing. Redis might be down."
        ) from e


def create_job(db: Session, job_in: JobCreate, idempotency_key: str | None = None) -> GenerationJob:
    """
    Persists a new bulk certificate-generation request and its recipients.

    If an idempotency_key is provided and already exists, returns the existing job.
    Uses a single database transaction to guarantee that either the job and ALL
    its recipients are created, or none are.
    """
    if idempotency_key:
        # Pre-check for idempotency to save work
        existing_job = (
            db.query(GenerationJob).filter(GenerationJob.idempotency_key == idempotency_key).first()
        )
        if existing_job:
            logger.info(
                f"Idempotency hit: Returning existing job {existing_job.id} for key {idempotency_key}"
            )
            if existing_job.status == JobStatus.QUEUED:
                _dispatch_job(str(existing_job.id))
            return existing_job

    # Start constructing the new job
    job_id = uuid.uuid4()
    total_recipients = len(job_in.recipients)

    new_job = GenerationJob(
        id=job_id,
        status=JobStatus.QUEUED,
        event_name=job_in.event.name,
        event_organization=job_in.event.organization,
        event_date=job_in.event.date,
        total_count=total_recipients,
        success_count=0,
        failed_count=0,
        idempotency_key=idempotency_key,
    )

    recipients = [
        CertificateRecipient(
            id=uuid.uuid4(),
            job_id=job_id,
            name=rec.name,
            email=rec.email,
            status=RecipientStatus.PENDING,
            attempt_count=0,
        )
        for rec in job_in.recipients
    ]

    new_job.recipients = recipients

    try:
        # We add the job. SQLAlchemy's cascade and relationship handles the recipients automatically.
        db.add(new_job)
        db.commit()
        db.refresh(new_job)
        logger.info(f"Created new GenerationJob {new_job.id} with {total_recipients} recipients")

        # Dispatch to celery after successful commit
        _dispatch_job(str(new_job.id))

        return new_job

    except IntegrityError as e:
        db.rollback()
        # This handles the race condition where another concurrent request
        # with the same idempotency key committed just before we did.
        if idempotency_key and "idempotency_key" in str(e).lower():
            logger.info(f"Concurrent idempotency resolution for key {idempotency_key}")
            existing_job = (
                db.query(GenerationJob)
                .filter(GenerationJob.idempotency_key == idempotency_key)
                .first()
            )
            if existing_job:
                if existing_job.status == JobStatus.QUEUED:
                    _dispatch_job(str(existing_job.id))
                return existing_job

        # If it's a different IntegrityError, wrap and raise it
        logger.error(f"Database integrity error during job creation: {str(e)}")
        raise DatabaseError("Database constraint violated during job creation.") from e

    except DispatchError:
        # Job is already committed; Redis is just down. Let the API layer return 503.
        raise

    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error during job creation: {str(e)}")
        raise DatabaseError("An unexpected error occurred while persisting the job.") from e
