"""
Certificate model representing a successfully generated PDF artifact.

What is it?
  Metadata about the final generated file on disk (or in cloud storage).

Why do we need it?
  To give the API a way to locate the physical file when a user requests a download,
  and to store file metadata (size, checksum) without reading the file from disk.

What real-world object does it represent?
  The actual PDF file.

How does it relate to other models?
  Belongs to a CertificateRecipient (1-to-1).

Why are these fields nullable/non-nullable?
  - All fields (file_name, storage_path, file_size) are non-nullable because this record
    is only created *after* successful generation. A partially generated file shouldn't have a record.
  - checksum is nullable in case calculating it is deferred or optional, though making it non-nullable adds integrity. We'll make it nullable for flexibility.

Why is this field indexed?
  - recipient_id: Indexed to quickly find the certificate for a specific recipient. (Though unique=True implicitly creates an index).

Why is this constraint necessary?
  - recipient_id has a unique constraint (enforcing the 1-to-1 relationship at the DB level). A recipient can only have one final certificate.

What happens if the relationship is deleted?
  - If the recipient is deleted, this record is cascade-deleted. Note: This only deletes the DB record; physical file cleanup would need to be handled by application logic or a background job.

How would I modify the model if the requirement changes?
  - If we switch from local disk storage to AWS S3, `storage_path` could be renamed to `s3_key` or `object_url`, and the underlying logic would fetch it from S3. The model structurally stays the same.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.recipient import CertificateRecipient


class Certificate(Base, TimestampMixin):
    __tablename__ = "certificates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key linking to the Recipient.
    # unique=True enforces the 1-to-1 relationship at the database level.
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("certificate_recipients.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # File metadata
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # Size in bytes
    checksum: Mapped[str | None] = mapped_column(String(255), nullable=True)  # e.g., SHA256 hash

    # Relationship back to Recipient
    recipient: Mapped["CertificateRecipient"] = relationship(
        "CertificateRecipient", back_populates="certificate"
    )
