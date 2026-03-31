"""Context compaction engine — 3-layer compression.

Directly adapted from Claude Code's QueryEngine compaction system:
- Layer 1 (Micro): Tool outputs > threshold offloaded to storage
- Layer 2 (Auto): Fires at 83.5% context usage, produces structured summary
- Layer 3 (Cross-session): Unique to Helix — resume interrupted workflows

Claude Code's thresholds:
- Auto-compaction at ~83.5% of 200K tokens (~167K)
- Reserves 33K tokens (16.5%) for output headroom
- Structured summary: intent, decisions, affected files, errors, pending, next steps
"""

from typing import Any
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class CompactionConfig(BaseModel):
    """Compaction configuration per org.

    Inherits Claude Code's 83.5% threshold as default.
    """

    auto_compaction_pct: float = 83.5  # CC's default
    max_context_tokens: int = 200000  # CC's default
    micro_compaction_threshold_bytes: int = 8192  # 8KB
    enable_cross_session: bool = True


class CompactionSummary(BaseModel):
    """Structured summary produced by auto-compaction.

    Claude Code produces: intent, decisions, affected files, errors,
    pending tasks, next steps. Continuation message injected post-compaction.
    """

    id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID
    agent_id: UUID
    intent: str = ""
    decisions: list[str] = Field(default_factory=list)
    integration_actions_taken: list[dict[str, Any]] = Field(default_factory=list)
    open_approvals: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    tokens_before: int = 0
    tokens_after: int = 0
    context_pct_at_trigger: float = 0.0


def should_auto_compact(
    current_tokens: int,
    config: CompactionConfig | None = None,
) -> bool:
    """Check if auto-compaction should fire.

    Claude Code: fires at ~83.5% context usage (~167K of 200K tokens).
    Controllable via CLAUDE_AUTOCOMPACT_PCT_OVERRIDE env var.
    """
    cfg = config or CompactionConfig()
    threshold = cfg.max_context_tokens * (cfg.auto_compaction_pct / 100)
    return current_tokens >= threshold


def should_micro_compact(
    output_size_bytes: int,
    config: CompactionConfig | None = None,
) -> bool:
    """Check if a tool output should be micro-compacted (offloaded to storage).

    Claude Code: bulky tool outputs offloaded to disk early; model sees
    references, not data. Cache policy controls inline retention.
    """
    cfg = config or CompactionConfig()
    return output_size_bytes > cfg.micro_compaction_threshold_bytes


def create_micro_compaction_reference(
    tool_name: str,
    output_size_bytes: int,
    storage_key: str,
) -> dict[str, Any]:
    """Create a reference pointer for a micro-compacted tool output.

    The agent sees this reference instead of the full output.
    """
    return {
        "type": "micro_compaction_reference",
        "tool_name": tool_name,
        "output_size_bytes": output_size_bytes,
        "storage_key": storage_key,
        "note": f"Full output ({output_size_bytes:,} bytes) stored externally. "
        f"Use storage_key to retrieve if needed.",
    }


def estimate_tokens(text: str) -> int:
    """Rough token estimation.

    ~4 characters per token for English text.
    Good enough for compaction threshold decisions.
    """
    return len(text) // 4


def calculate_output_headroom(config: CompactionConfig | None = None) -> int:
    """Calculate reserved output headroom.

    Claude Code reserves 33K tokens (16.5%) for output headroom.
    We follow the same ratio.
    """
    cfg = config or CompactionConfig()
    headroom_pct = 100 - cfg.auto_compaction_pct
    return int(cfg.max_context_tokens * (headroom_pct / 100))
