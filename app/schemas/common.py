"""
Common schemas reused across the API.
"""

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    """Specific details about an API error."""

    code: str = Field(..., description="A consistent string code representing the error type.")
    message: str = Field(..., description="A human-readable error description.")
    request_id: str | None = Field(None, description="Optional request ID for tracking.")


class ErrorResponse(BaseModel):
    """Standardized error response structure."""

    error: ErrorDetail

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "The provided email address is invalid.",
                    "request_id": "req-12345",
                }
            }
        }
    )
