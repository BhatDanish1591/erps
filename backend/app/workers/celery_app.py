from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "edusaas",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.notification_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,
    task_time_limit=360,
    beat_schedule={
        "process-notification-outbox": {
            "task": "notifications.process_pending_outbox_batch",
            "schedule": 30.0,
            "options": {"expires": 30},
        },
    },
)
