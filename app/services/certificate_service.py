import hashlib
import os
from typing import Any

from app.db.models.job import GenerationJob
from app.db.models.recipient import CertificateRecipient
from app.services.certificate_generator import CertificateGenerationError, generate_certificate_pdf
from app.services.storage import LocalStorageService, StorageError


def generate_and_store_certificate(
    job: GenerationJob, recipient: CertificateRecipient, storage_service: LocalStorageService
) -> dict[str, Any]:
    """
    Coordinates the generation and storage of a certificate for a single recipient.

    1. Generates the PDF to a temporary location.
    2. Calculates necessary file metadata (size, checksum).
    3. Moves the PDF to permanent storage via the provided storage service.
    4. Returns a dictionary of metadata suitable for constructing a Certificate DB record.

    This function explicitly DOES NOT interact with the database. This boundary ensures
    that the caller (e.g., a Celery background task) retains full control over the
    database session and transaction lifecycle.

    Raises:
        CertificateGenerationError: If the PDF rendering fails.
        StorageError: If the final artifact cannot be stored.
    """
    temp_pdf_path = None
    try:
        # Step 1: Generate PDF locally in a temp directory
        temp_pdf_path = generate_certificate_pdf(job, recipient)

        # Step 2: Calculate metadata before storage handover
        # (Useful if the storage service eventually uploads to S3, we won't need to download it to hash it)
        file_size = os.path.getsize(temp_pdf_path)

        sha256_hash = hashlib.sha256()
        with open(temp_pdf_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        checksum = sha256_hash.hexdigest()

        # Step 3: Store permanently
        # The storage service moves the file, effectively consuming/cleaning up the temp file
        storage_path = storage_service.save_artifact(temp_pdf_path)

        # Clean client-friendly file name (e.g. Sanjai_S_Certificate.pdf)
        safe_name = "".join([c if c.isalnum() else "_" for c in recipient.name])

        # Return metadata as a dict
        return {
            "recipient_id": recipient.id,
            "file_name": f"{safe_name}_Certificate.pdf",
            "storage_path": storage_path,
            "file_size": file_size,
            "checksum": checksum,
        }

    except (CertificateGenerationError, StorageError):
        # We catch and re-raise purely to ensure the finally block cleans up
        raise
    finally:
        # Fallback cleanup just in case the storage step failed or didn't consume the temp file
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
            except OSError:
                pass  # Best effort cleanup
