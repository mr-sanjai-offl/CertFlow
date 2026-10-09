from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "certflow_worker",
    broker=settings.REDIS_URL,
    # We do not strictly need a result backend for task state since our PostgreSQL DB is the source of truth,
    # but we configure it to Redis so Celery can internally track task failures if needed.
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Optional: limit retries and routing configurations could go here.
)

# Auto-discover tasks in the app.workers.tasks module
celery_app.autodiscover_tasks(["app.workers"])
