"""Tests for predictive workflow engine (speculative execution)."""

import uuid

from helix.orchestration.speculation import (
    SpeculationConfig,
    SpeculativeExecution,
    create_speculation,
    is_read_only_tool,
    resolve_speculation,
    should_speculate,
)


class TestShouldSpeculate:
    def test_low_risk_speculates(self) -> None:
        assert should_speculate("LOW")

    def test_medium_risk_speculates(self) -> None:
        assert should_speculate("MEDIUM")

    def test_high_risk_speculates_at_default_threshold(self) -> None:
        # HIGH has confidence 0.50, default min is 0.50
        assert should_speculate("HIGH")

    def test_critical_risk_does_not_speculate(self) -> None:
        # CRITICAL has confidence 0.20, below default min 0.50
        assert not should_speculate("CRITICAL")

    def test_disabled_config(self) -> None:
        config = SpeculationConfig(enabled=False)
        assert not should_speculate("LOW", config)

    def test_custom_min_confidence(self) -> None:
        config = SpeculationConfig(min_confidence=0.80)
        assert should_speculate("LOW", config)  # 0.95 >= 0.80
        assert not should_speculate("MEDIUM", config)  # 0.75 < 0.80


class TestCreateSpeculation:
    def test_create_default(self) -> None:
        spec = create_speculation(
            workflow_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            approval_request_id=uuid.uuid4(),
        )
        assert spec.status == "PENDING"
        assert spec.assumed_decision == "APPROVED"
        assert spec.queued_writes == []
        assert spec.read_only_results == []

    def test_create_with_confidence(self) -> None:
        spec = create_speculation(
            workflow_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            approval_request_id=uuid.uuid4(),
            confidence_score=0.85,
        )
        assert spec.confidence_score == 0.85


class TestResolveSpeculation:
    def _make_speculation(self) -> SpeculativeExecution:
        return create_speculation(
            workflow_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            approval_request_id=uuid.uuid4(),
            assumed_decision="APPROVED",
            confidence_score=0.75,
        )

    def test_apply_on_matching_decision(self) -> None:
        spec = self._make_speculation()
        spec.queued_writes = [{"tool": "update_opportunity", "args": {"id": "123"}}]
        result = resolve_speculation(spec, "APPROVED")
        assert result == "applied"
        assert spec.status == "APPLIED"
        assert spec.resolved_at is not None

    def test_discard_on_mismatching_decision(self) -> None:
        spec = self._make_speculation()
        result = resolve_speculation(spec, "REJECTED")
        assert result == "discarded"
        assert spec.status == "DISCARDED"
        assert spec.resolved_at is not None


class TestIsReadOnlyTool:
    def test_read_only_tools(self) -> None:
        assert is_read_only_tool("get_opportunity")
        assert is_read_only_tool("list_contacts")
        assert is_read_only_tool("search_accounts")
        assert is_read_only_tool("read_document")
        assert is_read_only_tool("query_pipeline")
        assert is_read_only_tool("fetch_report")
        assert is_read_only_tool("describe_object")

    def test_write_tools(self) -> None:
        assert not is_read_only_tool("update_opportunity")
        assert not is_read_only_tool("delete_account")
        assert not is_read_only_tool("create_contact")
        assert not is_read_only_tool("send_email")
        assert not is_read_only_tool("close_deal")
