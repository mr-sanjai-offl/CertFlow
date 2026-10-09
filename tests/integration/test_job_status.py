import datetime
import uuid

from sqlalchemy.orm import Session

from app.db.models.certificate import Certificate
from app.db.models.enums import JobStatus, RecipientStatus
from app.db.models.job import GenerationJob
from app.db.models.recipient import CertificateRecipient


def create_mock_job(db_session: Session, recipient_count: int = 2) -> GenerationJob:
    job_id = uuid.uuid4()
    job = GenerationJob(
        id=job_id,
        status=JobStatus.QUEUED,
        event_name="Test Event",
        event_organization="Test Org",
        event_date=datetime.date(2026, 1, 1),
        total_count=recipient_count,
        success_count=0,
        failed_count=0,
    )
    recipients = [
        CertificateRecipient(
            id=uuid.uuid4(),
            job_id=job_id,
            name=f"User {i}",
            email=f"user{i}@example.com",
            status=RecipientStatus.PENDING,
        )
        for i in range(recipient_count)
    ]
    db_session.add(job)
    db_session.add_all(recipients)
    db_session.commit()
    db_session.refresh(job)
    return job


class TestJobDetailsAPI:
    def test_get_job_details_success(self, client, db_session):
        job = create_mock_job(db_session)
        response = client.get(f"/api/v1/jobs/{job.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(job.id)
        assert data["status"] == "QUEUED"
        assert data["event_name"] == "Test Event"
        assert data["event_organization"] == "Test Org"
        assert data["total_count"] == 2
        assert "storage_path" not in data
        assert "storage_dir" not in data

    def test_get_job_details_not_found(self, client):
        response = client.get(f"/api/v1/jobs/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_get_job_details_malformed_uuid(self, client):
        response = client.get("/api/v1/jobs/not-a-uuid")
        # FastAPI Path parameter validation should return 422
        assert response.status_code == 422


class TestJobProgressAPI:
    def test_queued_job_returns_zero_processed(self, client, db_session):
        job = create_mock_job(db_session, recipient_count=5)
        response = client.get(f"/api/v1/jobs/{job.id}/progress")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 5
        assert data["success_count"] == 0
        assert data["failed_count"] == 0
        assert data["pending_count"] == 5
        assert data["progress_percentage"] == 0.0

    def test_all_successful_recipients(self, client, db_session):
        job = create_mock_job(db_session, recipient_count=2)
        job.status = JobStatus.COMPLETED
        for rec in job.recipients:
            rec.status = RecipientStatus.SUCCESS
        db_session.commit()

        response = client.get(f"/api/v1/jobs/{job.id}/progress")
        assert response.status_code == 200
        data = response.json()
        assert data["progress_percentage"] == 100.0
        assert data["success_count"] == 2

    def test_mixed_success_and_failure(self, client, db_session):
        job = create_mock_job(db_session, recipient_count=4)
        recipients = job.recipients
        recipients[0].status = RecipientStatus.SUCCESS
        recipients[1].status = RecipientStatus.FAILED
        recipients[2].status = RecipientStatus.PROCESSING
        recipients[3].status = RecipientStatus.PENDING
        db_session.commit()

        response = client.get(f"/api/v1/jobs/{job.id}/progress")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 4
        assert data["success_count"] == 1
        assert data["failed_count"] == 1
        assert data["processing_count"] == 1
        assert data["pending_count"] == 1
        assert data["progress_percentage"] == 50.0  # (1+1)/4

    def test_all_failed_job(self, client, db_session):
        job = create_mock_job(db_session, recipient_count=2)
        job.status = JobStatus.FAILED
        for rec in job.recipients:
            rec.status = RecipientStatus.FAILED
        db_session.commit()

        response = client.get(f"/api/v1/jobs/{job.id}/progress")
        assert response.status_code == 200
        data = response.json()
        assert data["progress_percentage"] == 100.0
        assert data["failed_count"] == 2
        assert data["success_count"] == 0

    def test_zero_total_handling(self, client, db_session):
        job = create_mock_job(db_session, recipient_count=0)
        response = client.get(f"/api/v1/jobs/{job.id}/progress")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert data["progress_percentage"] == 0.0


class TestRecipientListAPI:
    def test_existing_job_returns_recipients(self, client, db_session):
        job = create_mock_job(db_session, recipient_count=2)
        # Mock a generated certificate
        cert = Certificate(
            id=uuid.uuid4(),
            recipient_id=job.recipients[0].id,
            file_name="cert.pdf",
            storage_path="/tmp/cert.pdf",
            file_size=100,
        )
        job.recipients[0].status = RecipientStatus.SUCCESS
        job.recipients[1].status = RecipientStatus.FAILED
        job.recipients[1].error_message = "Safe error msg"
        db_session.add(cert)
        db_session.commit()

        response = client.get(f"/api/v1/jobs/{job.id}/recipients")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

        # Verify internal paths are not exposed
        for item in data["items"]:
            assert "storage_path" not in item

        success_item = next(i for i in data["items"] if i["status"] == "SUCCESS")
        assert success_item["certificate_id"] == str(cert.id)

        failed_item = next(i for i in data["items"] if i["status"] == "FAILED")
        assert failed_item["error_message"] == "Safe error msg"
        assert failed_item["certificate_id"] is None

    def test_unknown_job_returns_404(self, client):
        response = client.get(f"/api/v1/jobs/{uuid.uuid4()}/recipients")
        assert response.status_code == 404

    def test_pagination_limits_and_offsets(self, client, db_session):
        job = create_mock_job(db_session, recipient_count=5)

        # Page 1: limit 2, offset 0
        res1 = client.get(f"/api/v1/jobs/{job.id}/recipients?limit=2&offset=0")
        assert res1.status_code == 200
        data1 = res1.json()
        assert len(data1["items"]) == 2
        assert data1["total"] == 5

        # Page 2: limit 2, offset 2
        res2 = client.get(f"/api/v1/jobs/{job.id}/recipients?limit=2&offset=2")
        assert res2.status_code == 200
        data2 = res2.json()
        assert len(data2["items"]) == 2

        # Ensure no overlap
        ids1 = {i["id"] for i in data1["items"]}
        ids2 = {i["id"] for i in data2["items"]}
        assert ids1.isdisjoint(ids2)

    def test_invalid_pagination(self, client, db_session):
        job = create_mock_job(db_session)
        # negative offset
        response = client.get(f"/api/v1/jobs/{job.id}/recipients?offset=-1")
        assert response.status_code == 422
        # over max limit
        response = client.get(f"/api/v1/jobs/{job.id}/recipients?limit=2000")
        assert response.status_code == 422
