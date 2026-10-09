"""
Job API endpoints.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.job import JobCreate, JobResponse
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
