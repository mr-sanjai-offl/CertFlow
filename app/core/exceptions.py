"""
Application exception classes and FastAPI exception handlers.

All custom exceptions are defined here. FastAPI exception handlers
convert these into consistent JSON error responses so that internal
Python exceptions are never exposed to API clients.

Interview note:
  If asked "how do you prevent stack traces from leaking to users?" —
  explain that every custom exception has an error_code and a safe
  message. The exception handlers below format them into the standard
  error response shape before returning to the client.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Custom exception classes
# ---------------------------------------------------------------------------


class CertFlowError(Exception):
    """Base exception for all CertFlow application errors.

    Every custom exception inherits from this so we can catch
    all application errors in one handler if needed.
    """

    def __init__(
        self,
        message: str = "An internal error occurred.",
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(CertFlowError):
    """Raised when a requested resource does not exist."""

    def __init__(
        self,
        message: str = "The requested resource was not found.",
        error_code: str = "NOT_FOUND",
    ) -> None:
        super().__init__(message=message, error_code=error_code, status_code=404)


class ValidationError(CertFlowError):
    """Raised for business-logic validation failures.

    This is separate from Pydantic's ValidationError (which handles
    request schema validation). This class handles things like
    "duplicate idempotency key" or "too many recipients".
    """

    def __init__(
        self,
        message: str = "Validation failed.",
        error_code: str = "VALIDATION_ERROR",
    ) -> None:
        super().__init__(message=message, error_code=error_code, status_code=400)


class ConflictError(CertFlowError):
    """Raised when an operation conflicts with existing state."""

    def __init__(
        self,
        message: str = "The request conflicts with existing data.",
        error_code: str = "CONFLICT",
    ) -> None:
        super().__init__(message=message, error_code=error_code, status_code=409)


class DatabaseError(CertFlowError):
    """Raised when a database operation fails unexpectedly."""

    def __init__(
        self,
        message: str = "A database error occurred.",
        error_code: str = "DATABASE_ERROR",
    ) -> None:
        super().__init__(message=message, error_code=error_code, status_code=500)


# ---------------------------------------------------------------------------
# Exception handlers — register these on the FastAPI app
# ---------------------------------------------------------------------------


def _build_error_response(
    status_code: int,
    error_code: str,
    message: str,
    request_id: str | None = None,
) -> JSONResponse:
    """Build a consistent JSON error response."""
    body: dict = {
        "error": {
            "code": error_code,
            "message": message,
        }
    }
    if request_id:
        body["error"]["request_id"] = request_id
    return JSONResponse(status_code=status_code, content=body)


async def certflow_error_handler(request: Request, exc: CertFlowError) -> JSONResponse:
    """Handle all CertFlowError subclasses."""
    request_id = request.headers.get("X-Request-ID")
    return _build_error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        request_id=request_id,
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions.

    Logs the real error server-side but returns a safe generic
    message to the client. Never exposes internal details.
    """
    import logging

    logger = logging.getLogger("certflow.errors")
    logger.exception("Unhandled exception during request processing")

    request_id = request.headers.get("X-Request-ID")
    return _build_error_response(
        status_code=500,
        error_code="INTERNAL_ERROR",
        message="An internal error occurred. Please try again later.",
        request_id=request_id,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI application.

    Called during app startup in main.py.
    """
    app.add_exception_handler(CertFlowError, certflow_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)
