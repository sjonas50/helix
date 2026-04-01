"""Tests for Celery configuration and dream tasks."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID


def test_celery_app_configured():
    """Verify Celery app has correct queue routing and beat schedule."""
    from helix.workers.celery_app import celery_app

    routes = celery_app.conf.task_routes
    assert "helix.workers.workflow_tasks.*" in routes
    assert routes["helix.workers.workflow_tasks.*"]["queue"] == "workflow"
    assert "helix.workers.dream_tasks.*" in routes
    assert routes["helix.workers.dream_tasks.*"]["queue"] == "dream"

    beat = celery_app.conf.beat_schedule
    assert "check-dream-triggers" in beat
    assert beat["check-dream-triggers"]["schedule"] == 900.0
    assert (
        beat["check-dream-triggers"]["task"]
        == "helix.workers.dream_tasks.check_dream_triggers"
    )


def test_dream_task_acquires_lock():
    """Verify run_dream_cycle_task acquires Redis lock via SETNX."""
    mock_redis = MagicMock()
    mock_redis.set.return_value = True  # Lock acquired

    with (
        patch("redis.from_url", return_value=mock_redis),
        patch(
            "helix.config.get_settings",
            return_value=MagicMock(redis_url="redis://localhost:6379/0"),
        ),
        patch(
            "helix.workers.dream_tasks._run_dream_sync",
            return_value={"status": "complete", "org_id": "org-123"},
        ),
    ):
        from helix.workers.dream_tasks import run_dream_cycle_task

        result = run_dream_cycle_task("org-123")

    mock_redis.set.assert_called_once_with(
        "dream_lock:org-123", "1", nx=True, ex=1800
    )
    mock_redis.delete.assert_called_once_with("dream_lock:org-123")
    assert result["status"] == "complete"
    assert result["org_id"] == "org-123"


def test_dream_task_skips_when_locked():
    """Verify task skips execution when lock is already held."""
    mock_redis = MagicMock()
    mock_redis.set.return_value = False  # Lock NOT acquired

    with (
        patch("redis.from_url", return_value=mock_redis),
        patch(
            "helix.config.get_settings",
            return_value=MagicMock(redis_url="redis://localhost:6379/0"),
        ),
    ):
        from helix.workers.dream_tasks import run_dream_cycle_task

        result = run_dream_cycle_task("org-456")

    mock_redis.set.assert_called_once()
    mock_redis.delete.assert_not_called()
    assert result["status"] == "skipped"
    assert result["reason"] == "lock_held"


def test_run_dream_sync_queries_db_and_persists_result():
    """Verify _run_dream_sync creates a session, queries memories, and persists the dream run."""
    from helix.memory.dream import DreamRunResult

    org_id = "550e8400-e29b-41d4-a716-446655440000"
    fake_now = datetime(2025, 1, 1, tzinfo=UTC)

    mock_dream_result = DreamRunResult(
        org_id=UUID(org_id),
        triggered_by="celery",
        phase="COMPLETE",
        sessions_processed=0,
        records_created=0,
        records_updated=0,
        records_pruned=0,
        tokens_used=0,
        completed_at=fake_now,
    )

    # Mock the async session
    mock_session = AsyncMock()
    mock_execute_result = MagicMock()
    mock_execute_result.fetchall.return_value = []  # No existing memories
    mock_session.execute.return_value = mock_execute_result
    mock_session.commit = AsyncMock()

    # Build async context manager for session_factory()
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_factory = MagicMock(return_value=mock_session_ctx)

    with (
        patch(
            "helix.db.engine.get_session_factory",
            return_value=mock_factory,
        ),
        patch(
            "helix.memory.dream.run_dream_cycle",
            return_value=mock_dream_result,
        ) as mock_run,
    ):
        from helix.workers.dream_tasks import _run_dream_sync

        result = _run_dream_sync(org_id)

    assert result["status"] == "COMPLETE"
    assert result["org_id"] == org_id

    # Verify run_dream_cycle was called with correct args
    mock_run.assert_called_once()
    call_kwargs = mock_run.call_args
    assert call_kwargs[1]["org_id"] == UUID(org_id)
    assert call_kwargs[1]["existing_memories"] == []
    assert call_kwargs[1]["session_signals"] == []
    assert call_kwargs[1]["triggered_by"] == "celery"

    # Verify DB commit was called
    mock_session.commit.assert_awaited_once()
