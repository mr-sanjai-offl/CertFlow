import uuid
from datetime import date

import pytest
from pydantic import ValidationError

from app.core.config import get_settings
from app.db.models.enums import JobStatus, RecipientStatus
from app.schemas.job import EventInfo, JobCreate, JobProgress, JobStatusResponse
from app.schemas.recipient import RecipientCreate, RecipientResponse

# --- Valid Input Tests ---


def test_valid_recipient():
    """A recipient with valid name and email should pass validation."""
    recipient = RecipientCreate(name="John Doe", email="john@example.com")
    assert recipient.name == "John Doe"
    assert recipient.email == "john@example.com"


def test_valid_event():
    """An event with valid name, organization, and date should pass validation."""
    event = EventInfo(name="Python Workshop", organization="Example Corp", date="2026-10-08")
    assert event.name == "Python Workshop"
    assert event.organization == "Example Corp"
    assert event.date == date(2026, 10, 8)


def test_valid_job_create():
    """A job with a valid event and multiple valid recipients should pass."""
    payload = {
        "event": {"name": "Python Workshop", "organization": "Example Corp", "date": "2026-10-08"},
        "recipients": [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob", "email": "bob@example.com"},
        ],
    }
    job = JobCreate.model_validate(payload)
    assert job.event.name == "Python Workshop"
    assert len(job.recipients) == 2


# --- Invalid Input Tests ---


def test_invalid_recipient_name_missing():
    """Recipient name is required."""
    with pytest.raises(ValidationError) as exc:
        RecipientCreate(email="john@example.com")
    assert "name" in str(exc.value)


def test_invalid_recipient_name_empty():
    """Recipient name cannot be empty."""
    with pytest.raises(ValidationError) as exc:
        RecipientCreate(name="", email="john@example.com")
    assert "String should have at least 1 character" in str(exc.value)


def test_invalid_recipient_name_whitespace():
    """Recipient name cannot be only whitespace (it gets stripped)."""
    with pytest.raises(ValidationError) as exc:
        RecipientCreate(name="   ", email="john@example.com")
    assert "String should have at least 1 character" in str(exc.value)


def test_invalid_recipient_email():
    """Email must be structurally valid."""
    with pytest.raises(ValidationError) as exc:
        RecipientCreate(name="John", email="not-an-email")
    assert "value is not a valid email address" in str(exc.value)


def test_invalid_job_create_empty_recipients():
    """A job must have at least one recipient."""
    payload = {
        "event": {"name": "Python Workshop", "organization": "Example Corp", "date": "2026-10-08"},
        "recipients": [],
    }
    with pytest.raises(ValidationError) as exc:
        JobCreate.model_validate(payload)
    assert "List should have at least 1 item" in str(exc.value)


def test_invalid_job_create_too_many_recipients():
    """A job cannot exceed the configured maximum number of recipients."""
    max_recipients = get_settings().MAX_RECIPIENTS_PER_JOB
    payload = {
        "event": {"name": "Python Workshop", "organization": "Example Corp", "date": "2026-10-08"},
        "recipients": [
            {"name": f"User {i}", "email": f"user{i}@example.com"}
            for i in range(max_recipients + 1)
        ],
    }
    with pytest.raises(ValidationError) as exc:
        JobCreate.model_validate(payload)
    assert f"List should have at most {max_recipients} item" in str(exc.value)


def test_invalid_job_create_missing_event():
    """A job must include event information."""
    payload = {"recipients": [{"name": "Alice", "email": "alice@example.com"}]}
    with pytest.raises(ValidationError) as exc:
        JobCreate.model_validate(payload)
    assert "event" in str(exc.value)


def test_invalid_event_date():
    """The event date must be a valid date format."""
    with pytest.raises(ValidationError) as exc:
        EventInfo(name="A", organization="B", date="not-a-date")
    assert "Input should be a valid date" in str(exc.value)


# --- Response Serialization Tests ---


def test_job_status_response_serialization():
    """Enums, UUIDs, and nested progress should serialize correctly."""
    job_id = uuid.uuid4()
    response = JobStatusResponse(
        id=job_id,
        status=JobStatus.PROCESSING,
        total_count=100,
        progress=JobProgress(total=100, completed=50, failed=10, pending=40, percentage=60.0),
    )
    dump = response.model_dump(mode="json")
    assert dump["id"] == str(job_id)
    assert dump["status"] == "PROCESSING"  # Enum string representation
    assert dump["progress"]["percentage"] == 60.0


def test_recipient_response_nullable_fields():
    """Nullable fields like error messages and certificate IDs serialize gracefully."""
    recipient_id = uuid.uuid4()
    job_id = uuid.uuid4()

    # Successful recipient
    cert_id = uuid.uuid4()
    success_resp = RecipientResponse(
        id=recipient_id,
        job_id=job_id,
        name="Alice",
        email="alice@example.com",
        status=RecipientStatus.SUCCESS,
        attempt_count=1,
        error_code=None,
        error_message=None,
        certificate_id=cert_id,
    )
    dump_success = success_resp.model_dump(mode="json")
    assert dump_success["error_code"] is None
    assert dump_success["certificate_id"] == str(cert_id)

    # Failed recipient
    fail_resp = RecipientResponse(
        id=recipient_id,
        job_id=job_id,
        name="Bob",
        email="bob@example.com",
        status=RecipientStatus.FAILED,
        attempt_count=3,
        error_code="RENDER_ERROR",
        error_message="Font missing",
        certificate_id=None,
    )
    dump_fail = fail_resp.model_dump(mode="json")
    assert dump_fail["error_code"] == "RENDER_ERROR"
    assert dump_fail["certificate_id"] is None
