"""Integration bus — SaaS tool dispatch with risk classification.

Adapted from Claude Code's tool system:
- CC has 40-60 tools with LOW/MEDIUM/HIGH risk classification
- CC's classifyYoloAction() uses Claude inference for auto-approval
- CC sorts tools alphabetically for prompt cache optimization
- CC supports concurrent reads, serial writes

Key improvements:
- Tools are SaaS integrations (Salesforce, Jira, Slack, SAP) via Composio/Nango
- Risk classification per integration per tenant
- Approval workflows with escalation (not just approve/deny)
- Per-integration rate limiting via Redis
"""

from typing import Any
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class IntegrationTool(BaseModel):
    """A single tool within an integration.

    Maps to Claude Code's tool definitions with risk classification.
    """

    name: str
    description: str
    parameters_schema: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "LOW"  # LOW | MEDIUM | HIGH | CRITICAL
    requires_approval: bool = False
    approval_policy_id: UUID | None = None
    parallel_safe: bool = True  # CC: concurrent reads, serial writes
    idempotent: bool = False


class IntegrationConfig(BaseModel):
    """Configuration for a SaaS integration."""

    id: UUID = Field(default_factory=uuid4)
    org_id: UUID
    provider: str  # salesforce | jira | slack | sap | github
    connector_type: str = "composio"  # composio | nango | custom
    enabled: bool = True
    rate_limit_per_hour: int = 1000
    tools: list[IntegrationTool] = Field(default_factory=list)


class ToolCallRequest(BaseModel):
    """Request to execute an integration tool."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    workflow_id: UUID
    agent_id: UUID
    org_id: UUID
    integration_id: UUID


class ToolCallResult(BaseModel):
    """Result from an integration tool execution."""

    id: UUID = Field(default_factory=uuid4)
    tool_name: str
    output: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "LOW"
    approval_required: bool = False
    approval_id: UUID | None = None
    rate_limit_remaining: int | None = None
    duration_ms: int = 0
    error: str | None = None
    success: bool = True


def classify_risk(tool: IntegrationTool) -> str:
    """Classify tool risk level.

    Claude Code's classifyYoloAction() uses a fast Claude inference call.
    We use deterministic classification from the tool registry — faster,
    cheaper, auditable. Risk levels are set when the integration is
    configured, not at runtime.
    """
    return tool.risk_level


def requires_approval(tool: IntegrationTool) -> bool:
    """Check if a tool call requires human approval.

    Based on the tool's risk level and explicit approval requirement.
    Default: LOW is auto-approved, everything else needs approval.
    """
    if tool.requires_approval:
        return True
    return tool.risk_level in ("MEDIUM", "HIGH", "CRITICAL")


def get_sorted_tools(integration: IntegrationConfig) -> list[IntegrationTool]:
    """Return tools sorted alphabetically for prompt cache optimization.

    Claude Code sorts tools alphabetically in the registry specifically
    to maximize prompt cache hit rates — the order affects caching since
    the tool list appears in the system prompt.
    """
    return sorted(integration.tools, key=lambda t: t.name)


def can_execute_parallel(tools: list[IntegrationTool]) -> list[list[IntegrationTool]]:
    """Group tools into parallel-safe batches.

    Claude Code: concurrent execution for read-only tools, serial for writes.
    We use the parallel_safe flag on each tool to determine batching.
    """
    parallel_batch: list[IntegrationTool] = []
    serial_queue: list[IntegrationTool] = []

    for tool in tools:
        if tool.parallel_safe:
            parallel_batch.append(tool)
        else:
            serial_queue.append(tool)

    batches: list[list[IntegrationTool]] = []
    if parallel_batch:
        batches.append(parallel_batch)
    for tool in serial_queue:
        batches.append([tool])

    return batches


# Default tool registries for common integrations
SALESFORCE_TOOLS: list[IntegrationTool] = [
    IntegrationTool(
        name="get_account",
        description="Retrieve a Salesforce account by ID",
        risk_level="LOW",
        parallel_safe=True,
        idempotent=True,
    ),
    IntegrationTool(
        name="list_opportunities",
        description="List opportunities with optional filters",
        risk_level="LOW",
        parallel_safe=True,
        idempotent=True,
    ),
    IntegrationTool(
        name="update_opportunity",
        description="Update fields on a Salesforce opportunity",
        risk_level="HIGH",
        requires_approval=True,
        parallel_safe=False,
        idempotent=False,
    ),
    IntegrationTool(
        name="create_contact",
        description="Create a new contact in Salesforce",
        risk_level="MEDIUM",
        parallel_safe=False,
        idempotent=False,
    ),
    IntegrationTool(
        name="delete_account",
        description="Delete a Salesforce account (irreversible)",
        risk_level="CRITICAL",
        requires_approval=True,
        parallel_safe=False,
        idempotent=False,
    ),
]
