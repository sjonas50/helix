"""Predictive workflow engine — speculative pre-computation.

Adapted from Claude Code's speculative execution system:
- CC uses overlay filesystem at ~/.claude/speculation/<pid>/<speculation_id>/
- We use PostgreSQL savepoints (ACID-safe, distributed) — arch decision #3
- CC speculates one step ahead; we allow configurable depth (default 2)
- CC freely speculates on reads, blocks writes outside working dir
- We freely speculate on read-only integration calls, queue writes
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field

from helix.utils import utcnow

logger = structlog.get_logger()


class SpeculationConfig(BaseModel):
    """Configuration for speculative execution per workflow."""

    enabled: bool = True
    max_depth: int = 2  # CC hard-codes 1
    min_confidence: float = 0.5  # Don't speculate if P(approval) < this
    max_queued_writes: int = 20  # CC uses 20 tool-turn limit


class SpeculativeExecution(BaseModel):
    """A speculative execution branch.

    Claude Code tags these with querySource: "speculation", forkLabel: "speculation".
    We track them as first-class entities for audit trail compliance.
    """

    id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID
    org_id: UUID
    approval_request_id: UUID
    assumed_decision: str = "APPROVED"
    depth: int = 1
    pre_computed_state: dict[str, Any] = Field(default_factory=dict)
    queued_writes: list[dict[str, Any]] = Field(default_factory=list)
    read_only_results: list[dict[str, Any]] = Field(default_factory=list)
    confidence_score: float = 0.0
    token_cost: int = 0
    status: str = "PENDING"  # PENDING | READY | APPLIED | DISCARDED
    created_at: datetime = Field(default_factory=utcnow)
    resolved_at: datetime | None = None


def should_speculate(
    risk_level: str,
    config: SpeculationConfig | None = None,
) -> bool:
    """Determine if speculation should be triggered for a pending approval.

    Scoring: P(approval) × time_saved. LOW risk has high approval probability.
    CRITICAL risk has low probability — don't waste tokens speculatively.
    """
    cfg = config or SpeculationConfig()
    if not cfg.enabled:
        return False

    # Rough confidence heuristic by risk level
    confidence_by_risk = {
        "LOW": 0.95,
        "MEDIUM": 0.75,
        "HIGH": 0.50,
        "CRITICAL": 0.20,
    }
    confidence = confidence_by_risk.get(risk_level, 0.0)
    return confidence >= cfg.min_confidence


def create_speculation(
    workflow_id: UUID,
    org_id: UUID,
    approval_request_id: UUID,
    assumed_decision: str = "APPROVED",
    confidence_score: float = 0.0,
) -> SpeculativeExecution:
    """Create a new speculative execution branch.

    In Claude Code, this creates an overlay filesystem.
    In Helix, this starts a DB savepoint (actual savepoint management
    happens at the repository layer).
    """
    spec = SpeculativeExecution(
        workflow_id=workflow_id,
        org_id=org_id,
        approval_request_id=approval_request_id,
        assumed_decision=assumed_decision,
        confidence_score=confidence_score,
    )

    logger.info(
        "speculation.created",
        speculation_id=str(spec.id),
        workflow_id=str(workflow_id),
        assumed_decision=assumed_decision,
        confidence=confidence_score,
    )

    return spec


def resolve_speculation(
    speculation: SpeculativeExecution,
    actual_decision: str,
) -> str:
    """Resolve a speculation based on the actual approval decision.

    If decision matches assumption:
      → RELEASE SAVEPOINT, apply queued writes, status = APPLIED
    If decision doesn't match:
      → ROLLBACK TO SAVEPOINT, discard, status = DISCARDED

    Returns the action taken: "applied" or "discarded".
    """
    if actual_decision == speculation.assumed_decision:
        speculation.status = "APPLIED"
        speculation.resolved_at = utcnow()
        logger.info(
            "speculation.applied",
            speculation_id=str(speculation.id),
            queued_writes_count=len(speculation.queued_writes),
        )
        return "applied"
    else:
        speculation.status = "DISCARDED"
        speculation.resolved_at = utcnow()
        logger.info(
            "speculation.discarded",
            speculation_id=str(speculation.id),
            assumed=speculation.assumed_decision,
            actual=actual_decision,
        )
        return "discarded"


def is_read_only_tool(tool_name: str) -> bool:
    """Check if an integration tool is safe for speculative execution.

    Claude Code freely allows: Read, Glob, Grep, ToolSearch, LSP, TaskGet, TaskList.
    We allow read-only integration calls (GET requests, queries) during speculation.
    Write operations (mutations, POSTs) are queued and executed only on confirmation.
    """
    read_only_prefixes = {
        "get_", "list_", "search_", "read_", "query_", "fetch_", "describe_",
    }
    return any(tool_name.lower().startswith(prefix) for prefix in read_only_prefixes)
