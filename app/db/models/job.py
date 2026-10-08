"""
GenerationJob model representing a bulk certificate-generation request.

What is it?
  A record of a single request to generate one or more certificates.

Why do we need it?
  To track the overall progress of a bulk request, provide a single identifier
  for the client to poll, and ensure idempotency (prevent duplicate jobs).

What real-world object does it represent?
  A single API request or a batch task (e.g., "Generate 50 certificates for Python Bootcamp").

How does it relate to other models?
  A 1-to-many relationship with CertificateRecipient. One job has many recipients.

Why are these fields nullable/non-nullable?
  - started_at / completed_at are nullable because a job is created before it starts or completes.
  - idempotency_key is nullable because idempotency might be optional for some clients, or only enforced when provided. (Here we make it unique and nullable).
  - Counters are non-nullable with a default of 0 because they are strictly numeric metrics.

Why is this field indexed?
  - status: Indexed because we might query "find all QUEUED jobs" for a recovery worker.
  - created_at: Indexed to allow efficient sorting and time-based filtering (e.g., "show recent jobs").

Why is this constraint necessary?
  - idempotency_key has a unique constraint so that two identical requests from a client (e.g., due to a network retry) don't spawn two massive bulk generation tasks.

What happens if the relationship is deleted?
  - If a job is deleted, its recipients and certificates should logically be deleted. We configure SQLAlchemy's `cascade="all, delete-orphan"` so deleting a job cascades down.

How would I modify the model if the requirement changes?
  - If we needed jobs to belong to specific users/organizations, we'd add a `user_id` foreign key here, linking to a User model, and index it for efficient retrieval.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin
from app.db.models.enums import JobStatus

if TYPE_CHECKING:
    from app.db.models.recipient import CertificateRecipient


class GenerationJob(Base, TimestampMixin):
    __tablename__ = "generation_jobs"

    # Primary key using UUID to prevent sequential ID guessing and allow distributed ID generation
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Status uses the explicit enum
    status: Mapped[JobStatus] = mapped_column(
        String(50), default=JobStatus.QUEUED, nullable=False, index=True
    )

    # Counters for efficient progress reporting
    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Lifecycle timestamps (created_at provided by TimestampMixin)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Idempotency key to prevent duplicate job creation
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )

    # Relationship to recipients
    # cascade="all, delete-orphan" ensures recipients are deleted if the job is deleted.
    recipients: Mapped[list["CertificateRecipient"]] = relationship(
        "CertificateRecipient",
        back_populates="job",
        cascade="all, delete-orphan",
    )

    # Additional indexes
    __table_args__ = (Index("ix_generation_jobs_created_at", "created_at"),)
