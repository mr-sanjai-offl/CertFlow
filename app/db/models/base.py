"""
SQLAlchemy declarative base and common column mixins.

All ORM models inherit from Base.  The TimestampMixin provides
created_at automatically so we don't repeat it in every model.

Interview note:
  If asked "why UUIDs instead of auto-increment integers?" —
  UUIDs are non-sequential, so they don't leak information about
  how many records exist. They're safe to expose in URLs and don't
  require the database to assign them (useful for distributed systems).
  Trade-off: slightly larger storage and slower index lookups than integers.
  For this project's scale, the trade-off is acceptable.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models in CertFlow."""

    pass


class TimestampMixin:
    """Mixin that adds a created_at column to any model.

    Uses timezone-aware UTC timestamps. The default is set at the
    Python level (not database level) for portability across databases
    (PostgreSQL in production, SQLite in some tests).
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
