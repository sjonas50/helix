"""SQLAlchemy ORM models for the Helix platform.

All tables from docs/architecture.md. Multi-tenant with org_id on every
tenant-scoped table. Audit trail is append-only and partitioned by month.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all Helix ORM models."""

    pass


# ---------------------------------------------------------------------------
# Tenant Foundation
# ---------------------------------------------------------------------------


class Org(Base):
    __tablename__ = "orgs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    workos_org_id: Mapped[str | None] = mapped_column(String(256), unique=True)
    plan: Mapped[str] = mapped_column(String(32), server_default="enterprise")
    status: Mapped[str] = mapped_column(String(32), server_default="active")
    on_prem: Mapped[bool] = mapped_column(Boolean, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    users: Mapped[list["User"]] = relationship(back_populates="org")
    workflows: Mapped[list["Workflow"]] = relationship(back_populates="org")
    integrations: Mapped[list["Integration"]] = relationship(back_populates="org")
    memory_records: Mapped[list["MemoryRecord"]] = relationship(back_populates="org")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False
    )
    workos_user_id: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(256))
    roles: Mapped[list[str] | None] = mapped_column(ARRAY(Text), server_default="{}")
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    org: Mapped["Org"] = relationship(back_populates="users")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("org_id", "role", "resource", "action"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    resource: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    conditions: Mapped[dict | None] = mapped_column(JSONB, server_default="{}")


# ---------------------------------------------------------------------------
# Workflow Templates
# ---------------------------------------------------------------------------


class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id")
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    langgraph_definition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    max_hierarchy_depth: Mapped[int] = mapped_column(SmallInteger, server_default="2")
    speculation_depth: Mapped[int] = mapped_column(SmallInteger, server_default="1")
    default_model: Mapped[str] = mapped_column(
        String(128), server_default="claude-sonnet-4-6"
    )
    is_public: Mapped[bool] = mapped_column(Boolean, server_default="false")
    version: Mapped[int] = mapped_column(Integer, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


# ---------------------------------------------------------------------------
# Orchestration: Workflows, Agents, Messages, Approvals
# ---------------------------------------------------------------------------


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_templates.id")
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    coordinator_agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    initial_context: Mapped[dict | None] = mapped_column(JSONB)
    result: Mapped[dict | None] = mapped_column(JSONB)
    token_usage: Mapped[dict | None] = mapped_column(JSONB)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    org: Mapped["Org"] = relationship(back_populates="workflows")
    agents: Mapped[list["Agent"]] = relationship(back_populates="workflow")
    approval_requests: Mapped[list["ApprovalRequest"]] = relationship(
        back_populates="workflow"
    )


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    spawned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id")
    )
    hierarchy_depth: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    token_usage: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    terminated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workflow: Mapped["Workflow"] = relationship(back_populates="agents")
    parent: Mapped["Agent | None"] = relationship(remote_side=[id])


class AgentMessage(Base):
    __tablename__ = "agent_messages"
    __table_args__ = (
        Index("idx_agent_messages_workflow", "workflow_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False
    )
    sender_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )
    recipient_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id")
    )
    message_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class ApprovalPolicy(Base):
    __tablename__ = "approval_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    risk_levels_requiring_approval: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text)
    )
    approver_roles: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    escalation_sla_minutes: Mapped[int] = mapped_column(Integer, server_default="60")
    escalation_target_roles: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    multi_party_required: Mapped[bool] = mapped_column(
        Boolean, server_default="false"
    )
    min_approver_count: Mapped[int] = mapped_column(Integer, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False
    )
    requested_by_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )
    action_description: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    integration_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integrations.id")
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), server_default="PENDING")
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    decision_reason: Mapped[str | None] = mapped_column(Text)
    sla_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    escalated_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workflow: Mapped["Workflow"] = relationship(back_populates="approval_requests")


# ---------------------------------------------------------------------------
# Memory System
# ---------------------------------------------------------------------------


class MemoryRecord(Base):
    __tablename__ = "memory_records"
    __table_args__ = (
        Index("idx_memory_org_topic", "org_id", "topic"),
        UniqueConstraint("org_id", "source_system", "source_id", name="uq_memory_source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id")
    )
    topic: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text), server_default="{}")
    access_level: Mapped[str] = mapped_column(String(32), server_default="PUBLIC")
    allowed_roles: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), server_default="{}"
    )
    source_session_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), server_default="{}"
    )
    # Ambient memory: tracks where data came from for dedup and provenance
    content_hash: Mapped[str | None] = mapped_column(String(64))  # SHA-256
    source_system: Mapped[str | None] = mapped_column(String(64))  # slack, salesforce, etc.
    source_id: Mapped[str | None] = mapped_column(String(512))  # External record ID
    source_url: Mapped[str | None] = mapped_column(Text)  # Link back to original
    # Note: pgvector column created via raw SQL in migration (vector(1536))
    # embedding column is not mapped here — accessed via raw SQL for vector ops
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    org: Mapped["Org"] = relationship(back_populates="memory_records")


