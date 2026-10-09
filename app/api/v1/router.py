"""
API v1 router aggregator.

Collects all v1 sub-routers (health, jobs, certificates) into a single
router that is mounted on the FastAPI app in main.py.

Interview note:
  If asked "how would you add a v2 API?" — create an api/v2/ package
  with its own router.py, and mount it on a different prefix in main.py.
  The v1 routes continue to work unchanged.
"""

from fastapi import APIRouter, Depends
from app.core.security import get_api_key

from app.api.v1.certificates import router as certificates_router
from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router

v1_router = APIRouter()

# Health endpoints are mounted at the root level (no /api/v1 prefix)
# because health checks are infrastructure concerns, not API features.
# They are included here for organizational convenience.
health_router_for_root = health_router

# API-versioned routes will be added in later phases:
v1_router.include_router(jobs_router, prefix="/jobs", dependencies=[Depends(get_api_key)])
v1_router.include_router(certificates_router, prefix="/certificates", dependencies=[Depends(get_api_key)])
