"""
Job schemas for bulk certificate generation.
"""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import get_settings
from app.db.models.enums import JobStatus
from app.schemas.recipient import RecipientCreate


class EventInfo(BaseModel):
    """
    Metadata about the event for which certificates are being generated.
    """

    name: str = Field(
        ..., min_length=1, max_length=200, description="Name of the event (e.g., Python Bootcamp)."
    )
    organization: str = Field(
        ..., min_length=1, max_length=200, description="Organization hosting the event."
    )
    date: datetime.date = Field(..., description="Official date of the event in YYYY-MM-DD format.")


class JobCreate(BaseModel):
    """
    Input schema for initiating a bulk generation job.
    """

    event: EventInfo = Field(..., description="Event details to embed in certificates.")

    # We enforce limits at the schema level to prevent massive payloads
    # taking down the server.
    recipients: list[RecipientCreate] = Field(
        ...,
        min_length=1,
        max_length=get_settings().MAX_RECIPIENTS_PER_JOB,
        description=f"List of recipients (max {get_settings().MAX_RECIPIENTS_PER_JOB}).",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event": {
                    "name": "Python Backend Workshop",
                    "organization": "Example Organization",
                    "date": "2026-10-08",
                },
                "recipients": [{"name": "Sanjai S", "email": "sanjai@example.com"}],
            }
        }
    )


class JobResponse(BaseModel):
    """
    Standard output schema for a job, representing its current state.
    """

    id: uuid.UUID = Field(..., description="Unique job identifier.")
    status: JobStatus = Field(..., description="Current processing status.")
    total_count: int = Field(..., description="Total number of recipients in this job.")

    model_config = ConfigDict(from_attributes=True)


class JobDetailResponse(JobResponse):
    """
    Detailed job response containing event info, counters, and timestamps.
    """

    event_name: str
    event_organization: str
    event_date: datetime.date
    success_count: int
    failed_count: int
    created_at: datetime.datetime
    updated_at: datetime.datetime | None = None
    completed_at: datetime.datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class JobProgress(BaseModel):
    """
    Dedicated progress schema, derived from job counters and recipient statuses.
    """

    job_id: uuid.UUID = Field(..., description="Unique job identifier.")
    status: JobStatus = Field(..., description="Current processing status.")
    total_count: int = Field(..., description="Total recipients.")
    success_count: int = Field(..., description="Successfully processed recipients.")
    failed_count: int = Field(..., description="Failed recipients.")
    pending_count: int = Field(..., description="Recipients waiting to be processed.")
    processing_count: int = Field(..., description="Recipients currently processing.")
    progress_percentage: float = Field(..., ge=0.0, le=100.0, description="Percentage completed.")