class DreamConfig(Base):
    __tablename__ = "dream_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id"), unique=True, nullable=False
    )
    min_hours_between_runs: Mapped[int] = mapped_column(
        Integer, server_default="24"
    )
    min_sessions_between_runs: Mapped[int] = mapped_column(
        Integer, server_default="5"
    )
    max_memory_records: Mapped[int] = mapped_column(Integer, server_default="500")
    max_bytes_per_record: Mapped[int] = mapped_column(
        Integer, server_default="8192"
    )
    pii_strip_enabled: Mapped[bool] = mapped_column(
        Boolean, server_default="true"
    )
    consolidation_model: Mapped[str] = mapped_column(
        String(128), server_default="claude-sonnet-4-6"
    )


class DreamRun(Base):
    __tablename__ = "dream_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False
    )
    triggered_by: Mapped[str | None] = mapped_column(String(64))
    phase: Mapped[str] = mapped_column(String(32), nullable=False)
    sessions_processed: Mapped[int | None] = mapped_column(Integer)
    records_created: Mapped[int | None] = mapped_column(Integer)
    records_updated: Mapped[int | None] = mapped_column(Integer)
    records_pruned: Mapped[int | None] = mapped_column(Integer)
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ---------------------------------------------------------------------------
# Integration Bus
# ---------------------------------------------------------------------------


class Integration(Base):
    __tablename__ = "integrations"
    __table_args__ = (UniqueConstraint("org_id", "provider"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(32), nullable=False)
    credential_ref: Mapped[str | None] = mapped_column(String(512))
    config: Mapped[dict | None] = mapped_column(JSONB, server_default="{}")
    enabled: Mapped[bool] = mapped_column(Boolean, server_default="true")
    rate_limit_per_hour: Mapped[int] = mapped_column(
        Integer, server_default="1000"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    org: Mapped["Org"] = relationship(back_populates="integrations")


class IntegrationToolExecution(Base):
    __tablename__ = "integration_tool_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False
    )
    integration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integrations.id"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    arguments: Mapped[dict | None] = mapped_column(JSONB)
    result: Mapped[dict | None] = mapped_column(JSONB)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    approval_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("approval_requests.id")
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


# ---------------------------------------------------------------------------
# LLM Gateway
# ---------------------------------------------------------------------------


class LLMPolicy(Base):
    __tablename__ = "llm_policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id"), unique=True, nullable=False
    )
    primary_model: Mapped[str] = mapped_column(
        String(128), server_default="claude-sonnet-4-6"
    )
    fallback_chain: Mapped[dict | None] = mapped_column(
        JSONB, server_default='["claude-haiku-4-5"]'
    )
    allow_silent_downgrade: Mapped[bool] = mapped_column(
        Boolean, server_default="true"
    )
    max_context_tokens: Mapped[int] = mapped_column(
        Integer, server_default="200000"
    )
    compaction_threshold_pct: Mapped[float] = mapped_column(
        Numeric(5, 2), server_default="83.5"
    )
    provider_preference: Mapped[str] = mapped_column(
        String(64), server_default="anthropic"
    )
    azure_endpoint: Mapped[str | None] = mapped_column(Text)
    bedrock_region: Mapped[str | None] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class TokenUsageEvent(Base):
    __tablename__ = "token_usage_events"
    __table_args__ = (
        Index("idx_token_usage_org_date", "org_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False
    )
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id")
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id")
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, server_default="0")
    cache_write_tokens: Mapped[int] = mapped_column(Integer, server_default="0")
    cost_usd: Mapped[float | None] = mapped_column(Numeric(12, 8))
    cost_center: Mapped[str | None] = mapped_column(String(128))
    fallback_occurred: Mapped[bool] = mapped_column(
        Boolean, server_default="false"
    )
    fallback_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class WorkflowCompactionSnapshot(Base):
    __tablename__ = "workflow_compaction_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )
    context_pct_at_trigger: Mapped[float | None] = mapped_column(Numeric(5, 2))
    tokens_before: Mapped[int | None] = mapped_column(Integer)
    tokens_after: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


# ---------------------------------------------------------------------------
# Predictive Workflow Engine
# ---------------------------------------------------------------------------


class SpeculativeExecution(Base):
    __tablename__ = "speculative_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False
    )
    approval_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("approval_requests.id"), nullable=False
    )
    assumed_decision: Mapped[str] = mapped_column(String(16), nullable=False)
    speculation_depth: Mapped[int] = mapped_column(SmallInteger, server_default="1")
    pre_computed_state: Mapped[dict | None] = mapped_column(JSONB)
    queued_writes: Mapped[dict | None] = mapped_column(
        JSONB, server_default="[]"
    )
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    token_cost: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), server_default="PENDING")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ---------------------------------------------------------------------------
# Audit Trail (append-only)
# ---------------------------------------------------------------------------


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id")
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64))
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    payload: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
