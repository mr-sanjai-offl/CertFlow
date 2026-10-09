import datetime
import os
import uuid

from app.db.models.job import GenerationJob
from app.db.models.recipient import CertificateRecipient
from app.services.certificate_service import generate_and_store_certificate
from app.services.storage import LocalStorageService


def test_generate_and_store_certificate_success(tmp_path):
    """Test the coordination between generating a PDF and storing it."""
    # Setup storage
    storage_dir = tmp_path / "storage"
    storage_service = LocalStorageService(storage_dir=storage_dir)

    # Setup data
    job_id = uuid.uuid4()
    job = GenerationJob(
        id=job_id,
        event_name="Integration Test Event",
        event_organization="Org",
        event_date=datetime.date(2026, 10, 8),
    )
    recipient = CertificateRecipient(
        id=uuid.uuid4(), job_id=job_id, name="Sanjai S", email="sanjai@example.com"
    )

    # Execute service
    metadata = generate_and_store_certificate(job, recipient, storage_service)

    # Assert metadata returned is correct
    assert metadata["recipient_id"] == recipient.id
    assert metadata["file_name"] == "Sanjai_S_Certificate.pdf"
    assert "storage_path" in metadata
    assert metadata["storage_path"].endswith(".pdf")
    assert metadata["file_size"] > 0
    assert len(metadata["checksum"]) == 64  # SHA256 length

    # Verify file actually exists in final storage
    final_path = storage_dir / metadata["storage_path"]
    assert final_path.exists()
    assert os.path.getsize(final_path) == metadata["file_size"]

    # Verify temp files don't pollute the tmp_path base directory
    pdf_temp_files = list(tmp_path.glob("cert_*.pdf"))
    assert len(pdf_temp_files) == 0
