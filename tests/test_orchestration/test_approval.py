"""Tests for human-in-the-loop approval system."""

import uuid
from datetime import datetime, timedelta

import pytest

from helix.orchestration.approval import (
    ApprovalRequest,
    EscalationPolicy,
    check_escalation,
    create_approval_request,
    process_decision,
    requires_approval,
)


class TestApprovalRequest:
    def test_create_approval_request(self) -> None:
        req = create_approval_request(
            workflow_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            agent_id=uuid.uuid4(),
            action_description="Update Salesforce opportunity",
            risk_level="HIGH",
        )
        assert req.status == "PENDING"
        assert req.risk_level == "HIGH"
        assert req.sla_deadline is not None
        assert req.decided_by is None

    def test_create_with_custom_escalation(self) -> None:
        policy = EscalationPolicy(sla_minutes=30, multi_party_required=True)
        req = create_approval_request(
            workflow_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            agent_id=uuid.uuid4(),
            action_description="Delete account",
            risk_level="CRITICAL",
            escalation_policy=policy,
        )
        # SLA should be ~30 minutes from now
        assert req.sla_deadline is not None
        delta = req.sla_deadline - req.created_at
        assert 29 <= delta.total_seconds() / 60 <= 31


class TestProcessDecision:
    def _make_request(self) -> ApprovalRequest:
        return create_approval_request(
            workflow_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            agent_id=uuid.uuid4(),
            action_description="test action",
            risk_level="MEDIUM",
        )

    def test_approve(self) -> None:
        req = self._make_request()
        user_id = uuid.uuid4()
        result = process_decision(req, "APPROVED", user_id, "Looks good")
        assert result.status == "APPROVED"
        assert result.decided_by == user_id
        assert result.decision_reason == "Looks good"
        assert result.decided_at is not None

    def test_reject(self) -> None:
        req = self._make_request()
        result = process_decision(req, "REJECTED", uuid.uuid4(), "Too risky")
        assert result.status == "REJECTED"

    def test_cannot_decide_non_pending(self) -> None:
        req = self._make_request()
        process_decision(req, "APPROVED", uuid.uuid4())
        with pytest.raises(ValueError, match="Cannot decide"):
            process_decision(req, "REJECTED", uuid.uuid4())

    def test_invalid_decision(self) -> None:
        req = self._make_request()
        with pytest.raises(ValueError, match="Invalid decision"):
            process_decision(req, "MAYBE", uuid.uuid4())


class TestEscalation:
    def test_no_escalation_when_within_sla(self) -> None:
        req = create_approval_request(
            workflow_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            agent_id=uuid.uuid4(),
            action_description="test",
            risk_level="MEDIUM",
        )
        assert not check_escalation(req)

    def test_escalation_when_expired(self) -> None:
        req = create_approval_request(
            workflow_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            agent_id=uuid.uuid4(),
            action_description="test",
            risk_level="MEDIUM",
        )
        # Force SLA expiry
        req.sla_deadline = datetime.now() - timedelta(minutes=1)
        assert check_escalation(req)
        assert req.status == "ESCALATED"

    def test_no_escalation_on_decided_request(self) -> None:
        req = create_approval_request(
            workflow_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            agent_id=uuid.uuid4(),
            action_description="test",
            risk_level="MEDIUM",
        )
        process_decision(req, "APPROVED", uuid.uuid4())
        req.sla_deadline = datetime.now() - timedelta(minutes=1)
        assert not check_escalation(req)


class TestRequiresApproval:
    def test_low_auto_approved(self) -> None:
        assert not requires_approval("LOW")

    def test_medium_requires_approval(self) -> None:
        assert requires_approval("MEDIUM")

    def test_high_requires_approval(self) -> None:
        assert requires_approval("HIGH")

    def test_critical_requires_approval(self) -> None:
        assert requires_approval("CRITICAL")

    def test_custom_auto_approve_levels(self) -> None:
        assert not requires_approval("MEDIUM", auto_approve_levels={"LOW", "MEDIUM"})
        assert requires_approval("HIGH", auto_approve_levels={"LOW", "MEDIUM"})
