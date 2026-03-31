"""Workflow state model for the LangGraph orchestration engine.

Adapted from Claude Code's Coordinator Mode FSM. Key improvements:
- Multi-tenant: every state carries org_id
- AWAITING_APPROVAL is a first-class FSM state (not a side-channel)
- Speculation cache for predictive pre-computation
- Token usage tracking per workflow
"""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowPhase(StrEnum):
    """Workflow lifecycle phases.

    Claude Code uses: research → synthesis → implementation → verification.
    We generalize to: PLANNING → EXECUTING → AWAITING_APPROVAL → VERIFYING → COMPLETE/FAILED.
    """

    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    VERIFYING = "VERIFYING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class AgentRole(StrEnum):
    """Agent roles within a workflow."""

    COORDINATOR = "coordinator"
    RESEARCHER = "researcher"
    IMPLEMENTER = "implementer"
    VERIFIER = "verifier"


class AgentMessage(BaseModel):
    """Message passed between agents via the IPC bus.

    Claude Code uses file-based IPC at ~/.claude/teams/. We use
    PostgreSQL + Redis pub/sub for distributed, durable delivery.
    """

    sender_id: UUID
    recipient_id: UUID | None = None  # None = broadcast
    message_type: str
    payload: dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)


class ApprovalContext(BaseModel):
    """Pending approval request context.

    Claude Code's approval is binary (approve/deny). We add:
    - risk_level for routing to correct approver
    - escalation tracking
    - SLA deadline
    """

    approval_id: UUID
    action_description: str
    risk_level: str  # LOW | MEDIUM | HIGH | CRITICAL
    integration_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    sla_deadline: datetime | None = None
    escalated: bool = False


class TokenUsage(BaseModel):
    """Token usage tracking per workflow."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cost_usd: float = 0.0


class SpeculativeResult(BaseModel):
    """Pre-computed result from speculative execution.

    Claude Code uses overlay filesystem. We use DB savepoints (arch decision #3).
    """

    speculation_id: UUID
    assumed_decision: str  # APPROVED | REJECTED
    pre_computed_state: dict[str, Any] = Field(default_factory=dict)
    queued_writes: list[dict[str, Any]] = Field(default_factory=list)
    confidence_score: float = 0.0


class WorkflowState(BaseModel):
    """Complete workflow state for LangGraph.

    This is the typed state that flows through the LangGraph StateGraph.
    Persisted via LangGraph checkpointing → maps to our workflows table.
    """

    workflow_id: UUID
    org_id: UUID
    phase: WorkflowPhase = WorkflowPhase.PLANNING
    coordinator_agent_id: UUID | None = None
    worker_agent_ids: list[UUID] = Field(default_factory=list)
    messages: list[AgentMessage] = Field(default_factory=list)
    pending_approval: ApprovalContext | None = None
    speculation_cache: dict[str, SpeculativeResult] = Field(default_factory=dict)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def is_terminal(self) -> bool:
        """Check if workflow is in a terminal state."""
        return self.phase in (WorkflowPhase.COMPLETE, WorkflowPhase.FAILED)

    def can_transition_to(self, target: WorkflowPhase) -> bool:
        """Validate FSM transitions."""
        valid_transitions: dict[WorkflowPhase, set[WorkflowPhase]] = {
            WorkflowPhase.PLANNING: {WorkflowPhase.EXECUTING, WorkflowPhase.FAILED},
            WorkflowPhase.EXECUTING: {
                WorkflowPhase.AWAITING_APPROVAL,
                WorkflowPhase.VERIFYING,
                WorkflowPhase.FAILED,
            },
            WorkflowPhase.AWAITING_APPROVAL: {
                WorkflowPhase.EXECUTING,
                WorkflowPhase.FAILED,
            },
            WorkflowPhase.VERIFYING: {
                WorkflowPhase.COMPLETE,
                WorkflowPhase.EXECUTING,  # verification failed → re-execute
                WorkflowPhase.FAILED,
            },
            WorkflowPhase.COMPLETE: set(),
            WorkflowPhase.FAILED: set(),
        }
        return target in valid_transitions.get(self.phase, set())
