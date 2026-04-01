"""Memory store with semantic retrieval via pgvector.

Adapted from Claude Code's memory system:
- CC stores YAML files at ~/.claude/projects/<slug>/memory/ with frontmatter
- CC's Sonnet-powered selector reads up to 5 files sequentially
- We use PostgreSQL + pgvector: one DB round-trip for semantic similarity
  (arch decision #4: O(log N) vs O(N), catches concept matches)
- Org-scoped memory with access control per role
"""

import uuid
from datetime import datetime
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from helix.utils import utcnow

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
    content_hash: str | None = None  # SHA-256 for dedup
    source_system: str | None = None  # slack, salesforce, jira, etc.
    source_id: str | None = None  # External record ID
    source_url: str | None = None  # Link back to original
    version: int = 1
    valid_from: datetime = Field(default_factory=utcnow)
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
    entry.valid_until = utcnow()
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


async def db_create_memory(
    session: AsyncSession,
    entry: MemoryEntry,
    embedding: list[float] | None = None,
) -> uuid.UUID:
    """Insert a memory record into the database with optional embedding."""
    await session.execute(
        text(
            """INSERT INTO memory_records
            (id, org_id, user_id, agent_id, topic, content, tags, access_level,
             allowed_roles, source_session_ids, version, embedding)
            VALUES (:id, :org_id, :user_id, :agent_id, :topic, :content,
                    :tags, :access_level, :allowed_roles, :source_session_ids, :version,
                    :embedding::vector)"""
        ),
        {
            "id": entry.id,
            "org_id": entry.org_id,
            "user_id": entry.user_id,
            "agent_id": entry.agent_id,
            "topic": entry.topic,
            "content": entry.content,
            "tags": entry.tags,
            "access_level": entry.access_level,
            "allowed_roles": entry.allowed_roles,
            "source_session_ids": (
                [str(s) for s in entry.source_session_ids]
                if entry.source_session_ids
                else []
            ),
            "version": entry.version,
            "embedding": str(embedding) if embedding else None,
        },
    )
    logger.info("memory.db_created", memory_id=str(entry.id), topic=entry.topic)
    return entry.id


async def db_retrieve_relevant(
    session: AsyncSession,
    org_id: uuid.UUID,
    query_embedding: list[float],
    limit: int = 10,
    requester_roles: list[str] | None = None,
) -> list[dict]:
    """Semantic search via pgvector cosine similarity."""
    embedding_str = str(query_embedding)

    sql = """
        SELECT id, topic, content, tags, access_level, allowed_roles, version, created_at,
               1 - (embedding <=> :embedding::vector) AS similarity
        FROM memory_records
        WHERE org_id = :org_id AND valid_until IS NULL AND embedding IS NOT NULL
        ORDER BY embedding <=> :embedding::vector
        LIMIT :limit
    """
    result = await session.execute(
        text(sql),
        {"org_id": org_id, "embedding": embedding_str, "limit": limit},
    )
    rows = result.fetchall()

    results = []
    for row in rows:
        record = {
            "id": row[0],
            "topic": row[1],
            "content": row[2],
            "tags": row[3],
            "access_level": row[4],
            "allowed_roles": row[5],
            "version": row[6],
            "created_at": row[7],
            "similarity": float(row[8]),
        }
        # Access control filter
        if (
            requester_roles
            and record["access_level"] != "PUBLIC"
            and not set(requester_roles or []) & set(record["allowed_roles"] or [])
        ):
            continue
        results.append(record)

    return results


async def db_invalidate_memory(
    session: AsyncSession, memory_id: uuid.UUID
) -> None:
    """Soft-delete a memory record by setting valid_until."""
    await session.execute(
        text("UPDATE memory_records SET valid_until = now() WHERE id = :id"),
        {"id": memory_id},
    )
    logger.info("memory.db_invalidated", memory_id=str(memory_id))
