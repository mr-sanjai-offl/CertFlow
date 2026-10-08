"""
Certificate metadata schemas.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CertificateResponse(BaseModel):
    """
    Output schema for certificate metadata.

    Note: We do not expose `storage_path` here because internal filesystem
    or cloud paths are an implementation detail. The client should use a dedicated
    download endpoint that returns the actual file.
    """

    id: uuid.UUID = Field(..., description="Unique identifier for the certificate artifact.")
    recipient_id: uuid.UUID = Field(
        ..., description="ID of the recipient who owns this certificate."
    )

    file_name: str = Field(..., description="Name of the generated PDF file.")
    file_size: int = Field(..., description="Size of the file in bytes.")
    checksum: str | None = Field(None, description="Optional SHA256 checksum of the file.")

    created_at: datetime = Field(..., description="Timestamp when the certificate was generated.")

    model_config = ConfigDict(from_attributes=True)
