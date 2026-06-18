from celery import Celery
from config import settings
import ssl

celery_app = Celery(
    "audito",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_use_ssl={
        "ssl_cert_reqs": ssl.CERT_NONE,
    },
    redis_backend_use_ssl={
        "ssl_cert_reqs": ssl.CERT_NONE,
    },
)
