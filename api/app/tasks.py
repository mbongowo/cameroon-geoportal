"""Celery client — the API dispatches jobs to the worker by name.

The worker owns the task implementations; the API only enqueues and polls, so it
references tasks by their registered name (``worker.clip_export``) rather than
importing worker code.
"""
from __future__ import annotations

from celery import Celery

from app.config import settings

celery_client = Celery(
    "geoportal-api",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_client.conf.update(task_serializer="json", accept_content=["json"])
