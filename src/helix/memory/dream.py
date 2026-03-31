"""Dream Cycle — 4-phase memory consolidation.

Directly adapted from Claude Code's autoDream system:
- Phase 1 (Orient): Scan existing memory index
- Phase 2 (Gather): Extract signals from session transcripts
- Phase 3 (Consolidate): Merge, deduplicate, strip PII, embed
- Phase 4 (Prune): Enforce limits, invalidate stale records

Key improvements over Claude Code:
- Org-scoped (not per-user)
- PostgreSQL storage (not file-based YAML)
- Configurable triggers per org (not global 24hr/5 sessions)
- PII stripping before embedding (GDPR compliance)
- Runs as Celery task (not forked subagent)

Claude Code's three-gate trigger: 24hr + 5 sessions + lock
Ours: configurable min_hours + min_sessions + Redis distributed lock
"""

from datetime import datetime
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field

from helix.memory.pii import strip_pii
from helix.memory.store import MemoryEntry, create_memory, invalidate_memory

logger = structlog.get_logger()


class DreamPhase:
    """Dream cycle phase names matching Claude Code's autoDream."""

    ORIENT = "ORIENT"
    GATHER = "GATHER"
    CONSOLIDATE = "CONSOLIDATE"
    PRUNE = "PRUNE"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class DreamTriggerConfig(BaseModel):
    """Trigger configuration per org.

    Claude Code hard-codes: 24hr + 5 sessions + lock.
    We make all three configurable per org via DreamConfig table.
    """

    min_hours_between_runs: int = 24
    min_sessions_between_runs: int = 5
    max_memory_records: int = 500
    max_bytes_per_record: int = 8192
    pii_strip_enabled: bool = True
    consolidation_model: str = "claude-sonnet-4-6"


class DreamRunResult(BaseModel):
    """Result of a Dream Cycle execution."""

    id: UUID = Field(default_factory=uuid4)
    org_id: UUID
    triggered_by: str  # schedule | manual | api
    phase: str = DreamPhase.ORIENT
    sessions_processed: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_pruned: int = 0
    tokens_used: int = 0
    errors: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None


class SessionSignal(BaseModel):
    """A signal extracted from a session transcript during the Gather phase.

    Claude Code's Gather phase targets: user corrections, explicit save
    commands, recurring themes, significant architectural decisions.
    """

    session_id: UUID
    signal_type: str  # correction | decision | theme | instruction
    content: str
    confidence: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)


def should_trigger_dream(
    last_run_at: datetime | None,
    sessions_since_last_run: int,
    config: DreamTriggerConfig | None = None,
) -> bool:
    """Check if all three gates pass for triggering a Dream Cycle.

    Claude Code's three-gate system:
    1. 24+ hours since last dream run
    2. 5+ sessions since last dream
    3. Consolidation lock acquisition (handled at caller level)

    We check gates 1 and 2 here; gate 3 (distributed lock) is at the
    Celery task level using Redis SETNX.
    """
    cfg = config or DreamTriggerConfig()

    # Gate 1: Time since last run
    if last_run_at is not None:
        hours_since = (datetime.now() - last_run_at).total_seconds() / 3600
        if hours_since < cfg.min_hours_between_runs:
            return False

    # Gate 2: Session count
    return not sessions_since_last_run < cfg.min_sessions_between_runs


def orient_phase(
    existing_memories: list[MemoryEntry],
) -> dict[str, list[MemoryEntry]]:
    """Phase 1 — Orient: Scan existing memory and build topic index.

    Claude Code: `ls` the memory directory, read MEMORY.md index,
    skim existing topic files to avoid creating duplicates.

    We: Query memory_records table grouped by topic.
    """
    topic_index: dict[str, list[MemoryEntry]] = {}
    for entry in existing_memories:
        if entry.valid_until is None:  # Only active records
            topic_index.setdefault(entry.topic, []).append(entry)

    logger.info(
        "dream.orient",
        topic_count=len(topic_index),
        total_records=sum(len(v) for v in topic_index.values()),
    )

    return topic_index


def gather_phase(
    signals: list[SessionSignal],
    min_confidence: float = 0.3,
) -> list[SessionSignal]:
    """Phase 2 — Gather Signal: Filter and rank extracted signals.

    Claude Code: Targeted grep of session transcripts (JSONL) for
    corrections, save commands, recurring themes, decisions.
    Narrow approach conserves tokens.

    We: Process pre-extracted signals, filter by confidence.
    """
    filtered = [s for s in signals if s.confidence >= min_confidence]

    logger.info(
        "dream.gather",
        total_signals=len(signals),
        filtered_signals=len(filtered),
        signal_types={s.signal_type for s in filtered},
    )

    return filtered


