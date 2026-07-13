from celery import Celery

from config.settings import REDIS_URL

celery = Celery(
    "gmaps_scraper",
    include=["services.scraping_service"],
)

celery.conf.update(
    broker_url=REDIS_URL,
    result_backend=REDIS_URL,
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery.autodiscover_tasks(["services"])
