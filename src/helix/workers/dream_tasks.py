"""Celery tasks for Dream Cycle execution."""

import structlog

from helix.workers.celery_app import celery_app

logger = structlog.get_logger()


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
        # In production: run full 4-phase dream cycle with DB session
        return {"status": "complete", "org_id": org_id}
    except Exception as e:
        logger.error("dream.cycle_failed", org_id=org_id, error=str(e))
        return {"status": "failed", "org_id": org_id, "error": str(e)}
    finally:
        r.delete(lock_key)
        logger.info("dream.lock_released", org_id=org_id)
