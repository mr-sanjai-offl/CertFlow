import logging

from sqlalchemy.orm import Session

from app.db.models.certificate import Certificate
from app.db.models.enums import RecipientStatus
from app.db.models.job import GenerationJob
from app.db.models.recipient import CertificateRecipient
from app.services.certificate_service import generate_and_store_certificate
from app.services.storage import LocalStorageService

logger = logging.getLogger(__name__)


def process_recipient(
    db: Session, job: GenerationJob, recipient_id: str, storage_service: LocalStorageService
) -> bool:
    """
    Processes a single recipient: generates the PDF, saves it, and updates DB records.

    Returns:
        bool: True if processing was successful or already completed successfully, False otherwise.
    """
    recipient = db.query(CertificateRecipient).filter_by(id=recipient_id).first()

    if not recipient:
        logger.warning(f"Recipient {recipient_id} not found in database.")
        return False

    if recipient.job_id != job.id:
        logger.warning(f"Recipient {recipient_id} does not belong to job {job.id}.")
        return False

    if recipient.status == RecipientStatus.SUCCESS:
        logger.info(f"Recipient {recipient_id} already successfully processed. Skipping.")
        return True

    # Mark as processing
    recipient.status = RecipientStatus.PROCESSING
    recipient.attempt_count += 1
    db.commit()

    try:
        # Generate and store PDF
        # This returns a dict with keys: recipient_id, file_name, storage_path, file_size, checksum
        metadata = generate_and_store_certificate(job, recipient, storage_service)

        # Create Certificate record
        cert = Certificate(
            recipient_id=recipient.id,
            file_name=metadata["file_name"],
            storage_path=metadata["storage_path"],
            file_size=metadata["file_size"],
            checksum=metadata.get("checksum"),
        )
        db.add(cert)

        # Mark recipient as success
        recipient.status = RecipientStatus.SUCCESS
        recipient.error_code = None
        recipient.error_message = None

        db.commit()
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to process recipient {recipient_id}: {e}")

        # We catch exceptions locally and update the DB so one failure doesn't crash the whole job.
        # In a real app, we'd distinguish between permanent (invalid data) and transient (storage down).
        recipient.status = RecipientStatus.FAILED
        recipient.error_code = "GENERATION_ERROR"
        recipient.error_message = str(e)[:1000]  # Safe truncation
        db.commit()
        return False
