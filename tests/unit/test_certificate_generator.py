import datetime
import os
import uuid

import pytest
from pypdf import PdfReader

from app.db.models.job import GenerationJob
from app.db.models.recipient import CertificateRecipient
from app.services.certificate_generator import CertificateGenerationError, generate_certificate_pdf


def test_generate_pdf_success():
    """Test generating a standard PDF certificate."""
    job_id = uuid.uuid4()
    job = GenerationJob(
        id=job_id,
        event_name="Advanced Python Mastery",
        event_organization="PyTech Inc",
        event_date=datetime.date(2026, 12, 1),
    )

    recipient = CertificateRecipient(
        id=uuid.uuid4(), job_id=job_id, name="Alex Kumar", email="alex@example.com"
    )

    temp_pdf_path = None
    try:
        temp_pdf_path = generate_certificate_pdf(job, recipient)

        # Verify file exists and is not empty
        assert temp_pdf_path.exists()
        assert os.path.getsize(temp_pdf_path) > 0

        # Verify valid PDF and text extraction
        reader = PdfReader(str(temp_pdf_path))
        assert len(reader.pages) == 1

        page = reader.pages[0]
        text = page.extract_text()

        # Check that core content is present
        assert "Certificate of Achievement" in text
        assert "Alex Kumar" in text
        assert "Advanced Python Mastery" in text
        assert "PyTech Inc" in text
        assert "December 01, 2026" in text

        # Ensure email is NOT rendered on the PDF
        assert "alex@example.com" not in text

    finally:
        # Cleanup
        if temp_pdf_path and temp_pdf_path.exists():
            os.remove(temp_pdf_path)


def test_generate_pdf_recipient_mismatch():
    """Test generating a PDF when the recipient does not belong to the job."""
    job = GenerationJob(id=uuid.uuid4())
    recipient = CertificateRecipient(
        job_id=uuid.uuid4(),  # Different ID
        name="Bob",
        email="bob@example.com",
    )

    with pytest.raises(CertificateGenerationError, match="does not belong to the given job"):
        generate_certificate_pdf(job, recipient)


def test_generate_pdf_long_names():
    """Test that extremely long names do not crash the PDF generator."""
    job_id = uuid.uuid4()
    job = GenerationJob(
        id=job_id,
        event_name="A" * 100,  # 100 characters
        event_organization="B" * 50,
        event_date=datetime.date(2026, 12, 1),
    )

    recipient = CertificateRecipient(
        id=uuid.uuid4(),
        job_id=job_id,
        name="Charlie " * 20,  # Very long name
        email="charlie@example.com",
    )

    temp_pdf_path = None
    try:
        temp_pdf_path = generate_certificate_pdf(job, recipient)
        assert temp_pdf_path.exists()

        reader = PdfReader(str(temp_pdf_path))
        text = reader.pages[0].extract_text()
        assert "Charlie Charlie" in text

    finally:
        if temp_pdf_path and temp_pdf_path.exists():
            os.remove(temp_pdf_path)
