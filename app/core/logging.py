"""
Structured logging configuration.

Sets up Python's built-in logging with a consistent format that includes
fields useful for debugging production issues:
  - timestamp
  - level
  - logger name
  - message

Later phases will add request_id, job_id, and recipient_id context
via logging filters or contextvars.

Interview note:
  If asked "how would you debug a failed certificate in production?" —
  explain that structured logs include job_id and recipient_id so you
  can filter logs for a specific recipient's processing history.
"""

import logging
import sys

from app.core.config import get_settings


def setup_logging() -> None:
    """Configure application-wide logging.

    Called once during application startup (in main.py lifespan).
    Uses a simple, readable format suitable for development.
    In production, this could be switched to JSON format for
    log aggregation tools.
    """
    settings = get_settings()

    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    logging.basicConfig(
        level=settings.LOG_LEVEL.upper(),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,  # Override any existing root logger config
    )

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger.

    Usage:
        logger = get_logger(__name__)
        logger.info("Job created", extra={"job_id": job_id})
    """
    return logging.getLogger(name)
