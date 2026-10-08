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

## API Endpoints (Phase 1)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Liveness check — is the process running? |
| GET | `/health/ready` | Readiness check — are dependencies reachable? |

More endpoints will be added in subsequent phases.

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
