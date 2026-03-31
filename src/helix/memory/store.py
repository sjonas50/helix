"""Memory store with semantic retrieval via pgvector.

Adapted from Claude Code's memory system:
- CC stores YAML files at ~/.claude/projects/<slug>/memory/ with frontmatter
- CC's Sonnet-powered selector reads up to 5 files sequentially
- We use PostgreSQL + pgvector: one DB round-trip for semantic similarity
  (arch decision #4: O(log N) vs O(N), catches concept matches)
- Org-scoped memory with access control per role
"""

from datetime import datetime
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class MemoryEntry(BaseModel):
    """A memory record with metadata.

    Claude Code uses YAML frontmatter with name, description, type fields.
    We use structured fields with access control and versioning.
    """

    id: UUID = Field(default_factory=uuid4)
    org_id: UUID
    user_id: UUID | None = None  # None = org-level memory
    agent_id: UUID | None = None
    topic: str
    content: str
    tags: list[str] = Field(default_factory=list)
    access_level: str = "PUBLIC"  # PUBLIC | ROLE_RESTRICTED | CONFIDENTIAL
    allowed_roles: list[str] = Field(default_factory=list)
    embedding: list[float] | None = None  # 1536-dim vector
    version: int = 1
    valid_from: datetime = Field(default_factory=datetime.now)
    valid_until: datetime | None = None
    source_session_ids: list[UUID] = Field(default_factory=list)


class MemoryQueryResult(BaseModel):
    """Result from a semantic memory query."""

    entry: MemoryEntry
    similarity_score: float  # cosine similarity, 0.0 to 1.0


def create_memory(
    org_id: UUID,
    topic: str,
    content: str,
    tags: list[str] | None = None,
    access_level: str = "PUBLIC",
    allowed_roles: list[str] | None = None,
    user_id: UUID | None = None,
    agent_id: UUID | None = None,
    source_session_ids: list[UUID] | None = None,
) -> MemoryEntry:
    """Create a new memory record.

    Claude Code creates files with Write tool. We create DB records.
    """
    entry = MemoryEntry(
        org_id=org_id,
        user_id=user_id,
        agent_id=agent_id,
        topic=topic,
        content=content,
        tags=tags or [],
        access_level=access_level,
        allowed_roles=allowed_roles or [],
        source_session_ids=source_session_ids or [],
    )

    logger.info(
        "memory.created",
        memory_id=str(entry.id),
        org_id=str(org_id),
        topic=topic,
        access_level=access_level,
    )

    return entry


def can_access_memory(
    entry: MemoryEntry,
    requester_roles: list[str],
) -> bool:
    """Check if a requester can access a memory record.

    Claude Code has no memory access control (single-user).
    Helix enforces per-role access on every memory retrieval.
    """
    if entry.access_level == "PUBLIC":
        return True
    if entry.access_level in ("ROLE_RESTRICTED", "CONFIDENTIAL"):
        return bool(set(requester_roles) & set(entry.allowed_roles))
    return False


def invalidate_memory(entry: MemoryEntry) -> MemoryEntry:
    """Mark a memory record as no longer valid.

    Claude Code's Prune phase deletes files. We soft-delete via valid_until
    to preserve the audit trail and support time-travel queries.
    """
    entry.valid_until = datetime.now()
    logger.info(
        "memory.invalidated",
        memory_id=str(entry.id),
        topic=entry.topic,
    )
    return entry


def merge_memories(
    existing: MemoryEntry,
    new_content: str,
    new_tags: list[str] | None = None,
) -> MemoryEntry:
    """Create a new version of an existing memory with merged content.

    Claude Code's Consolidate phase merges overlapping entries.
    We create a new version (append-only) rather than updating in place.
    """
    merged = MemoryEntry(
        org_id=existing.org_id,
        user_id=existing.user_id,
        agent_id=existing.agent_id,
        topic=existing.topic,
        content=new_content,
        tags=list(set(existing.tags + (new_tags or []))),
        access_level=existing.access_level,
        allowed_roles=existing.allowed_roles,
        version=existing.version + 1,
        source_session_ids=existing.source_session_ids,
    )

    # Invalidate old version
    invalidate_memory(existing)

    logger.info(
        "memory.merged",
        old_id=str(existing.id),
        new_id=str(merged.id),
        topic=existing.topic,
        new_version=merged.version,
    )

    return merged
