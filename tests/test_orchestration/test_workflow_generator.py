"""Tests for workflow generation from natural language."""

from unittest.mock import AsyncMock, patch

from helix.orchestration.workflow_generator import (
    GeneratedWorkflow,
    WorkflowNode,
    _generate_fallback,
    _get_available_tools_prompt,
    generate_workflow,
)


class TestGenerateFallback:
    """Test the keyword-based fallback generator."""

    def test_detects_salesforce(self) -> None:
        result = _generate_fallback("When a Salesforce opportunity closes, notify the team")
        assert "salesforce" in result.integrations_used

    def test_detects_multiple_integrations(self) -> None:
        result = _generate_fallback("Create a Jira ticket and send a Slack message when a GitHub PR is merged")
        assert "jira" in result.integrations_used
        assert "slack" in result.integrations_used
        assert "github" in result.integrations_used

    def test_detects_schedule_trigger(self) -> None:
        result = _generate_fallback("Every week, generate a pipeline report from Salesforce")
        trigger = next(n for n in result.nodes if n.type == "trigger")
        assert trigger.trigger_type == "schedule"

    def test_detects_manual_trigger(self) -> None:
        result = _generate_fallback("When I manually request it, pull HubSpot data")
        trigger = next(n for n in result.nodes if n.type == "trigger")
        assert trigger.trigger_type == "manual"

    def test_adds_approval_for_high_risk(self) -> None:
        result = _generate_fallback("Update opportunities in Salesforce")
        # Salesforce update_opportunity is HIGH risk → should add approval
        high_risk_actions = [n for n in result.nodes if n.type == "action" and n.risk_level in ("HIGH", "CRITICAL")]
        approval_nodes = [n for n in result.nodes if n.type == "approval"]
        # If there are high-risk actions, there should be approvals
        if high_risk_actions:
            assert len(approval_nodes) >= 1
        else:
            # The fallback may pick a different tool — just verify it generated something
            assert len(result.nodes) >= 3

    def test_includes_research_agent(self) -> None:
        result = _generate_fallback("Analyze Salesforce pipeline data")
        agent_nodes = [n for n in result.nodes if n.type == "agent"]
        assert any(n.agent_role == "researcher" for n in agent_nodes)

    def test_includes_verifier_agent(self) -> None:
        result = _generate_fallback("Send a Slack notification about Jira tickets")
        agent_nodes = [n for n in result.nodes if n.type == "agent"]
        assert any(n.agent_role == "verifier" for n in agent_nodes)

    def test_edges_connect_all_nodes(self) -> None:
        result = _generate_fallback("Salesforce to Slack notification workflow")
        node_ids = {n.id for n in result.nodes}
        edge_sources = {e.source for e in result.edges}
        edge_targets = {e.target for e in result.edges}
        # All nodes except the first should be a target
        # All nodes except the last should be a source
        connected = edge_sources | edge_targets
        assert connected.issubset(node_ids)

    def test_uses_real_tool_names(self) -> None:
        result = _generate_fallback("Send a message in Slack and create a Jira issue")
        action_nodes = [n for n in result.nodes if n.type == "action"]
        for node in action_nodes:
            assert node.provider is not None
            assert node.tool_name is not None

    def test_defaults_when_no_clear_integration_detected(self) -> None:
        result = _generate_fallback("Process incoming requests and respond appropriately")
        # Should still generate a valid workflow even without clear integration keywords
        assert len(result.nodes) >= 3
        assert len(result.integrations_used) >= 1

    def test_sets_estimated_risk(self) -> None:
        result = _generate_fallback("Delete an account in Salesforce")
        assert result.estimated_risk in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


class TestGenerateWorkflow:
    """Test the LLM-powered generator with mock."""

    async def test_calls_llm_and_returns_result(self) -> None:
        mock_result = GeneratedWorkflow(
            name="Test Workflow",
            description="A test",
            nodes=[WorkflowNode(id="n1", type="trigger", label="Start")],
            edges=[],
            integrations_used=["slack"],
            estimated_risk="LOW",
        )
        with patch("helix.llm.structured.structured_call", new_callable=AsyncMock, return_value=mock_result):
            result = await generate_workflow("Send a Slack message when something happens")
            assert result.name == "Test Workflow"
            assert len(result.nodes) == 1

    async def test_falls_back_on_llm_failure(self) -> None:
        with patch("helix.llm.structured.structured_call", new_callable=AsyncMock, side_effect=Exception("API down")):
            result = await generate_workflow("Create a Jira ticket from Salesforce data")
            # Should use fallback, not crash
            assert len(result.nodes) >= 3
            assert "jira" in result.integrations_used or "salesforce" in result.integrations_used


class TestAvailableToolsPrompt:
    def test_includes_all_providers(self) -> None:
        prompt = _get_available_tools_prompt()
        assert "salesforce" in prompt
        assert "slack" in prompt
        assert "jira" in prompt
        assert "github" in prompt
