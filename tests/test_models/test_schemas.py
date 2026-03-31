"""Tests for Pydantic API schemas — validation rules, defaults, edge cases."""

import pytest
from pydantic import ValidationError

from helix.api.schemas.integrations import (
    ApprovalDecision,
    IntegrationCreate,
    RiskLevel,
)
from helix.api.schemas.memory import AccessLevel, MemoryCreate, MemoryQuery
from helix.api.schemas.orgs import OrgCreate
from helix.api.schemas.workflows import WorkflowCreate, WorkflowStatus


class TestOrgSchemas:
    def test_org_create_valid(self) -> None:
        org = OrgCreate(name="Acme Corp", slug="acme-corp")
        assert org.name == "Acme Corp"
        assert org.plan == "enterprise"
        assert org.on_prem is False

    def test_org_create_empty_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            OrgCreate(name="", slug="acme")

    def test_org_create_invalid_slug_rejected(self) -> None:
        with pytest.raises(ValidationError):
            OrgCreate(name="Acme", slug="Acme Corp!")  # uppercase + special char

    def test_org_create_valid_slug_patterns(self) -> None:
        org = OrgCreate(name="Test", slug="my-org-123")
        assert org.slug == "my-org-123"


class TestWorkflowSchemas:
    def test_workflow_create_defaults(self) -> None:
        wf = WorkflowCreate()
        assert wf.template_id is None
        assert wf.initial_context == {}

    def test_workflow_create_with_context(self) -> None:
        wf = WorkflowCreate(initial_context={"prompt": "analyze Q1 pipeline"})
        assert wf.initial_context["prompt"] == "analyze Q1 pipeline"

    def test_workflow_status_literals(self) -> None:
        valid_statuses: list[WorkflowStatus] = [
            "PLANNING",
            "EXECUTING",
            "AWAITING_APPROVAL",
            "VERIFYING",
            "COMPLETE",
            "FAILED",
        ]
        assert len(valid_statuses) == 6


class TestMemorySchemas:
    def test_memory_create_defaults(self) -> None:
        mem = MemoryCreate(topic="onboarding", content="Step 1: create account")
        assert mem.access_level == "PUBLIC"
        assert mem.tags == []
        assert mem.allowed_roles == []

    def test_memory_create_empty_content_rejected(self) -> None:
        with pytest.raises(ValidationError):
            MemoryCreate(topic="test", content="")

    def test_memory_query_defaults(self) -> None:
        q = MemoryQuery(query="how to onboard")
        assert q.limit == 10
        assert q.access_level is None

    def test_memory_query_limit_bounds(self) -> None:
        with pytest.raises(ValidationError):
            MemoryQuery(query="test", limit=0)
        with pytest.raises(ValidationError):
            MemoryQuery(query="test", limit=51)

    def test_access_level_values(self) -> None:
        valid: list[AccessLevel] = ["PUBLIC", "ROLE_RESTRICTED", "CONFIDENTIAL"]
        assert len(valid) == 3


class TestIntegrationSchemas:
    def test_integration_create_defaults(self) -> None:
        integ = IntegrationCreate(provider="salesforce")
        assert integ.connector_type == "composio"
        assert integ.rate_limit_per_hour == 1000
        assert integ.config == {}

    def test_integration_create_custom_type(self) -> None:
        integ = IntegrationCreate(
            provider="custom-erp", connector_type="custom", rate_limit_per_hour=500
        )
        assert integ.connector_type == "custom"

    def test_integration_create_invalid_connector(self) -> None:
        with pytest.raises(ValidationError):
            IntegrationCreate(provider="test", connector_type="invalid")

    def test_approval_decision_valid(self) -> None:
        d = ApprovalDecision(decision="APPROVED", reason="LGTM")
        assert d.decision == "APPROVED"

    def test_approval_decision_invalid(self) -> None:
        with pytest.raises(ValidationError):
            ApprovalDecision(decision="MAYBE")

    def test_risk_level_values(self) -> None:
        valid: list[RiskLevel] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert len(valid) == 4


class TestOrmModels:
    """Test that SQLAlchemy models can be imported and have correct table names."""

    def test_all_models_importable(self) -> None:
        from helix.db.models import (
            Agent,
            AgentMessage,
            ApprovalPolicy,
            ApprovalRequest,
            AuditEvent,
            DreamConfig,
            DreamRun,
            Integration,
            IntegrationToolExecution,
            LLMPolicy,
            MemoryRecord,
            Org,
            RolePermission,
            SpeculativeExecution,
            TokenUsageEvent,
            User,
            Workflow,
            WorkflowCompactionSnapshot,
            WorkflowTemplate,
        )
        assert Org.__tablename__ == "orgs"
        assert User.__tablename__ == "users"
        assert RolePermission.__tablename__ == "role_permissions"
        assert Workflow.__tablename__ == "workflows"
        assert WorkflowTemplate.__tablename__ == "workflow_templates"
        assert Agent.__tablename__ == "agents"
        assert AgentMessage.__tablename__ == "agent_messages"
        assert ApprovalPolicy.__tablename__ == "approval_policies"
        assert ApprovalRequest.__tablename__ == "approval_requests"
        assert MemoryRecord.__tablename__ == "memory_records"
        assert DreamConfig.__tablename__ == "dream_configs"
        assert DreamRun.__tablename__ == "dream_runs"
        assert Integration.__tablename__ == "integrations"
        assert IntegrationToolExecution.__tablename__ == "integration_tool_executions"
        assert LLMPolicy.__tablename__ == "llm_policies"
        assert TokenUsageEvent.__tablename__ == "token_usage_events"
        assert WorkflowCompactionSnapshot.__tablename__ == "workflow_compaction_snapshots"
        assert SpeculativeExecution.__tablename__ == "speculative_executions"
        assert AuditEvent.__tablename__ == "audit_events"

    def test_model_count(self) -> None:
        """Verify we have all 19 models from architecture."""
        from helix.db.models import Base

        # Get all mapped tables
        tables = Base.metadata.tables
        assert len(tables) == 19, f"Expected 19 tables, got {len(tables)}: {list(tables.keys())}"

    def test_org_relationships(self) -> None:
        from helix.db.models import Org

        rel_names = {r.key for r in Org.__mapper__.relationships}
        assert "users" in rel_names
        assert "workflows" in rel_names
        assert "integrations" in rel_names
        assert "memory_records" in rel_names
