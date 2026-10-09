# CertFlow

**Production-Grade Bulk Certificate Generation API**

An asynchronous REST API for bulk certificate generation with job tracking, per-recipient failure isolation, idempotent requests, persistent job state, and downloadable certificate artifacts.

---

## 1. Project Overview

CertFlow is a backend API that accepts bulk certificate generation requests, processes them asynchronously using a background worker, and provides endpoints to track progress and retrieve generated PDF certificates. It is built to be robust, secure, and production-ready.

## 2. Problem Statement

Organizations need to generate certificates for events — workshops, courses, competitions. When the recipient list grows to hundreds or thousands, generating certificates one-by-one through individual API requests is impractical. The process needs to:
- Accept a batch of recipients in a single request.
- Generate certificates asynchronously so the client isn't blocked.
- Track progress so the client can monitor the job.
- Handle individual failures without stopping the entire batch.
- Allow generated certificates to be securely downloaded.

## 3. Key Features

- **Bulk Processing**: Accept hundreds of recipients in a single payload.
- **Asynchronous Execution**: Celery workers handle heavy PDF generation in the background.
- **Per-Recipient Tracking**: Granular success and failure tracking for each individual recipient.
- **Idempotency**: Prevent duplicate jobs from being created if a client retries a request.
- **Secure Access**: API key authentication to protect business endpoints.
- **Path Traversal Protection**: Securely stream files without exposing internal storage paths.
- **Health Checks**: Unauthenticated liveness and readiness probes for orchestrator monitoring.

## 4. Architecture and Request-Processing Flow

### Architecture Diagram
```
Client
  │
  ▼
FastAPI (HTTP API)
  │
  ├─── Pydantic validation
  │
  ▼
Service Layer (business logic)
  │
  ▼
PostgreSQL (persistent state)
  │
  ▼
Redis (message broker)
  │
  ▼
Celery Worker (background processing)
  │
  ├─── CertificateGenerator (PDF creation)
  │
  ├─── StorageService (file storage)
  │
  ▼
PostgreSQL (status updates)
```

### Request-to-Worker Flow
1. Client sends a `POST /api/v1/jobs` request containing event details and a list of recipients.
2. FastAPI validates the payload and creates the `GenerationJob` and its recipients inside a single PostgreSQL transaction.
3. Once the database commit succeeds, the API dispatches the Job ID to the Celery queue via Redis.
4. The HTTP endpoint immediately returns `202 Accepted` to the client.
5. The Celery Worker picks up the job ID, fetches the job from PostgreSQL, and processes the recipients sequentially.
6. The Worker generates the PDFs, stores them, and updates the database statuses.

## 5. Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| API Framework | FastAPI | HTTP endpoints, request validation, OpenAPI docs |
| Validation | Pydantic v2 | Request/response schema validation |
| Database | PostgreSQL | Persistent storage for jobs, recipients, certificates |
| ORM | SQLAlchemy 2.x | Database access and model definitions |
| Migrations | Alembic | Database schema versioning |
| Task Queue | Celery | Asynchronous background processing |
| Message Broker | Redis | Celery task queue and result backend |
| PDF Generation | ReportLab | Certificate PDF creation |
| Testing | Pytest + HTTPX | Unit and integration tests |
| Containerization | Docker Compose | Local development environment |
| Code Quality | Ruff | Linting and formatting |

## 6. Repository Structure

```
certflow/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── api/v1/              # HTTP route handlers
│   ├── core/                # Config, logging, security, exceptions
│   ├── db/                  # Database session and ORM models
│   ├── schemas/             # Pydantic validation models
│   ├── services/            # Business logic (Job, Certificate, Storage)
│   ├── workers/             # Celery background tasks
│   └── generators/          # PDF certificate generation
├── tests/                   # Unit and integration test suite
├── migrations/              # Alembic database migrations
├── templates/               # Certificate template assets
└── storage/                 # Generated certificate files (gitignored)
```

## 7. Prerequisites

- Python 3.12+
- PostgreSQL 16+ (or use Docker)
- Redis 7+ (or use Docker)
- Docker & Docker Compose (for containerized execution)

## 8. Environment Setup

Copy the environment example and configure your variables:
```bash
cp .env.example .env
```

Edit `.env` to match your local setup if you are not using Docker for the database and Redis.

## 9. How to Generate a Strong API Key

All business endpoints are protected by API Key authentication. To generate a cryptographically strong, URL-safe key, run the following command in your terminal:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
Place the output in your `.env` file under the `API_KEY` variable.

## 10. How to Start the Services with Docker Compose

