"""Tests for Celery configuration and dream tasks."""

from unittest.mock import MagicMock, patch


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
