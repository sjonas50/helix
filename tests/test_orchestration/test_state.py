"""Tests for workflow state model and FSM transitions."""

import uuid

import pytest

from helix.orchestration.state import (
    AgentMessage,
    AgentRole,
    ApprovalContext,
    TokenUsage,
    WorkflowPhase,
    WorkflowState,
)


class TestWorkflowPhase:
    def test_all_phases_defined(self) -> None:
        phases = list(WorkflowPhase)
        assert len(phases) == 6

    def test_phase_values(self) -> None:
        assert WorkflowPhase.PLANNING == "PLANNING"
        assert WorkflowPhase.AWAITING_APPROVAL == "AWAITING_APPROVAL"


class TestWorkflowState:
    def _make_state(self, **kwargs: object) -> WorkflowState:
        defaults = {
            "workflow_id": uuid.uuid4(),
            "org_id": uuid.uuid4(),
        }
        defaults.update(kwargs)
        return WorkflowState(**defaults)

    def test_default_state(self) -> None:
        state = self._make_state()
        assert state.phase == WorkflowPhase.PLANNING
        assert state.coordinator_agent_id is None
        assert state.worker_agent_ids == []
        assert state.messages == []
        assert state.pending_approval is None
        assert state.speculation_cache == {}
        assert not state.is_terminal()

    def test_terminal_states(self) -> None:
        complete = self._make_state(phase=WorkflowPhase.COMPLETE)
        assert complete.is_terminal()

        failed = self._make_state(phase=WorkflowPhase.FAILED)
        assert failed.is_terminal()

    def test_non_terminal_states(self) -> None:
        for phase in [
            WorkflowPhase.PLANNING,
            WorkflowPhase.EXECUTING,
            WorkflowPhase.AWAITING_APPROVAL,
            WorkflowPhase.VERIFYING,
        ]:
            state = self._make_state(phase=phase)
            assert not state.is_terminal()

    @pytest.mark.parametrize(
        "from_phase,to_phase,expected",
        [
            # Valid transitions
            (WorkflowPhase.PLANNING, WorkflowPhase.EXECUTING, True),
            (WorkflowPhase.PLANNING, WorkflowPhase.FAILED, True),
            (WorkflowPhase.EXECUTING, WorkflowPhase.AWAITING_APPROVAL, True),
            (WorkflowPhase.EXECUTING, WorkflowPhase.VERIFYING, True),
            (WorkflowPhase.EXECUTING, WorkflowPhase.FAILED, True),
            (WorkflowPhase.AWAITING_APPROVAL, WorkflowPhase.EXECUTING, True),
            (WorkflowPhase.AWAITING_APPROVAL, WorkflowPhase.FAILED, True),
            (WorkflowPhase.VERIFYING, WorkflowPhase.COMPLETE, True),
            (WorkflowPhase.VERIFYING, WorkflowPhase.EXECUTING, True),
            (WorkflowPhase.VERIFYING, WorkflowPhase.FAILED, True),
            # Invalid transitions
            (WorkflowPhase.PLANNING, WorkflowPhase.COMPLETE, False),
            (WorkflowPhase.COMPLETE, WorkflowPhase.EXECUTING, False),
            (WorkflowPhase.FAILED, WorkflowPhase.PLANNING, False),
            (WorkflowPhase.EXECUTING, WorkflowPhase.PLANNING, False),
        ],
    )
    def test_fsm_transitions(
        self, from_phase: WorkflowPhase, to_phase: WorkflowPhase, expected: bool
    ) -> None:
        state = self._make_state(phase=from_phase)
        assert state.can_transition_to(to_phase) == expected


class TestAgentMessage:
    def test_broadcast_message(self) -> None:
        msg = AgentMessage(
            sender_id=uuid.uuid4(),
            message_type="broadcast",
            payload={"content": "status update"},
        )
        assert msg.recipient_id is None

    def test_direct_message(self) -> None:
        msg = AgentMessage(
            sender_id=uuid.uuid4(),
            recipient_id=uuid.uuid4(),
            message_type="write",
            payload={"content": "task result"},
        )
        assert msg.recipient_id is not None


class TestApprovalContext:
    def test_approval_context(self) -> None:
        ctx = ApprovalContext(
            approval_id=uuid.uuid4(),
            action_description="Delete Salesforce account",
            risk_level="CRITICAL",
        )
        assert ctx.risk_level == "CRITICAL"
        assert not ctx.escalated


class TestTokenUsage:
    def test_defaults(self) -> None:
        usage = TokenUsage()
        assert usage.input_tokens == 0
        assert usage.cost_usd == 0.0


class TestAgentRole:
    def test_roles(self) -> None:
        assert AgentRole.COORDINATOR == "coordinator"
        assert AgentRole.RESEARCHER == "researcher"
        assert AgentRole.IMPLEMENTER == "implementer"
        assert AgentRole.VERIFIER == "verifier"
