"""Shared utilities for the Helix platform."""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Return timezone-aware UTC datetime. Use everywhere instead of datetime.now()."""
    return datetime.now(tz=UTC)