def consolidate_phase(
    topic_index: dict[str, list[MemoryEntry]],
    signals: list[SessionSignal],
    org_id: UUID,
    config: DreamTriggerConfig | None = None,
) -> tuple[list[MemoryEntry], list[MemoryEntry]]:
    """Phase 3 — Consolidate: Merge, deduplicate, strip PII, create new records.

    Claude Code: Write/update memory files. Convert relative dates to absolute.
    Remove contradicted facts. Merge overlapping entries. Prune stale references.

    We: Create new memory versions. Strip PII before embedding.
    Return (new_records, invalidated_records).
    """
    cfg = config or DreamTriggerConfig()
    new_records: list[MemoryEntry] = []
    invalidated: list[MemoryEntry] = []

    # Group signals by topic (using signal_type as rough topic)
    signal_by_topic: dict[str, list[SessionSignal]] = {}
    for signal in signals:
        signal_by_topic.setdefault(signal.signal_type, []).append(signal)

    for signal_type, type_signals in signal_by_topic.items():
        # Combine signal contents
        combined_content = "\n".join(s.content for s in type_signals)

        # Strip PII before storing
        cleaned_content, redactions = strip_pii(combined_content, cfg.pii_strip_enabled)

        # Enforce max bytes per record
        if len(cleaned_content.encode()) > cfg.max_bytes_per_record:
            cleaned_content = cleaned_content[: cfg.max_bytes_per_record]

        # Check if topic already exists
        existing = topic_index.get(signal_type, [])
        if existing:
            # Invalidate old records in this topic
            for old in existing:
                invalidate_memory(old)
                invalidated.append(old)

        # Create new consolidated record
        session_ids = [s.session_id for s in type_signals]
        new_record = create_memory(
            org_id=org_id,
            topic=signal_type,
            content=cleaned_content,
            tags=[signal_type],
            source_session_ids=session_ids,
        )
        new_records.append(new_record)

    logger.info(
        "dream.consolidate",
        new_records=len(new_records),
        invalidated=len(invalidated),
    )

    return new_records, invalidated


def prune_phase(
    all_records: list[MemoryEntry],
    max_records: int = 500,
) -> list[MemoryEntry]:
    """Phase 4 — Prune: Enforce record limits, remove stale entries.

    Claude Code: Maintain MEMORY.md under 200 lines / 25KB cap.
    Remove obsolete pointers, reorder by relevance.

    We: Enforce max_memory_records per org. Prune oldest records
    when limit exceeded. Return list of pruned records.
    """
    active_records = [r for r in all_records if r.valid_until is None]

    if len(active_records) <= max_records:
        logger.info("dream.prune", pruned=0, active=len(active_records))
        return []

    # Sort by creation date, prune oldest
    sorted_records = sorted(active_records, key=lambda r: r.valid_from)
    to_prune = sorted_records[: len(active_records) - max_records]

    for record in to_prune:
        invalidate_memory(record)

    logger.info(
        "dream.prune",
        pruned=len(to_prune),
        remaining=max_records,
    )

    return to_prune


def run_dream_cycle(
    org_id: UUID,
    existing_memories: list[MemoryEntry],
    session_signals: list[SessionSignal],
    config: DreamTriggerConfig | None = None,
    triggered_by: str = "schedule",
) -> DreamRunResult:
    """Execute the full 4-phase Dream Cycle.

    This is the top-level orchestrator. In production, this is called
    from a Celery task after acquiring the Redis distributed lock.
    """
    cfg = config or DreamTriggerConfig()
    result = DreamRunResult(org_id=org_id, triggered_by=triggered_by)

    try:
        # Phase 1: Orient
        result.phase = DreamPhase.ORIENT
        topic_index = orient_phase(existing_memories)

        # Phase 2: Gather
        result.phase = DreamPhase.GATHER
        filtered_signals = gather_phase(session_signals)
        result.sessions_processed = len({s.session_id for s in filtered_signals})

        # Phase 3: Consolidate
        result.phase = DreamPhase.CONSOLIDATE
        new_records, invalidated = consolidate_phase(
            topic_index, filtered_signals, org_id, cfg
        )
        result.records_created = len(new_records)
        result.records_updated = len(invalidated)

        # Phase 4: Prune
        result.phase = DreamPhase.PRUNE
        all_records = existing_memories + new_records
        pruned = prune_phase(all_records, cfg.max_memory_records)
        result.records_pruned = len(pruned)

        # Complete
        result.phase = DreamPhase.COMPLETE
        result.completed_at = datetime.now()

        logger.info(
            "dream.complete",
            org_id=str(org_id),
            sessions=result.sessions_processed,
            created=result.records_created,
            pruned=result.records_pruned,
        )

    except Exception as e:
        result.phase = DreamPhase.FAILED
        result.errors.append(str(e))
        result.completed_at = datetime.now()
        logger.error("dream.failed", org_id=str(org_id), error=str(e))

    return result
