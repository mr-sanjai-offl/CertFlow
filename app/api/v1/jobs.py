"""
Job API endpoints.
"""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.job import JobCreate, JobDetailResponse, JobProgress, JobResponse
from app.schemas.recipient import PaginatedRecipientResponse
from app.services import job_service

router = APIRouter(tags=["jobs"])
logger = logging.getLogger(__name__)


@router.post("", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_generation_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    """
    Create a new bulk certificate-generation job.

    This endpoint accepts a validated job payload and queues it for asynchronous processing.
    It returns a 202 Accepted status with the job ID and initial progress counters.

    If `Idempotency-Key` is provided in the headers, it will safely return an existing
    job if one was already queued with that exact key, preventing duplicate batch generation.
    """
    logger.info(f"Received request to create job with {len(payload.recipients)} recipients")
    job = job_service.create_job(db=db, job_in=payload, idempotency_key=idempotency_key)
    return job


@router.get("/{job_id}", response_model=JobDetailResponse)
def get_generation_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Retrieve details and status of a specific job.
    """
    job = job_service.get_job(db=db, job_id=str(job_id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.get("/{job_id}/progress", response_model=JobProgress)
def get_job_progress(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Retrieve real-time progress of a specific job based on recipient processing outcomes.
    """
    progress = job_service.get_job_progress(db=db, job_id=str(job_id))
    if not progress:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return progress


@router.get("/{job_id}/recipients", response_model=PaginatedRecipientResponse)
def list_job_recipients(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=1000, description="Max number of recipients to return"),
    offset: int = Query(0, ge=0, description="Number of recipients to skip"),
):
    """
    List recipients for a specific job with pagination.
    """
    items, total = job_service.get_job_recipients(db=db, job_id=str(job_id), limit=limit, offset=offset)
    if items is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return {"items": items, "total": total, "limit": limit, "offset": offset}
