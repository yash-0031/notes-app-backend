from celery import Celery
import os
from celery.schedules import crontab

celery_app = Celery(
    "noteshare",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    timezone="UTC",
    enable_utc=True,

    task_acks_late=True,

    worker_prefetch_multiplier=1,

    result_expires=3600,
)

celery_app.conf.beat_schedule = {
    "cleanup-archived-embeddings": {
        "task": "cleanup_archived_embeddings",
        "schedule": crontab(minute=0), 
    },
}

celery_app.autodiscover_tasks(["app.tasks"])

# Ensure task modules are imported so Celery workers register named tasks.
from app.tasks import embedding_tasks  # noqa: E402,F401
