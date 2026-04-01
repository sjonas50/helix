"""Tests for real-time event emission helpers."""

from unittest.mock import AsyncMock

import pytest

from helix.api import events


@pytest.fixture(autouse=True)
def _reset_manager():
    """Reset the cached manager between tests."""
    events._manager = None
    yield
    events._manager = None


@pytest.fixture
def mock_manager() -> AsyncMock:
    mgr = AsyncMock()
    mgr.broadcast_to_org = AsyncMock()
    return mgr


class TestEmitApprovalRequest:
    @pytest.mark.anyio
    async def test_broadcasts_correct_shape(self, mock_manager: AsyncMock) -> None:
        events._manager = mock_manager

        await events.emit_approval_request(
            org_id="org-1",
            approval_id="apr-1",
            workflow_id="wf-1",
            action_description="Deploy to prod",
            risk_level="high",
            sla_deadline="2026-04-01T00:00:00Z",
        )

        mock_manager.broadcast_to_org.assert_awaited_once()
        call_args = mock_manager.broadcast_to_org.call_args
        assert call_args[0][0] == "org-1"
        msg = call_args[0][1]
        assert msg["type"] == "approval_request"
        assert "timestamp" in msg
        assert msg["data"]["approval_id"] == "apr-1"
        assert msg["data"]["risk_level"] == "high"
        assert msg["data"]["sla_deadline"] == "2026-04-01T00:00:00Z"


class TestEmitWorkflowStatus:
    @pytest.mark.anyio
    async def test_broadcasts_correct_shape(self, mock_manager: AsyncMock) -> None:
        events._manager = mock_manager

        await events.emit_workflow_status(
            org_id="org-1",
            workflow_id="wf-1",
            status="running",
            phase="execution",
        )

        mock_manager.broadcast_to_org.assert_awaited_once()
        msg = mock_manager.broadcast_to_org.call_args[0][1]
        assert msg["type"] == "workflow_status"
        assert msg["data"]["workflow_id"] == "wf-1"
        assert msg["data"]["status"] == "running"
        assert msg["data"]["phase"] == "execution"


class TestEmitAgentActivity:
    @pytest.mark.anyio
    async def test_broadcasts_correct_shape(self, mock_manager: AsyncMock) -> None:
        events._manager = mock_manager

        await events.emit_agent_activity(
            org_id="org-1",
            agent_id="agent-1",
            workflow_id="wf-1",
            action="tool_call",
            description="Querying database",
        )

        mock_manager.broadcast_to_org.assert_awaited_once()
        msg = mock_manager.broadcast_to_org.call_args[0][1]
        assert msg["type"] == "agent_activity"
        assert msg["data"]["agent_id"] == "agent-1"
        assert msg["data"]["action"] == "tool_call"
        assert msg["data"]["description"] == "Querying database"
