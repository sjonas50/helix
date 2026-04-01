"""Celery tasks for Dream Cycle execution."""

import asyncio
import uuid

import structlog
from sqlalchemy import text

from helix.workers.celery_app import celery_app

logger = structlog.get_logger()


def _run_dream_sync(org_id: str) -> dict:
    """Synchronous wrapper for async dream cycle."""

    async def _inner() -> dict:
        from helix.db.engine import get_session_factory
        from helix.memory.dream import run_dream_cycle
        from helix.memory.store import MemoryEntry

        session_factory = get_session_factory()
        async with session_factory() as session:
            # Query existing memories for this org
            result = await session.execute(
                text(
                    "SELECT id, org_id, topic, content, tags, access_level, version, "
                    "valid_from, valid_until FROM memory_records WHERE org_id = :org_id"
                ),
                {"org_id": org_id},
            )
            rows = result.fetchall()

            existing = [
                MemoryEntry(
                    id=row[0],
                    org_id=row[1],
                    topic=row[2],
                    content=row[3],
                    tags=row[4] or [],
                    access_level=row[5],
                    version=row[6],
                    valid_from=row[7],
                    valid_until=row[8],
                )
                for row in rows
            ]

            # Run dream cycle (no signals for now — will add LLM extraction later)
            dream_result = run_dream_cycle(
                org_id=uuid.UUID(org_id),
                existing_memories=existing,
                session_signals=[],
                triggered_by="celery",
            )

            # Persist dream run result
            await session.execute(
                text(
                    """INSERT INTO dream_runs
                    (org_id, triggered_by, phase, sessions_processed, records_created,
                     records_updated, records_pruned, tokens_used, completed_at)
                    VALUES (:org_id, :triggered_by, :phase, :sessions_processed, :records_created,
                            :records_updated, :records_pruned, :tokens_used, :completed_at)"""
                ),
                {
                    "org_id": org_id,
                    "triggered_by": dream_result.triggered_by,
                    "phase": dream_result.phase,
                    "sessions_processed": dream_result.sessions_processed,
                    "records_created": dream_result.records_created,
                    "records_updated": dream_result.records_updated,
                    "records_pruned": dream_result.records_pruned,
                    "tokens_used": dream_result.tokens_used,
                    "completed_at": dream_result.completed_at,
                },
            )
            await session.commit()

            return {"status": dream_result.phase, "org_id": org_id}

    return asyncio.run(_inner())


@celery_app.task(name="helix.workers.dream_tasks.check_dream_triggers")
def check_dream_triggers() -> dict:
    """Check all orgs for dream cycle trigger conditions. Runs every 15 min via beat."""
    logger.info("dream.checking_triggers")
    # In production: query all orgs, check should_trigger_dream() for each
    # For qualifying orgs, dispatch run_dream_cycle_task.delay(str(org_id))
    return {"checked": True}


@celery_app.task(
    name="helix.workers.dream_tasks.run_dream_cycle_task",
    bind=True,
    max_retries=0,
)
def run_dream_cycle_task(self, org_id: str) -> dict:  # noqa: ANN001
    """Execute dream cycle for a single org with distributed lock."""
    import redis as redis_lib

    from helix.config import get_settings

    settings = get_settings()
    r = redis_lib.from_url(settings.redis_url)
    lock_key = f"dream_lock:{org_id}"

    # Gate 3: Redis distributed lock (SETNX with 30-min TTL)
    acquired = r.set(lock_key, "1", nx=True, ex=1800)
    if not acquired:
        logger.info("dream.lock_not_acquired", org_id=org_id)
        return {"status": "skipped", "reason": "lock_held"}

    try:
        logger.info("dream.cycle_started", org_id=org_id)
        return _run_dream_sync(org_id)
    except Exception as e:
        logger.error("dream.cycle_failed", org_id=org_id, error=str(e))
        return {"status": "failed", "org_id": org_id, "error": str(e)}
    finally:
        r.delete(lock_key)
        logger.info("dream.lock_released", org_id=org_id)
