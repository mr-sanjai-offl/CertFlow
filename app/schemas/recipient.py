"""
Recipient schemas for API request validation and response serialization.
"""

import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.db.models.enums import RecipientStatus


class RecipientCreate(BaseModel):
    """
    Input schema for a single recipient.

    Validation Rules:
      - name: Required, max length 100, strips whitespace, must not be empty.
      - email: Required, valid email format, max length 255.
    """

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)] = (
        Field(..., description="Full name of the recipient to appear on the certificate.")
    )

    email: EmailStr = Field(
        ..., max_length=255, description="Valid email address of the recipient."
    )


class RecipientResponse(BaseModel):
    """
    Output schema for a single recipient.
    """

    id: uuid.UUID = Field(..., description="Unique identifier for the recipient.")
    job_id: uuid.UUID = Field(..., description="ID of the job this recipient belongs to.")
    name: str = Field(..., description="Recipient's name.")
    email: str = Field(..., description="Recipient's email address.")

    status: RecipientStatus = Field(..., description="Current processing status.")
    attempt_count: int = Field(..., description="Number of processing attempts made.")

    error_code: str | None = Field(None, description="Error code if processing failed.")
    error_message: str | None = Field(
        None, description="Detailed error message if processing failed."
    )

    # We expose the certificate ID if one exists, but not the whole nested object
    # to keep the recipient list response lean.
    certificate_id: uuid.UUID | None = Field(
        None, description="ID of the generated certificate, if successful."
    )

    model_config = ConfigDict(from_attributes=True)
