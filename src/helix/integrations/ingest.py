"""Webhook data ingest pipeline: normalize -> hash -> embed -> upsert.

Takes raw webhook payloads from Slack, Jira, GitHub, etc. and
ingests them into memory_records for ambient agent awareness.
"""

import hashlib
from uuid import UUID, uuid4

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from helix.memory.embeddings import embed_text

logger = structlog.get_logger()


def compute_content_hash(content: str) -> str:
    """SHA-256 hash for content dedup."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def normalize_webhook_payload(
    provider: str, event_type: str, payload: dict
) -> dict | None:
    """Extract structured content from a webhook payload.

    Returns dict with: topic, content, source_id, source_url, entity_type
    or None if the event shouldn't be indexed.
    """
    normalizers = {
        "slack": _normalize_slack,
        "jira": _normalize_jira,
        "github": _normalize_github,
    }
    normalizer = normalizers.get(provider)
    if not normalizer:
        logger.warning("ingest.no_normalizer", provider=provider)
        return None
    return normalizer(event_type, payload)


def _normalize_slack(event_type: str, payload: dict) -> dict | None:
    """Normalize Slack webhook to memory content."""
    if event_type not in ("message_posted", "message"):
        return None
    event = payload.get("event", payload)
    text_content = event.get("text", "")
    channel = event.get("channel", "unknown")
    user = event.get("user", "unknown")
    ts = event.get("ts", "")
    if not text_content or len(text_content) < 10:
        return None  # Skip trivial messages
    return {
        "topic": f"slack:{channel}",
        "content": f"[Slack #{channel}] {user}: {text_content}",
        "source_id": f"{channel}:{ts}",
        "source_url": f"https://slack.com/archives/{channel}/p{ts.replace('.', '')}",
        "entity_type": "message",
    }


def _normalize_jira(event_type: str, payload: dict) -> dict | None:
    """Normalize Jira webhook to memory content."""
    issue = payload.get("issue", {})
    fields = issue.get("fields", {})
    key = issue.get("key", "")
    summary = fields.get("summary", "")
    description = fields.get("description", "") or ""
    if not key:
        return None
    # Truncate description to first 2000 chars
    content = f"[Jira {key}] {summary}"
    if description:
        content += f"\n{description[:2000]}"
    return {
        "topic": f"jira:{key}",
        "content": content,
        "source_id": key,
        "source_url": issue.get("self"),
        "entity_type": "issue",
    }


def _normalize_github(event_type: str, payload: dict) -> dict | None:
    """Normalize GitHub webhook to memory content."""
    if event_type == "issue_opened":
        issue = payload.get("issue", {})
        return {
            "topic": f"github:issue:{issue.get('number', '')}",
            "content": (
                f"[GitHub Issue #{issue.get('number', '')}] {issue.get('title', '')}"
                f"\n{(issue.get('body', '') or '')[:2000]}"
            ),
            "source_id": str(issue.get("id", "")),
            "source_url": issue.get("html_url"),
            "entity_type": "issue",
        }
    if event_type == "pull_request_opened":
        pr = payload.get("pull_request", {})
        return {
            "topic": f"github:pr:{pr.get('number', '')}",
            "content": (
                f"[GitHub PR #{pr.get('number', '')}] {pr.get('title', '')}"
                f"\n{(pr.get('body', '') or '')[:2000]}"
            ),
            "source_id": str(pr.get("id", "")),
            "source_url": pr.get("html_url"),
            "entity_type": "pull_request",
        }
    return None


async def ingest_webhook_to_memory(
    session: AsyncSession,
    org_id: UUID,
    provider: str,
    event_type: str,
    payload: dict,
) -> str | None:
    """Full pipeline: normalize -> hash -> check dedup -> embed -> upsert.

    Returns the memory record ID if ingested, None if skipped (dedup or unsupported).
    """
    normalized = normalize_webhook_payload(provider, event_type, payload)
    if normalized is None:
        return None

    content = normalized["content"]
    content_hash = compute_content_hash(content)

    # Check if content already exists (dedup by hash)
    existing = await session.execute(
        text(
            "SELECT id FROM memory_records"
            " WHERE org_id = :org_id AND content_hash = :hash"
            " AND valid_until IS NULL"
        ),
        {"org_id": org_id, "hash": content_hash},
    )
    if existing.fetchone():
        logger.debug(
            "ingest.dedup_skip",
            provider=provider,
            source_id=normalized["source_id"],
        )
        return None

    # Generate embedding
    embedding = await embed_text(content)

    # Upsert (insert or update by source key)
    record_id = uuid4()

    # Check for zero-vector (no API key in dev) — store None instead
    embedding_value = (
        str(embedding) if embedding and embedding[0] != 0.0 else None
    )

    await session.execute(
        text("""
            INSERT INTO memory_records
                (id, org_id, topic, content, content_hash, source_system, source_id, source_url,
                 tags, access_level, embedding)
            VALUES
                (:id, :org_id, :topic, :content, :hash, :source_system, :source_id, :source_url,
                 :tags, 'PUBLIC', :embedding::vector)
            ON CONFLICT (org_id, source_system, source_id)
            DO UPDATE SET
                content = EXCLUDED.content,
                content_hash = EXCLUDED.content_hash,
                embedding = EXCLUDED.embedding,
                valid_from = now()
        """),
        {
            "id": record_id,
            "org_id": org_id,
            "topic": normalized["topic"],
            "content": content,
            "hash": content_hash,
            "source_system": provider,
            "source_id": normalized["source_id"],
            "source_url": normalized.get("source_url"),
            "tags": [provider, normalized.get("entity_type", "")],
            "embedding": embedding_value,
        },
    )
    await session.commit()

    logger.info(
        "ingest.stored",
        provider=provider,
        source_id=normalized["source_id"],
        org_id=str(org_id),
    )
    return str(record_id)
