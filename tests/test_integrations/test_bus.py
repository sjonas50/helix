"""Tests for integration bus — risk classification, tool sorting, parallel batching."""

import uuid

from helix.integrations.bus import (
    SALESFORCE_TOOLS,
    IntegrationConfig,
    IntegrationTool,
    can_execute_parallel,
    classify_risk,
    get_sorted_tools,
    requires_approval,
)


class TestClassifyRisk:
    def test_returns_tool_risk_level(self) -> None:
        tool = IntegrationTool(name="test", description="test", risk_level="HIGH")
        assert classify_risk(tool) == "HIGH"


class TestRequiresApproval:
    def test_low_no_approval(self) -> None:
        tool = IntegrationTool(name="get_x", description="read", risk_level="LOW")
        assert not requires_approval(tool)

    def test_medium_requires_approval(self) -> None:
        tool = IntegrationTool(name="create_x", description="write", risk_level="MEDIUM")
        assert requires_approval(tool)

    def test_high_requires_approval(self) -> None:
        tool = IntegrationTool(name="update_x", description="write", risk_level="HIGH")
        assert requires_approval(tool)

    def test_critical_requires_approval(self) -> None:
        tool = IntegrationTool(name="delete_x", description="delete", risk_level="CRITICAL")
        assert requires_approval(tool)

    def test_explicit_approval_flag(self) -> None:
        tool = IntegrationTool(
            name="safe_but_flagged",
            description="test",
            risk_level="LOW",
            requires_approval=True,
        )
        assert requires_approval(tool)


class TestGetSortedTools:
    def test_alphabetical_sort(self) -> None:
        integration = IntegrationConfig(
            org_id=uuid.uuid4(),
            provider="salesforce",
            tools=[
                IntegrationTool(name="zebra", description="z"),
                IntegrationTool(name="alpha", description="a"),
                IntegrationTool(name="middle", description="m"),
            ],
        )
        sorted_tools = get_sorted_tools(integration)
        names = [t.name for t in sorted_tools]
        assert names == ["alpha", "middle", "zebra"]


class TestCanExecuteParallel:
    def test_all_parallel_safe(self) -> None:
        tools = [
            IntegrationTool(name="get_a", description="a", parallel_safe=True),
            IntegrationTool(name="get_b", description="b", parallel_safe=True),
        ]
        batches = can_execute_parallel(tools)
        assert len(batches) == 1
        assert len(batches[0]) == 2

    def test_all_serial(self) -> None:
        tools = [
            IntegrationTool(name="update_a", description="a", parallel_safe=False),
            IntegrationTool(name="update_b", description="b", parallel_safe=False),
        ]
        batches = can_execute_parallel(tools)
        assert len(batches) == 2  # Each gets its own batch

    def test_mixed(self) -> None:
        tools = [
            IntegrationTool(name="get_a", description="a", parallel_safe=True),
            IntegrationTool(name="get_b", description="b", parallel_safe=True),
            IntegrationTool(name="update_c", description="c", parallel_safe=False),
        ]
        batches = can_execute_parallel(tools)
        assert len(batches) == 2  # One parallel batch + one serial


class TestSalesforceToolRegistry:
    def test_default_tools_exist(self) -> None:
        assert len(SALESFORCE_TOOLS) == 5

    def test_risk_levels(self) -> None:
        risks = {t.name: t.risk_level for t in SALESFORCE_TOOLS}
        assert risks["get_account"] == "LOW"
        assert risks["list_opportunities"] == "LOW"
        assert risks["update_opportunity"] == "HIGH"
        assert risks["create_contact"] == "MEDIUM"
        assert risks["delete_account"] == "CRITICAL"

    def test_read_tools_parallel_safe(self) -> None:
        for tool in SALESFORCE_TOOLS:
            if tool.name.startswith(("get_", "list_")):
                assert tool.parallel_safe

    def test_write_tools_not_parallel_safe(self) -> None:
        for tool in SALESFORCE_TOOLS:
            if tool.name.startswith(("update_", "create_", "delete_")):
                assert not tool.parallel_safe
