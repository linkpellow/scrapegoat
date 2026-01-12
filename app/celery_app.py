from celery import Celery
from app.config import settings

celery_app = Celery(
    "scraper_platform",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    broker_transport_options={"visibility_timeout": 60 * 60},
)

# Import tasks to ensure they're registered
celery_app.autodiscover_tasks(["app.workers"])
