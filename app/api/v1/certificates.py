import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import certificate_service
from app.services.storage import LocalStorageService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["certificates"])


@router.get("/{certificate_id}/download")
def download_certificate(certificate_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Download a successfully generated PDF certificate by its ID.
    """
    storage_service = LocalStorageService()
    cert, stream = certificate_service.get_certificate_download_stream(
        db, str(certificate_id), storage_service
    )

    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")

    if not stream:
        # DB record exists but artifact does not
        logger.error(f"Artifact missing for certificate {certificate_id} at {cert.storage_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Certificate artifact not found"
        )

    filename = f"certificate-{cert.id}.pdf"

    return StreamingResponse(
        stream,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
