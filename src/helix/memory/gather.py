"""Extract signals from memory records using Haiku for Dream Cycle Gather phase.

Uses Claude Haiku to analyze recent memory records and extract:
- User corrections (things users explicitly told agents to change)
- Decisions (architectural or process decisions made)
- Recurring themes (patterns that appear across multiple records)
"""

from datetime import UTC, datetime
from uuid import uuid4

import structlog
from pydantic import BaseModel, Field

from helix.memory.dream import SessionSignal

logger = structlog.get_logger()


class ExtractedSignals(BaseModel):
    """Structured output from LLM signal extraction."""

    corrections: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)


async def extract_signals_from_memories(
    recent_memories: list[dict],
    model: str = "claude-haiku-4-5",
) -> list[SessionSignal]:
    """Use Haiku to extract signals from recent memory records.

    Takes a list of memory record dicts (topic, content) and returns
    SessionSignal objects for the Dream Cycle Consolidate phase.

    Args:
        recent_memories: List of dicts with topic, content, source_system keys.
        model: LLM model to use for extraction.

    Returns:
        List of SessionSignal objects extracted from the memories.
    """
    if not recent_memories:
        return []

    # Build a summary of recent memories for the LLM
    memory_text = "\n\n".join(
        f"[{m.get('source_system', 'unknown')}] {m.get('topic', '')}: "
        f"{m.get('content', '')[:500]}"
        for m in recent_memories[:50]  # Cap at 50 to control token cost
    )

    prompt = f"""Analyze these recent records from an enterprise knowledge base. Extract:

1. CORRECTIONS: Things that were explicitly corrected or updated (e.g., "the correct process is X, not Y")
2. DECISIONS: Important decisions made (e.g., "decided to use PostgreSQL instead of MongoDB")
3. THEMES: Recurring patterns or topics that appear across multiple records

Records:
{memory_text}

Return only signals that are genuinely important for institutional memory. Skip trivial items."""

    try:
        from helix.llm.structured import structured_call

        result = await structured_call(prompt, ExtractedSignals, model=model)
    except Exception as e:
        logger.error("gather.llm_failed", error=str(e))
        # Graceful degradation: return empty signals instead of failing the dream cycle
        return []

    signals: list[SessionSignal] = []
    session_id = uuid4()  # Group all signals from this extraction

    for correction in result.corrections:
        signals.append(
            SessionSignal(
                session_id=session_id,
                signal_type="correction",
                content=correction,
                confidence=0.8,
                timestamp=datetime.now(tz=UTC),
            )
        )

    for decision in result.decisions:
        signals.append(
            SessionSignal(
                session_id=session_id,
                signal_type="decision",
                content=decision,
                confidence=0.9,
                timestamp=datetime.now(tz=UTC),
            )
        )

    for theme in result.themes:
        signals.append(
            SessionSignal(
                session_id=session_id,
                signal_type="theme",
                content=theme,
                confidence=0.7,
                timestamp=datetime.now(tz=UTC),
            )
        )

    logger.info(
        "gather.extracted",
        corrections=len(result.corrections),
        decisions=len(result.decisions),
        themes=len(result.themes),
    )
    return signals
