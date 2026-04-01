"""Celery tasks for webhook data ingest into memory."""

import asyncio
from typing import Any

import structlog

from helix.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="helix.workers.ingest_tasks.ingest_webhook", queue="workflow")
def ingest_webhook(
    org_id: str, provider: str, event_type: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """Async ingest a webhook payload into memory_records."""

    async def _inner() -> dict[str, Any]:
        from uuid import UUID

        from helix.db.engine import get_session_factory
        from helix.integrations.ingest import ingest_webhook_to_memory

        session_factory = get_session_factory()
        async with session_factory() as session:
            record_id = await ingest_webhook_to_memory(
                session,
                UUID(org_id),
                provider,
                event_type,
                payload,
            )
            return {
                "status": "ingested" if record_id else "skipped",
                "record_id": record_id,
            }

    return asyncio.run(_inner())
