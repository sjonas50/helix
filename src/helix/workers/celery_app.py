"""Celery application configuration for Helix background workers."""

from celery import Celery

from helix.config import get_settings

settings = get_settings()

celery_app = Celery(
    "helix",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_routes={
        "helix.workers.workflow_tasks.*": {"queue": "workflow"},
        "helix.workers.dream_tasks.*": {"queue": "dream"},
    },
    beat_schedule={
        "check-dream-triggers": {
            "task": "helix.workers.dream_tasks.check_dream_triggers",
            "schedule": 900.0,  # 15 minutes
        },
    },
)
