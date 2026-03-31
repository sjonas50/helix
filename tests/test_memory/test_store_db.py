"""Tests for database memory operations."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from helix.memory.store import (
    MemoryEntry,
    db_create_memory,
    db_invalidate_memory,
    db_retrieve_relevant,
)


def _make_entry(**overrides) -> MemoryEntry:
    """Create a test MemoryEntry with sensible defaults."""
    defaults = {
        "org_id": uuid.uuid4(),
        "topic": "test-topic",
        "content": "test content",
        "tags": ["test"],
        "access_level": "PUBLIC",
    }
    defaults.update(overrides)
    return MemoryEntry(**defaults)


@pytest.mark.asyncio
async def test_db_create_memory_mock():
    """Verifies INSERT SQL is executed with correct parameters."""
    session = AsyncMock()
    entry = _make_entry()
    embedding = [0.1] * 1536

    result_id = await db_create_memory(session, entry, embedding=embedding)

    session.execute.assert_awaited_once()
    call_args = session.execute.call_args
    sql_text = str(call_args[0][0])
    assert "INSERT INTO memory_records" in sql_text
    assert result_id == entry.id


@pytest.mark.asyncio
async def test_db_create_memory_no_embedding():
    """Verifies INSERT works without embedding."""
    session = AsyncMock()
    entry = _make_entry()

    result_id = await db_create_memory(session, entry, embedding=None)

    session.execute.assert_awaited_once()
    params = session.execute.call_args[0][1]
    assert params["embedding"] is None
    assert result_id == entry.id


@pytest.mark.asyncio
async def test_db_retrieve_relevant_mock():
    """Verifies vector similarity query is executed."""
    org_id = uuid.uuid4()
    query_embedding = [0.5] * 1536

    mock_row = (
        uuid.uuid4(),  # id
        "topic",  # topic
        "content",  # content
        ["tag1"],  # tags
        "PUBLIC",  # access_level
        [],  # allowed_roles
        1,  # version
        "2025-01-01T00:00:00",  # created_at
        0.95,  # similarity
    )

    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [mock_row]
    session.execute.return_value = mock_result

    results = await db_retrieve_relevant(
        session, org_id, query_embedding, limit=5
    )

    session.execute.assert_awaited_once()
    sql_text = str(session.execute.call_args[0][0])
    assert "embedding <=>" in sql_text
    assert len(results) == 1
    assert results[0]["similarity"] == 0.95
    assert results[0]["topic"] == "topic"


@pytest.mark.asyncio
async def test_db_retrieve_relevant_access_control():
    """Verifies role-based filtering on retrieval."""
    org_id = uuid.uuid4()
    query_embedding = [0.5] * 1536

    # Restricted row that requester cannot access
    restricted_row = (
        uuid.uuid4(), "secret", "classified", ["internal"],
        "ROLE_RESTRICTED", ["admin"], 1, "2025-01-01T00:00:00", 0.9,
    )
    # Public row
    public_row = (
        uuid.uuid4(), "public-info", "hello", ["general"],
        "PUBLIC", [], 1, "2025-01-01T00:00:00", 0.8,
    )

    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [restricted_row, public_row]
    session.execute.return_value = mock_result

    results = await db_retrieve_relevant(
        session, org_id, query_embedding, limit=10, requester_roles=["viewer"]
    )

    # Should filter out the restricted row since "viewer" not in ["admin"]
    assert len(results) == 1
    assert results[0]["topic"] == "public-info"


@pytest.mark.asyncio
async def test_db_invalidate_memory_mock():
    """Verifies UPDATE SQL sets valid_until."""
    session = AsyncMock()
    memory_id = uuid.uuid4()

    await db_invalidate_memory(session, memory_id)

    session.execute.assert_awaited_once()
    sql_text = str(session.execute.call_args[0][0])
    assert "UPDATE memory_records" in sql_text
    assert "valid_until" in sql_text
    params = session.execute.call_args[0][1]
    assert params["id"] == memory_id