To start the API, PostgreSQL, Redis, and the Celery worker all together:
```bash
docker compose up --build
```
The API will be available at `http://localhost:8000`.

## 11. How to Run Database Migrations

When running locally without Docker:
```bash
alembic upgrade head
```
*(Note: The provided Docker Compose configuration automatically runs migrations before starting the FastAPI server.)*

## 12. How to Start the API and Celery Worker (Local)

If you are developing locally without Docker Compose:

**Terminal 1 (FastAPI):**
```bash
uvicorn app.main:app --reload
```

**Terminal 2 (Celery Worker):**
```bash
# On Windows, add --pool=solo
celery -A app.workers.celery_app worker --loglevel=info
```

## 13. How to Open Swagger UI and Authenticate

1. Navigate to `http://localhost:8000/docs` in your browser.
2. Click the green **Authorize** button near the top right.
3. Enter your configured `API_KEY` in the `X-API-Key` field.
4. Click **Authorize** and then **Close**. You can now execute protected endpoints from the Swagger UI.

## 14. Example Job-Creation Request and Response

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Idempotency-Key: unique-request-id-123" \
  -d '{
    "event": {
      "name": "Python Workshop 2026",
      "organization": "Open Source Tech",
      "date": "2026-10-15"
    },
    "recipients": [
      {"name": "Alice Smith", "email": "alice@example.com"},
      {"name": "Bob Jones", "email": "bob@example.com"}
    ]
  }'
```

**Response (`202 Accepted`):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "QUEUED",
  "event_name": "Python Workshop 2026",
  "event_organization": "Open Source Tech",
  "event_date": "2026-10-15",
  "total_count": 2,
  "success_count": 0,
  "failed_count": 0,
  "created_at": "2026-10-09T14:30:00Z"
}
```

## 15. How to Check Job Status and Progress

```bash
curl -H "X-API-Key: YOUR_API_KEY" http://localhost:8000/api/v1/jobs/123e4567-e89b-12d3-a456-426614174000/progress
```

**Response:**
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "PROCESSING",
  "total_count": 2,
  "success_count": 1,
  "failed_count": 0,
  "pending_count": 1,
  "processing_count": 0,
  "progress_percentage": 50.0
}
```

## 16. How to Retrieve Paginated Recipient Results

```bash
curl -H "X-API-Key: YOUR_API_KEY" "http://localhost:8000/api/v1/jobs/123e4567-e89b-12d3-a456-426614174000/recipients?skip=0&limit=10"
```

**Response:**
```json
[
  {
    "id": "abc-123",
    "name": "Alice Smith",
    "email": "alice@example.com",
    "status": "SUCCESS",
    "certificate_id": "def-456",
    "error_message": null
  }
]
```

## 17. How to Download a Generated Certificate

Extract the `certificate_id` from the recipient results and download the PDF. The `-f -O -J` flags tell curl to save the file using the server-provided filename.

```bash
curl -f -OJ -H "X-API-Key: YOUR_API_KEY" http://localhost:8000/api/v1/certificates/def-456/download
```

## 18. How to Run Tests and Linting

```bash
# Run all tests
pytest

# Run linting with Ruff
ruff check .

# Run formatting checks with Ruff
ruff format --check .
```

## 19. Important Design Decisions

- **Idempotency:** The `/jobs` POST endpoint uses an `Idempotency-Key` header. If a client safely retries a network-failed request, the API returns the existing queued job instead of duplicating it.
- **Celery Retry Safety:** Background workers manage their own database sessions and use standard Celery retries for transient errors. They do not prematurely mark jobs as `FAILED` unless `max_retries` is exceeded.
- **Graceful Health Checks:** The `/health/ready` check does not hard-fail the entire API if Redis is temporarily unavailable. The API degrades gracefully, allowing users to still download existing certificates.
- **Path Traversal Protection:** The storage service ensures absolute validation against directory escapes (`../../etc/passwd`) before streaming any file bytes to the client.

## 20. Known Limitations and Future Improvements

- **Single-Tenant Authorization:** Currently, the API uses a single global `API_KEY` for all authentication. It prevents anonymous access but does not provide multi-tenant or per-user data isolation. Any valid key can access any job.
- **Synchronous Polling:** Progress tracking currently relies on REST polling. WebSockets or Server-Sent Events (SSE) would improve real-time tracking efficiency.
- **Local Storage:** Certificates are stored on the local filesystem. This is unsuitable for horizontal scaling. Future enhancements should include an AWS S3 (or compatible) storage implementation behind the `StorageService` abstraction.
- **Rate Limiting:** No strict API rate limits exist yet to prevent abuse of the generation endpoint..
