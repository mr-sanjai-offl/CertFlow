import logging
import uuid

from celery import shared_task

from app.db.models.enums import JobStatus
from app.db.models.job import GenerationJob
from app.db.models.recipient import CertificateRecipient
from app.db.session import SessionLocal
from app.services.recipient_processor import process_recipient
from app.services.storage import LocalStorageService

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="process_generation_job", max_retries=3)
def process_generation_job(self, job_id: str):
    """
    Celery task to process an entire GenerationJob.

    1. Loads the job from DB.
    2. Processes each recipient sequentially.
    3. Updates final success/failure counters and job status.
    """
    logger.info(f"Starting processing for job {job_id}")

    # We must open our own DB session in the background task
    db = SessionLocal()
    storage_service = LocalStorageService()

    try:
        job_uuid = uuid.UUID(job_id)
        job = db.query(GenerationJob).filter_by(id=job_uuid).first()

        if not job:
            logger.error(f"Job {job_id} not found.")
            return

        # Skip if terminal
        if job.status in [JobStatus.COMPLETED, JobStatus.COMPLETED_WITH_ERRORS, JobStatus.FAILED]:
            logger.info(f"Job {job_id} is already in terminal state {job.status}. Skipping.")
            return

        # Mark job as processing
        job.status = JobStatus.PROCESSING
        db.commit()

        recipients = (
            db.query(CertificateRecipient)
            .filter_by(job_id=job.id)
            .order_by(CertificateRecipient.id)
            .all()
        )

        success_count = 0
        failed_count = 0

        for recipient in recipients:
            is_success = process_recipient(db, job, recipient.id, storage_service)
            if is_success:
                success_count += 1
            else:
                failed_count += 1

        # Recalculate and set final status
        # Since we lock the job conceptually (only one worker processes a job at a time),
        # we can safely update counters here. For higher concurrency, we'd use UPDATE table SET success_count = success_count + 1.
        job.success_count = success_count
        job.failed_count = failed_count

        if failed_count == 0 and success_count > 0:
            job.status = JobStatus.COMPLETED
        elif success_count == 0 and failed_count > 0:
            job.status = JobStatus.FAILED
        else:
            job.status = JobStatus.COMPLETED_WITH_ERRORS

        db.commit()
        logger.info(
            f"Job {job_id} finished with status {job.status}. Success: {success_count}, Failed: {failed_count}"
        )

    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error processing job {job_id}: {e}")

        # We only retry for expected transient errors or general exceptions
        retries = getattr(self.request, "retries", 0)

        from celery.exceptions import Retry

        try:
            self.retry(exc=e, countdown=2**retries)
        except Retry:
            raise
        except self.MaxRetriesExceededError:
            # Mark job as failed only if retries are exhausted
            try:
                job_uuid = uuid.UUID(job_id)
                job = db.query(GenerationJob).filter_by(id=job_uuid).first()
                if job:
                    job.status = JobStatus.FAILED
                    db.commit()
            except Exception:
                db.rollback()
            raise

    finally:
        db.close()
