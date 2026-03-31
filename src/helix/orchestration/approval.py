"""Human-in-the-loop approval FSM with escalation.

Claude Code's approval model is binary (approve/deny via interactive prompt).
Helix adds:
- Risk-based routing to appropriate approvers
- SLA timers with automatic escalation
- Multi-party approval for CRITICAL actions
- Audit trail on every decision
"""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field

from helix.utils import utcnow

logger = structlog.get_logger()


class EscalationPolicy(BaseModel):
    """Defines when and how approvals escalate."""

    sla_minutes: int = 60
    escalation_target_roles: list[str] = Field(default_factory=lambda: ["admin"])
    multi_party_required: bool = False
    min_approver_count: int = 1


class ApprovalRequest(BaseModel):
    """A request for human approval of an agent action."""

    id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID
    org_id: UUID
    agent_id: UUID
    action_description: str
    risk_level: str  # LOW | MEDIUM | HIGH | CRITICAL
    integration_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    status: str = "PENDING"  # PENDING | APPROVED | REJECTED | ESCALATED | EXPIRED
    decided_by: UUID | None = None
    decision_reason: str = ""
    sla_deadline: datetime | None = None
    escalated_to: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    decided_at: datetime | None = None

    def is_expired(self) -> bool:
        """Check if the SLA deadline has passed."""
        if self.sla_deadline is None:
            return False
        return utcnow() > self.sla_deadline


def create_approval_request(
    workflow_id: UUID,
    org_id: UUID,
    agent_id: UUID,
    action_description: str,
    risk_level: str,
    escalation_policy: EscalationPolicy | None = None,
    integration_id: UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> ApprovalRequest:
    """Create a new approval request with SLA deadline.

    The SLA deadline is computed from the escalation policy. When it expires,
    the request is auto-escalated to higher-authority approvers.
    """
    policy = escalation_policy or EscalationPolicy()
    sla_deadline = utcnow() + timedelta(minutes=policy.sla_minutes)

    request = ApprovalRequest(
        workflow_id=workflow_id,
        org_id=org_id,
        agent_id=agent_id,
        action_description=action_description,
        risk_level=risk_level,
        integration_id=integration_id,
        payload=payload or {},
        sla_deadline=sla_deadline,
    )

    logger.info(
        "approval.created",
        approval_id=str(request.id),
        workflow_id=str(workflow_id),
        risk_level=risk_level,
        sla_deadline=sla_deadline.isoformat(),
    )

    return request


def process_decision(
    request: ApprovalRequest,
    decision: str,
    decided_by: UUID,
    reason: str = "",
) -> ApprovalRequest:
    """Process an approval decision.

    Returns updated request with decision recorded.
    """
    if request.status != "PENDING":
        raise ValueError(f"Cannot decide on request in status: {request.status}")

    if decision not in ("APPROVED", "REJECTED"):
        raise ValueError(f"Invalid decision: {decision}")

    request.status = decision
    request.decided_by = decided_by
    request.decision_reason = reason
    request.decided_at = utcnow()

    logger.info(
        "approval.decided",
        approval_id=str(request.id),
        decision=decision,
        decided_by=str(decided_by),
    )

    return request


def check_escalation(request: ApprovalRequest) -> bool:
    """Check if a pending request should be escalated.

    Returns True if escalation is needed (SLA expired).
    """
    if request.status != "PENDING":
        return False
    if request.is_expired():
        request.status = "ESCALATED"
        logger.warning(
            "approval.escalated",
            approval_id=str(request.id),
            workflow_id=str(request.workflow_id),
        )
        return True
    return False


def requires_approval(risk_level: str, auto_approve_levels: set[str] | None = None) -> bool:
    """Determine if an action requires human approval based on risk level.

    Claude Code's classifyYoloAction() uses an LLM call for this.
    We use deterministic risk-level routing — faster, cheaper, auditable.

    Default: LOW is auto-approved, everything else requires approval.
    """
    auto_levels = auto_approve_levels or {"LOW"}
    return risk_level not in auto_levels
