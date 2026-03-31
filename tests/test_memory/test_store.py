"""Tests for memory store operations."""

import uuid

from helix.memory.store import (
    MemoryEntry,
    can_access_memory,
    create_memory,
    invalidate_memory,
    merge_memories,
)


class TestCreateMemory:
    def test_create_basic(self) -> None:
        entry = create_memory(
            org_id=uuid.uuid4(),
            topic="onboarding",
            content="Step 1: Create account in Salesforce",
        )
        assert entry.topic == "onboarding"
        assert entry.access_level == "PUBLIC"
        assert entry.version == 1
        assert entry.valid_until is None

    def test_create_with_access_control(self) -> None:
        entry = create_memory(
            org_id=uuid.uuid4(),
            topic="financials",
            content="Q1 revenue: $10M",
            access_level="CONFIDENTIAL",
            allowed_roles=["admin", "finance"],
        )
        assert entry.access_level == "CONFIDENTIAL"
        assert "admin" in entry.allowed_roles


class TestAccessControl:
    def _make_entry(self, access_level: str, allowed_roles: list[str] | None = None) -> MemoryEntry:
        return MemoryEntry(
            org_id=uuid.uuid4(),
            topic="test",
            content="test content",
            access_level=access_level,
            allowed_roles=allowed_roles or [],
        )

    def test_public_accessible_by_anyone(self) -> None:
        entry = self._make_entry("PUBLIC")
        assert can_access_memory(entry, ["viewer"])
        assert can_access_memory(entry, [])

    def test_role_restricted_requires_matching_role(self) -> None:
        entry = self._make_entry("ROLE_RESTRICTED", ["admin", "operator"])
        assert can_access_memory(entry, ["admin"])
        assert can_access_memory(entry, ["operator"])
        assert not can_access_memory(entry, ["viewer"])
        assert not can_access_memory(entry, [])

    def test_confidential_requires_matching_role(self) -> None:
        entry = self._make_entry("CONFIDENTIAL", ["admin"])
        assert can_access_memory(entry, ["admin"])
        assert not can_access_memory(entry, ["operator"])


class TestInvalidateMemory:
    def test_invalidate_sets_valid_until(self) -> None:
        entry = create_memory(
            org_id=uuid.uuid4(),
            topic="test",
            content="test",
        )
        assert entry.valid_until is None
        invalidate_memory(entry)
        assert entry.valid_until is not None


class TestMergeMemories:
    def test_merge_creates_new_version(self) -> None:
        original = create_memory(
            org_id=uuid.uuid4(),
            topic="process",
            content="Original process",
            tags=["ops"],
        )
        merged = merge_memories(original, "Updated process with new steps", ["updated"])
        assert merged.version == 2
        assert merged.topic == "process"
        assert "ops" in merged.tags
        assert "updated" in merged.tags
        # Original should be invalidated
        assert original.valid_until is not None

    def test_merge_preserves_org_scope(self) -> None:
        org_id = uuid.uuid4()
        original = create_memory(org_id=org_id, topic="t", content="c")
        merged = merge_memories(original, "new content")
        assert merged.org_id == org_id
