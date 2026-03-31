"""Token usage persistence for billing attribution.

Records every LLM call to the token_usage_events table so orgs can
track spend by workflow, agent, model, and cost center.
"""

from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from helix.llm.gateway import TokenUsageTracker

logger = structlog.get_logger()


async def record_usage(session: AsyncSession, tracker: TokenUsageTracker) -> None:
    """Persist token usage to token_usage_events table.

    Args:
        session: Async SQLAlchemy session for the write.
        tracker: Populated token usage tracker from an LLM call.
    """
    params: dict[str, object] = {}
    for field_name in tracker.model_fields:
        if field_name == "timestamp":
            continue
        value = getattr(tracker, field_name)
        # Convert UUID fields to str for database compatibility
        if isinstance(value, UUID):
            value = str(value)
        params[field_name] = value

    await session.execute(
        text(
            """INSERT INTO token_usage_events
            (org_id, workflow_id, agent_id, user_id, model_id, provider,
             input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
             cost_usd, cost_center, fallback_occurred, fallback_reason)
            VALUES (:org_id, :workflow_id, :agent_id, :user_id, :model_id, :provider,
                    :input_tokens, :output_tokens, :cache_read_tokens, :cache_write_tokens,
                    :cost_usd, :cost_center, :fallback_occurred, :fallback_reason)"""
        ),
        params,
    )

    logger.info(
        "metering.usage_recorded",
        org_id=str(tracker.org_id),
        model_id=tracker.model_id,
        input_tokens=tracker.input_tokens,
        output_tokens=tracker.output_tokens,
        cost_usd=tracker.cost_usd,
    )
