"""Tests for the workflow execution engine."""

import uuid
from unittest.mock import AsyncMock, patch

from helix.integrations.bus import ToolCallResult
from helix.llm.gateway import LLMResponse
from helix.orchestration.executor import (
    ExecutionContext,
    _build_arguments_from_context,
    _execute_action,
    _execute_agent,
    _execute_approval,
    _execute_condition,
    _execute_trigger,
    _topological_sort,
    _update_workflow_status,
    execute_workflow,
)
from helix.orchestration.workflow_generator import (
    GeneratedWorkflow,
    WorkflowEdge,
    WorkflowNode,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_workflow(
    nodes: list[WorkflowNode] | None = None,
    edges: list[WorkflowEdge] | None = None,
) -> GeneratedWorkflow:
    """Build a minimal test workflow."""
    if nodes is None:
        nodes = [
            WorkflowNode(id="t1", type="trigger", label="Start", trigger_type="manual"),
            WorkflowNode(
                id="a1",
                type="action",
                label="Send Slack",
                provider="slack",
                tool_name="send_message",
            ),
        ]
    if edges is None:
        edges = [WorkflowEdge(id="e1", source="t1", target="a1")]
    return GeneratedWorkflow(
        name="Test WF",
        description="test",
        nodes=nodes,
        edges=edges,
    )


def _make_ctx(results: dict | None = None) -> ExecutionContext:
    """Build a mock execution context."""
    session = AsyncMock()
    ctx = ExecutionContext(
        workflow_id=str(uuid.uuid4()),
        org_id=str(uuid.uuid4()),
        session=session,
    )
    if results:
        ctx.results = results
    return ctx


# ---------------------------------------------------------------------------
# _topological_sort
# ---------------------------------------------------------------------------


class TestTopologicalSort:
    def test_linear_chain(self) -> None:
        wf = _make_workflow(
            nodes=[
                WorkflowNode(id="a", type="trigger", label="A"),
                WorkflowNode(id="b", type="action", label="B"),
                WorkflowNode(id="c", type="agent", label="C"),
            ],
            edges=[
                WorkflowEdge(id="e1", source="a", target="b"),
                WorkflowEdge(id="e2", source="b", target="c"),
            ],
        )
        order = _topological_sort(wf)
        assert order == ["a", "b", "c"]

    def test_diamond_shape(self) -> None:
        wf = _make_workflow(
            nodes=[
                WorkflowNode(id="a", type="trigger", label="A"),
                WorkflowNode(id="b", type="action", label="B"),
                WorkflowNode(id="c", type="action", label="C"),
                WorkflowNode(id="d", type="agent", label="D"),
            ],
            edges=[
                WorkflowEdge(id="e1", source="a", target="b"),
                WorkflowEdge(id="e2", source="a", target="c"),
                WorkflowEdge(id="e3", source="b", target="d"),
                WorkflowEdge(id="e4", source="c", target="d"),
            ],
        )
        order = _topological_sort(wf)
        assert order[0] == "a"
        assert order[-1] == "d"
        assert set(order) == {"a", "b", "c", "d"}

    def test_single_node(self) -> None:
        wf = _make_workflow(
            nodes=[WorkflowNode(id="x", type="trigger", label="X")],
            edges=[],
        )
        assert _topological_sort(wf) == ["x"]

    def test_empty_workflow(self) -> None:
        wf = _make_workflow(nodes=[], edges=[])
        assert _topological_sort(wf) == []


# ---------------------------------------------------------------------------
# _execute_trigger
# ---------------------------------------------------------------------------


class TestExecuteTrigger:
    async def test_returns_correct_shape(self) -> None:
        ctx = _make_ctx()
        node = WorkflowNode(id="t1", type="trigger", label="Start", trigger_type="webhook")
        result = await _execute_trigger(ctx, node)
        assert result["status"] == "triggered"
        assert result["trigger_type"] == "webhook"
        assert "timestamp" in result

    async def test_defaults_to_manual(self) -> None:
        ctx = _make_ctx()
        node = WorkflowNode(id="t1", type="trigger", label="Start")
        result = await _execute_trigger(ctx, node)
        assert result["trigger_type"] == "manual"


# ---------------------------------------------------------------------------
# _execute_action
# ---------------------------------------------------------------------------


class TestExecuteAction:
    @patch("helix.orchestration.executor.execute_tool")
    async def test_calls_execute_tool(self, mock_tool: AsyncMock) -> None:
        mock_tool.return_value = ToolCallResult(
            tool_name="send_message",
            output={"ok": True},
            duration_ms=42,
        )
        ctx = _make_ctx()
        node = WorkflowNode(
            id="a1",
            type="action",
            label="Send Slack",
            provider="slack",
            tool_name="send_message",
        )
        result = await _execute_action(ctx, node)

        mock_tool.assert_called_once()
        assert result["status"] == "success"
        assert result["provider"] == "slack"
        assert result["tool"] == "send_message"
        assert result["output"] == {"ok": True}
        assert result["duration_ms"] == 42

    @patch("helix.orchestration.executor.execute_tool")
    async def test_handles_tool_failure(self, mock_tool: AsyncMock) -> None:
        mock_tool.return_value = ToolCallResult(
            tool_name="send_message",
            output={},
            success=False,
            error="API timeout",
            duration_ms=5000,
        )
        ctx = _make_ctx()
        node = WorkflowNode(
            id="a1",
            type="action",
            label="Send Slack",
            provider="slack",
            tool_name="send_message",
        )
        result = await _execute_action(ctx, node)
        assert result["status"] == "failed"
        assert result["error"] == "API timeout"

    async def test_skips_when_no_provider(self) -> None:
        ctx = _make_ctx()
        node = WorkflowNode(id="a1", type="action", label="No Provider")
        result = await _execute_action(ctx, node)
        assert result["status"] == "skipped"


# ---------------------------------------------------------------------------
# _execute_agent
# ---------------------------------------------------------------------------


class TestExecuteAgent:
    @patch("helix.orchestration.executor.call_llm")
    async def test_calls_llm_with_haiku(self, mock_llm: AsyncMock) -> None:
        mock_llm.return_value = LLMResponse(
            content="Research complete",
            model_used="claude-haiku-4-5",
            provider="anthropic",
            input_tokens=100,
            output_tokens=50,
        )
        ctx = _make_ctx()
        node = WorkflowNode(
            id="ag1",
            type="agent",
            label="Research",
            description="Find data",
            agent_role="researcher",
        )
        result = await _execute_agent(ctx, node)

        mock_llm.assert_called_once()
        call_args = mock_llm.call_args
        request = call_args[0][0]
        assert request.model == "claude-haiku-4-5"
        assert result["status"] == "complete"
        assert result["role"] == "researcher"
        assert result["output"] == "Research complete"
        assert result["tokens"] == 150

    @patch("helix.orchestration.executor.call_llm")
    async def test_degrades_gracefully_on_llm_failure(self, mock_llm: AsyncMock) -> None:
        mock_llm.side_effect = RuntimeError("All LLM models failed")
        ctx = _make_ctx()
        node = WorkflowNode(
            id="ag1", type="agent", label="Verify", agent_role="verifier"
        )
        result = await _execute_agent(ctx, node)
        # Agent failure should NOT raise -- returns degraded status
        assert result["status"] == "degraded"
        assert "error" in result


# ---------------------------------------------------------------------------
# _execute_approval
# ---------------------------------------------------------------------------


class TestExecuteApproval:
    async def test_creates_db_record_and_pauses(self) -> None:
        ctx = _make_ctx()
        node = WorkflowNode(
            id="ap1",
            type="approval",
            label="Approve deploy",
            description="Review this action",
            risk_level="HIGH",
            sla_minutes=30,
        )

        with patch("helix.orchestration.executor.emit_approval_request", new_callable=AsyncMock):
            result = await _execute_approval(ctx, node)

        assert result["status"] == "AWAITING_APPROVAL"
        assert result["risk_level"] == "HIGH"
        assert result["sla_minutes"] == 30
        assert "approval_id" in result

        # Verify DB insert was called
        ctx.session.execute.assert_called()
        ctx.session.commit.assert_called()


# ---------------------------------------------------------------------------
# _execute_condition
# ---------------------------------------------------------------------------


class TestExecuteCondition:
    async def test_evaluates_true_when_all_succeeded(self) -> None:
        ctx = _make_ctx(
            results={
                "t1": {"status": "triggered"},
                "a1": {"status": "success"},
            }
        )
        node = WorkflowNode(id="c1", type="condition", label="Check")
        result = await _execute_condition(ctx, node)
        assert result["status"] == "evaluated"
        assert result["result"] is True

    async def test_evaluates_false_when_any_failed(self) -> None:
        ctx = _make_ctx(
            results={
                "t1": {"status": "triggered"},
                "a1": {"status": "failed"},
            }
        )
        node = WorkflowNode(id="c1", type="condition", label="Check")
        result = await _execute_condition(ctx, node)
        assert result["result"] is False

    async def test_uses_custom_condition_text(self) -> None:
        ctx = _make_ctx()
        node = WorkflowNode(
            id="c1",
            type="condition",
            label="Check amount",
            condition_text="deal_value > 50000",
        )
        result = await _execute_condition(ctx, node)
        assert result["condition"] == "deal_value > 50000"


# ---------------------------------------------------------------------------
# _build_arguments_from_context
# ---------------------------------------------------------------------------


class TestBuildArguments:
    def test_builds_from_dict_outputs(self) -> None:
        ctx = _make_ctx(results={"a1": {"status": "success", "output": {"key": "val"}}})
        node = WorkflowNode(id="a2", type="action", label="Next")
        args = _build_arguments_from_context(ctx, node)
        assert "workflow_context" in args
        assert args["workflow_context"]["a1"] == {"key": "val"}

    def test_wraps_string_outputs(self) -> None:
        ctx = _make_ctx(results={"a1": {"status": "success", "output": "hello"}})
        node = WorkflowNode(id="a2", type="action", label="Next")
        args = _build_arguments_from_context(ctx, node)
        assert args["workflow_context"]["a1"] == {"text": "hello"}


# ---------------------------------------------------------------------------
# Full execute_workflow integration test
# ---------------------------------------------------------------------------


class TestExecuteWorkflow:
    @patch("helix.orchestration.executor.emit_agent_activity", new_callable=AsyncMock)
    @patch("helix.orchestration.executor.emit_workflow_status", new_callable=AsyncMock)
    @patch("helix.orchestration.executor.execute_tool")
    async def test_full_execution_success(
        self,
        mock_tool: AsyncMock,
        mock_status: AsyncMock,
        mock_activity: AsyncMock,
    ) -> None:
        mock_tool.return_value = ToolCallResult(
            tool_name="send_message",
            output={"ok": True},
            duration_ms=10,
        )

        session = AsyncMock()
        wf = _make_workflow()
        wf_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())

        result = await execute_workflow(session, wf_id, org_id, wf)

        assert result["status"] == "COMPLETE"
        assert result["workflow_id"] == wf_id
        assert "t1" in result["results"]
        assert "a1" in result["results"]

        # Status events were emitted
        assert mock_status.call_count >= 2  # EXECUTING + COMPLETE

    @patch("helix.orchestration.executor.emit_agent_activity", new_callable=AsyncMock)
    @patch("helix.orchestration.executor.emit_workflow_status", new_callable=AsyncMock)
    @patch("helix.orchestration.executor.execute_tool")
    async def test_execution_pauses_at_approval(
        self,
        mock_tool: AsyncMock,
        mock_status: AsyncMock,
        mock_activity: AsyncMock,
    ) -> None:
        wf = _make_workflow(
            nodes=[
                WorkflowNode(id="t1", type="trigger", label="Start"),
                WorkflowNode(
                    id="ap1",
                    type="approval",
                    label="Approve",
                    risk_level="HIGH",
                    sla_minutes=30,
                ),
                WorkflowNode(
                    id="a1",
                    type="action",
                    label="Send",
                    provider="slack",
                    tool_name="send_message",
                ),
            ],
            edges=[
                WorkflowEdge(id="e1", source="t1", target="ap1"),
                WorkflowEdge(id="e2", source="ap1", target="a1"),
            ],
        )

        session = AsyncMock()
        wf_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())

        with patch(
            "helix.orchestration.executor.emit_approval_request", new_callable=AsyncMock
        ):
            result = await execute_workflow(session, wf_id, org_id, wf)

        assert result["status"] == "AWAITING_APPROVAL"
        assert result["paused_at_node"] == "ap1"
        assert "approval_id" in result
        # Action was NOT executed
        mock_tool.assert_not_called()

    @patch("helix.orchestration.executor.emit_agent_activity", new_callable=AsyncMock)
    @patch("helix.orchestration.executor.emit_workflow_status", new_callable=AsyncMock)
    @patch("helix.orchestration.executor.execute_tool")
    async def test_execution_handles_node_error(
        self,
        mock_tool: AsyncMock,
        mock_status: AsyncMock,
        mock_activity: AsyncMock,
    ) -> None:
        mock_tool.side_effect = Exception("Connection refused")

        session = AsyncMock()
        wf = _make_workflow()
        wf_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())

        result = await execute_workflow(session, wf_id, org_id, wf)

        assert result["status"] == "FAILED"
        assert result["failed_at_node"] == "a1"
        assert "Connection refused" in result["error"]

    @patch("helix.orchestration.executor.emit_agent_activity", new_callable=AsyncMock)
    @patch("helix.orchestration.executor.emit_workflow_status", new_callable=AsyncMock)
    @patch("helix.orchestration.executor.call_llm")
    @patch("helix.orchestration.executor.execute_tool")
    async def test_workflow_with_agent_node(
        self,
        mock_tool: AsyncMock,
        mock_llm: AsyncMock,
        mock_status: AsyncMock,
        mock_activity: AsyncMock,
    ) -> None:
        mock_tool.return_value = ToolCallResult(
            tool_name="send_message", output={"ok": True}, duration_ms=5
        )
        mock_llm.return_value = LLMResponse(
            content="All good",
            model_used="claude-haiku-4-5",
            provider="anthropic",
            input_tokens=50,
            output_tokens=25,
        )

        wf = _make_workflow(
            nodes=[
                WorkflowNode(id="t1", type="trigger", label="Start"),
                WorkflowNode(
                    id="a1",
                    type="action",
                    label="Send",
                    provider="slack",
                    tool_name="send_message",
                ),
                WorkflowNode(
                    id="ag1",
                    type="agent",
                    label="Verify",
                    agent_role="verifier",
                ),
            ],
            edges=[
                WorkflowEdge(id="e1", source="t1", target="a1"),
                WorkflowEdge(id="e2", source="a1", target="ag1"),
            ],
        )

        session = AsyncMock()
        result = await execute_workflow(session, str(uuid.uuid4()), str(uuid.uuid4()), wf)

        assert result["status"] == "COMPLETE"
        assert result["results"]["ag1"]["status"] == "complete"
        assert result["results"]["ag1"]["role"] == "verifier"


# ---------------------------------------------------------------------------
# _update_workflow_status
# ---------------------------------------------------------------------------


class TestUpdateWorkflowStatus:
    async def test_sets_completed_at_for_terminal_states(self) -> None:
        session = AsyncMock()
        await _update_workflow_status(session, "wf-1", "COMPLETE")
        # Should have called execute twice (status update + completed_at) + commit
        assert session.execute.call_count == 2
        session.commit.assert_called()

    async def test_no_completed_at_for_executing(self) -> None:
        session = AsyncMock()
        await _update_workflow_status(session, "wf-1", "EXECUTING")
        assert session.execute.call_count == 1
        session.commit.assert_called()
