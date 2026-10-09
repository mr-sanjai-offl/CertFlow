# CertFlow

**Production-Grade Bulk Certificate Generation API**

An asynchronous REST API for bulk certificate generation with job tracking, per-recipient failure isolation, idempotent requests, persistent job state, and downloadable certificate artifacts.

---

## Problem

Organizations need to generate certificates for events — workshops, courses, competitions. When the recipient list grows to hundreds or thousands, generating certificates one-by-one through individual API requests is impractical. The process needs to:

- Accept a batch of recipients in a single request
- Generate certificates asynchronously (the client shouldn't wait)
- Track progress so the client can check how the job is going
- Handle individual failures without stopping the entire batch
- Allow generated certificates to be downloaded

## Solution

CertFlow is a backend API that accepts bulk certificate generation requests, processes them asynchronously using a background worker, and provides endpoints to track progress and retrieve generated PDF certificates.

### Architecture

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

## Tech Stack

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
| Code Quality | Ruff + Black | Linting and formatting |

### Why Celery and Redis?

- **Celery** is a mature Python task-processing framework that is suitable for handling asynchronous certificate-generation jobs in this project. It isolates CPU-heavy PDF generation from the Fast API web layer, ensuring endpoints remain responsive.
- **Redis** is used as the message broker to queue tasks between FastAPI and Celery. It's lightweight, extremely fast, and natively supported by Celery.

### Request-to-Worker Flow

1. Client sends a `POST /api/v1/jobs` request containing event details and a list of recipients.
2. FastAPI validates the payload via Pydantic and creates the `GenerationJob` and its recipients inside a single PostgreSQL transaction.
3. Once the database commit succeeds, the API dispatches the Job ID to the Celery queue via Redis.
4. The HTTP endpoint immediately returns `202 Accepted` to the client.
5. The Celery Worker picks up the job ID, fetches the job from PostgreSQL, and processes the recipients sequentially.
6. The Worker generates the PDFs, stores them, and updates the database statuses.

**Known Limitations:** The database commit and Redis queue dispatch are not perfectly atomic. If the database commit succeeds but Redis is unavailable, the API will safely catch the failure, return a `503 Service Unavailable`, and keep the job safely in the database with a `QUEUED` state. The client can retry the idempotent request to successfully dispatch the queued job later.

## Current Status

**Phase 1: Project Foundation** ✅

- [x] Project structure and configuration
- [x] FastAPI application with health endpoints
- [x] Database session management (skeleton)
- [x] Alembic migration setup
- [x] Docker Compose (PostgreSQL, Redis, API, Worker)
- [x] Test framework with initial health check tests
- [x] Linting and formatting configuration

**Phase 2: Database Models and Migrations** ✅

- [x] GenerationJob model
- [x] CertificateRecipient model
- [x] Certificate model
- [x] Job and recipient status enums
- [x] Alembic migration and verification
- [x] Model-level unit tests

**Phase 6: Celery Background Processing** ✅

- [x] Celery application and Redis configuration
- [x] Background worker dispatch boundary
- [x] Sequential recipient PDF processing
- [x] Worker-managed PostgreSQL sessions
- [x] Idempotent retry handling
- [x] Docker compose worker setup

**Phase 7: Job Status and Progress API** ✅

- [x] Job Details endpoint (`GET /api/v1/jobs/{job_id}`)
- [x] Job Progress endpoint (`GET /api/v1/jobs/{job_id}/progress`)
- [x] Job Recipients endpoint with pagination (`GET /api/v1/jobs/{job_id}/recipients`)
- [x] Progress calculated accurately from recipient outcomes

**Phase 8: Certificate Retrieval and Download API** ✅

- [x] Certificate download endpoint (`GET /api/v1/certificates/{certificate_id}/download`)
- [x] Stream artifact directly without loading into memory entirely
- [x] Protect against path traversal and hide storage paths

**Phase 9: API Key Authentication and Authorization** ✅

- [x] Protect API using standard `X-API-Key` headers
- [x] Fail-closed validation for configured keys
- [x] Unauthenticated health checks for orchestrator monitoring

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 16+ (or use Docker)
- Redis 7+ (or use Docker)

### Local Development (without Docker)

```bash
# 1. Clone and enter project
git clone <repo-url>
cd certflow

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Copy environment config
cp .env.example .env
# Edit .env with your database and Redis connection details

# 5. Run the application
uvicorn app.main:app --reload

# 6. Run tests
pytest

# 7. Run linting
ruff check .

# 8. Run formatting check
black --check .
```

### Docker Development

```bash
# Start all services (PostgreSQL, Redis, API, Worker)
docker compose up

# The API will be available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Liveness check — is the process running? |
| GET | `/health/ready` | Readiness check — are dependencies reachable? |
| POST | `/api/v1/jobs` | Create a new bulk generation job. Returns `202 Accepted` |
| GET | `/api/v1/jobs/{job_id}` | Retrieve job details, counters, and metadata |
| GET | `/api/v1/jobs/{job_id}/progress` | Retrieve concise processing progress |
| GET | `/api/v1/jobs/{job_id}/recipients` | List recipients and their results (paginated) |
| GET | `/api/v1/certificates/{certificate_id}/download` | Download a successfully generated PDF certificate |

### Polling for Progress

To track a job, clients should poll the progress endpoint:

```http
GET /api/v1/jobs/123e4567-e89b-12d3-a456-426614174000/progress
```

**Example Response:**
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "PROCESSING",
  "total_count": 100,
  "success_count": 50,
  "failed_count": 5,
  "pending_count": 45,
  "processing_count": 0,
  "progress_percentage": 55.0
}
```

**How Progress is Calculated:**
Progress percentage is accurately derived from the actual recipient records in the database, even while the background worker is running:
`((success_count + failed_count) / total_count) * 100`

### Job Status Meanings

- `QUEUED`: Job is waiting to be picked up by the Celery worker.
- `PROCESSING`: Worker is actively generating certificates.
- `COMPLETED`: All recipients successfully processed.
- `COMPLETED_WITH_ERRORS`: Job finished, but some recipients failed (e.g. invalid email).
- `FAILED`: Total job failure (e.g. invalid event config) or all recipients failed.

### Downloading Certificates

To download a generated certificate by its ID:

```bash
curl -f -OJ http://localhost:8000/api/v1/certificates/123e4567-e89b-12d3-a456-426614174000/download
```

**Expected Success Response Headers:**
```http
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="certificate-123e4567-e89b-12d3-a456-426614174000.pdf"
```

**Possible Errors:**
- `404 Not Found`: The certificate record does not exist or the underlying PDF artifact is missing.

*Note: Authentication is currently not implemented. This endpoint relies on the application's existing access model.*

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+pg8000://certflow:certflow@localhost:5432/certflow` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL for Celery broker/backend |
| `STORAGE_DIR` | `./storage` | Local certificate storage path |
| `MAX_RECIPIENTS_PER_JOB` | `1000` | Maximum recipients per request |
| `MAX_RETRIES` | `3` | Retry limit for transient failures |
| `LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `ENVIRONMENT` | `development` | Environment name |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins (comma-separated) |

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/integration/test_health.py
```

## Project Structure

```
certflow/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── api/v1/              # HTTP route handlers
│   ├── core/                # Config, logging, exceptions
│   ├── db/                  # Database session and ORM models
│   ├── schemas/             # Pydantic validation models
│   ├── services/            # Business logic
│   ├── workers/             # Celery background tasks
│   └── generators/          # PDF certificate generation
├── tests/                   # Test suite
├── migrations/              # Alembic database migrations
├── templates/               # Certificate template assets
└── storage/                 # Generated certificate files (gitignored)
```

## Design Decisions

Documented in the architecture document. Key decisions will be added to this section as the project progresses.

- **Generic Uuid Type:** The database models use SQLAlchemy's generic `Uuid` type instead of PostgreSQL-specific `UUID`. This architectural correction ensures the application can seamlessly fall back to SQLite for robust unit testing while natively utilizing Postgres UUIDs in production.

## Database Design

The data layer uses the following relational hierarchy to enforce referential integrity and tracking:

```
GenerationJob
     │ (1-to-many)
     ↓
CertificateRecipient
     │ (1-to-1)
     ↓
Certificate
```

### 1. GenerationJob
Tracks the bulk generation request. Contains counters (`total_count`, `success_count`, `failed_count`) to efficiently serve API progress requests without doing expensive aggregate queries. Uses an explicit `idempotency_key` constraint to prevent duplicate bulk jobs.
- **States:** `QUEUED`, `PROCESSING`, `COMPLETED`, `COMPLETED_WITH_ERRORS`, `FAILED`

### 2. CertificateRecipient
Isolates per-recipient failure. Belongs to a job. Contains individual retry trackers (`attempt_count`) and safe string-based error representations (`error_code`, `error_message`) avoiding internal stack trace leakage.
- **States:** `PENDING`, `PROCESSING`, `SUCCESS`, `FAILED`

### 3. Certificate
Represents the successfully generated artifact. Has a strictly enforced 1-to-1 relationship with the recipient (a failed recipient gets no artifact). Contains metadata like `storage_path` and `file_size`.

## License

MIT
