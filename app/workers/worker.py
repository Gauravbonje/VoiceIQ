from celery import Celery
from app.core.config import settings


celery = Celery(
    "voiceiq",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)


celery.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",

    # Performance + reliability
    worker_prefetch_multiplier=1,
    task_acks_late=True,

    # Expire results after 1 day
    result_expires=86400,
)