import os
import tempfile
from pathlib import Path

from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from app.db.models.job import GenerationJob
from app.db.models.recipient import CertificateRecipient


class CertificateGenerationError(Exception):
    """Exception raised when PDF generation fails."""

    pass


def generate_certificate_pdf(job: GenerationJob, recipient: CertificateRecipient) -> Path:
    """
    Generates a PDF certificate for the given recipient and job.

    Uses ReportLab to draw a clean, professional landscape certificate.

    Returns:
        Path to the generated temporary PDF file. The caller is responsible for
        moving it to permanent storage or cleaning it up.
    """
    if recipient.job_id != job.id:
        raise CertificateGenerationError("Recipient does not belong to the given job.")

    # We use a temporary file to avoid leaving partial files in permanent storage.
    # The file is securely created by the OS in the system temp directory.
    fd, temp_path = tempfile.mkstemp(suffix=".pdf", prefix=f"cert_{recipient.id}_")
    os.close(fd)

    try:
        # Create a landscape PDF canvas
        c = canvas.Canvas(temp_path, pagesize=landscape(letter))
        width, height = landscape(letter)

        # Title
        c.setFont("Helvetica-Bold", 36)
        c.drawCentredString(width / 2.0, height - 2 * inch, "Certificate of Achievement")

        # Statement
        c.setFont("Helvetica", 18)
        c.drawCentredString(width / 2.0, height - 3 * inch, "This is proudly presented to")

        # Recipient Name
        c.setFont("Helvetica-Bold", 32)
        c.drawCentredString(width / 2.0, height - 4.5 * inch, str(recipient.name))

        # Event Statement
        c.setFont("Helvetica", 18)
        c.drawCentredString(width / 2.0, height - 5.5 * inch, "for successful participation in")

        # Event Name
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(width / 2.0, height - 6.2 * inch, str(job.event_name))

        # Organization and Date
        c.setFont("Helvetica", 14)
        date_str = job.event_date.strftime("%B %d, %Y") if job.event_date else "Unknown Date"
        footer_text = f"Issued by {job.event_organization} on {date_str}"
        c.drawCentredString(width / 2.0, 1.5 * inch, footer_text)

        c.showPage()
        c.save()

        # Verify it actually has content
        if os.path.getsize(temp_path) == 0:
            raise CertificateGenerationError("Generated PDF is empty.")

        return Path(temp_path)

    except Exception as e:
        # Clean up temp file on failure before raising
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise CertificateGenerationError(f"Failed to generate PDF: {e}") from e
