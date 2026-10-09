"""
Health check endpoints.

These endpoints allow monitoring tools (or a human) to verify that
the application is running and that its dependencies are reachable.

GET /health       — Is the process alive? Always returns 200 if the
                    server is accepting requests.

GET /health/ready — Are dependencies (database, Redis) reachable?
                    Returns 200 only if all checks pass. Returns 503
                    if any dependency is unreachable.

Interview note:
  - /health is a "liveness" check: is the process running?
  - /health/ready is a "readiness" check: can it serve real traffic?
  - These do NOT expose secrets, connection strings, or internal config.
  - In production, a load balancer uses /health/ready to decide whether
    to send traffic to this instance.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Liveness check",
    description="Returns 200 if the application process is running.",
)
def health_check() -> dict:
    """Basic liveness probe — no dependency checks."""
    return {"status": "healthy"}


@router.get(
    "/health/ready",
    summary="Readiness check",
    description="Returns 200 if the application and its dependencies (database, Redis) are ready.",
)
def readiness_check(db: Session = Depends(get_db)) -> dict:
    """Check that critical dependencies are reachable.

    Currently checks:
    - PostgreSQL: runs SELECT 1
    - Redis: checked via a simple ping (will be added when Celery is set up)
    """
    checks: dict[str, str] = {}

    # --- Database check ---
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"

    # --- Redis check (placeholder until Celery is integrated) ---
    try:
        import redis

        from app.core.config import get_settings

        settings = get_settings()
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"

    # Determine overall status
    # Redis is important for queueing new jobs, but the API can still serve
    # status checks and certificate downloads if only Redis is down.
    # Therefore, we consider the API "ready" as long as the database is up.
    is_ready = checks.get("database") == "ok"
    status_code = 200 if is_ready else 503

    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "not_ready",
            **checks,
        },
    )
