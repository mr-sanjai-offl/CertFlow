"""
CertificateRecipient model representing one person/entity receiving a certificate.

What is it?
  A record of an individual inside a bulk generation job.

Why do we need it?
  To allow per-recipient failure isolation. If rendering fails for one person,
  it only updates this record to FAILED, while the rest of the job continues.
  It also tracks individual retry attempts.

What real-world object does it represent?
  A student taking a course, or an attendee at an event.

How does it relate to other models?
  - Belongs to a GenerationJob (many-to-1).
  - Has zero or one Certificate (1-to-1). A failed recipient has zero certificates.

Why are these fields nullable/non-nullable?
  - error_code / error_message: Nullable because successful recipients won't have errors.
  - name / email: Non-nullable as they are the core data needed to render a certificate (assuming email is a strict requirement; if email is optional, we'd make it nullable, but we'll assume non-nullable for this design).

Why is this field indexed?
  - job_id: Indexed because we frequently query "get all recipients for job X".
  - status: Indexed because the worker might query "get all PENDING recipients for job X".

Why is this constraint necessary?
  - We could add a unique constraint on (job_id, email) to prevent duplicate recipients in the same job, but this might block legitimate use cases (e.g., one person getting two different certificates in one batch). We omit it for flexibility, unless strict de-duplication is requested.

What happens if the relationship is deleted?
  - Deleting a recipient cascades to delete its associated Certificate artifact record.

How would I modify the model if the requirement changes?
  - If a recipient needs multiple certificates (e.g., for different modules in a course), the Certificate relationship would change from 1-to-1 (uselist=False) to 1-to-many.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin
from app.db.models.enums import RecipientStatus

if TYPE_CHECKING:
    from app.db.models.certificate import Certificate
    from app.db.models.job import GenerationJob


class CertificateRecipient(Base, TimestampMixin):
    __tablename__ = "certificate_recipients"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key linking to the GenerationJob
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("generation_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Recipient data
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)

    # Status uses the explicit enum
    status: Mapped[RecipientStatus] = mapped_column(
        String(50), default=RecipientStatus.PENDING, nullable=False, index=True
    )

    # Retry tracking
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Safe error information (no stack traces)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Lifecycle timestamps
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship back to Job
    job: Mapped["GenerationJob"] = relationship("GenerationJob", back_populates="recipients")

    # 1-to-1 relationship with Certificate
    # uselist=False enforces that a recipient has at most one certificate record.
    certificate: Mapped["Certificate | None"] = relationship(
        "Certificate",
        back_populates="recipient",
        uselist=False,
        cascade="all, delete-orphan",
    )
