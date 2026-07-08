"""Celery application.

Defines the Celery app and its configuration (Redis broker + result backend).
No tasks are registered in this milestone; the ``include`` list and queue
topology are added when background work is introduced. The worker process runs
this app via ``celery -A app.worker.celery_app worker``.
"""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "dcip",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks.evidence", "app.worker.tasks.watchlist"],
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
    task_always_eager=settings.celery_task_always_eager,
    broker_connection_retry_on_startup=True,
)
