"""Generate workflow graphs from natural language descriptions.

Takes a user's plain-English description of what they want to automate,
considers available integrations and tools, and produces a structured
workflow graph that can be rendered on the React Flow canvas.
"""

from typing import Any

import structlog
from pydantic import BaseModel, Field

from helix.integrations.registry import ToolRegistry

logger = structlog.get_logger()

REGISTRY = ToolRegistry()


class WorkflowNode(BaseModel):
    """A node in the generated workflow graph."""

    id: str
    type: str  # trigger | action | condition | approval | agent
    label: str
    description: str = ""
    # Type-specific fields
    provider: str | None = None
    tool_name: str | None = None
    risk_level: str | None = None
    trigger_type: str | None = None  # webhook | schedule | manual
    agent_role: str | None = None  # researcher | implementer | verifier
    condition_text: str | None = None
    sla_minutes: int | None = None


class WorkflowEdge(BaseModel):
    """An edge connecting two nodes."""

    id: str
    source: str
    target: str
    label: str = ""


class GeneratedWorkflow(BaseModel):
    """Complete generated workflow from NL description."""

    name: str
    description: str
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    integrations_used: list[str] = Field(default_factory=list)
    estimated_risk: str = "MEDIUM"


def _get_available_tools_prompt() -> str:
    """Build a summary of available tools for the LLM prompt."""
    lines = []
    for provider in REGISTRY.get_all_providers():
        tools = REGISTRY.get_tools(provider)
        tool_names = ", ".join(t.name for t in tools)
        lines.append(f"  {provider}: {tool_names}")
    return "\n".join(lines)


async def generate_workflow(description: str) -> GeneratedWorkflow:
    """Generate a workflow graph from a natural language description.

    Uses Claude to understand the intent, map to available integrations/tools,
    and produce a structured graph with proper node types and connections.
    """
    tools_prompt = _get_available_tools_prompt()

    prompt = f"""You are a workflow architect for an enterprise automation platform.

Given a user's description of what they want to automate, generate a workflow graph.

Available integrations and tools:
{tools_prompt}

Node types you can use:
- trigger: The event that starts the workflow (webhook, schedule, or manual)
- action: A specific tool call to an integration (must reference a real provider and tool from the list above)
- condition: An if/else branch based on data (e.g., "if deal value > $50K")
- approval: A human-in-the-loop pause point for review (include SLA in minutes)
- agent: An LLM agent that researches, analyzes, or generates content (role: researcher, implementer, or verifier)

Rules:
1. Use REAL provider names and tool names from the available list above
2. Set appropriate risk_level for each action node (LOW, MEDIUM, HIGH, CRITICAL)
3. Add approval nodes before any HIGH or CRITICAL risk actions
4. Add an agent node when the workflow needs intelligence (research, analysis, drafting)
5. Keep it practical — 4-8 nodes is ideal, not more than 12
6. Every workflow must start with a trigger and should end with either a verification agent or a notification

User's description: {description}"""

    try:
        from helix.llm.structured import structured_call

        result = await structured_call(prompt, GeneratedWorkflow, model="claude-sonnet-4-6")
        logger.info(
            "workflow.generated",
            name=result.name,
            nodes=len(result.nodes),
            edges=len(result.edges),
        )
        return result
    except Exception as e:
        logger.error("workflow.generation_failed", error=str(e))
        # Fallback: generate a sensible default from the description
        return _generate_fallback(description)


def _generate_fallback(description: str) -> GeneratedWorkflow:
    """Generate a basic workflow when LLM call fails.

    Parses the description for keywords to identify integrations and
    builds a reasonable trigger → research → action → approve → verify flow.
    """
    desc_lower = description.lower()

    # Detect integrations mentioned
    integrations_found = []
    provider_keywords = {
        "salesforce": ["salesforce", "sfdc", "opportunity", "lead", "account", "crm"],
        "slack": ["slack", "channel", "message", "notify", "notification"],
        "jira": ["jira", "ticket", "issue", "sprint", "backlog"],
        "github": ["github", "pr", "pull request", "merge", "repo", "repository"],
        "hubspot": ["hubspot", "deal", "contact", "pipeline"],
        "google_workspace": ["google", "gmail", "calendar", "docs", "sheets", "email"],
        "zendesk": ["zendesk", "support ticket", "helpdesk"],
        "servicenow": ["servicenow", "incident", "itil", "change request"],
        "notion": ["notion", "wiki", "knowledge base", "page"],
        "docusign": ["docusign", "sign", "contract", "envelope"],
    }

    for provider, keywords in provider_keywords.items():
        if any(kw in desc_lower for kw in keywords):
            integrations_found.append(provider)

    if not integrations_found:
        integrations_found = ["slack"]  # Default fallback

    # Detect trigger type
    trigger_type = "webhook"
    if any(w in desc_lower for w in ["every", "daily", "weekly", "monthly", "schedule", "cron"]):
        trigger_type = "schedule"
    elif any(w in desc_lower for w in ["manually", "on demand", "when i click"]):
        trigger_type = "manual"

    # Build nodes
    nodes: list[WorkflowNode] = []
    edges: list[WorkflowEdge] = []
    node_id = 0

    def add_node(**kwargs: Any) -> str:
        nonlocal node_id
        node_id += 1
        nid = f"node-{node_id}"
        nodes.append(WorkflowNode(id=nid, **kwargs))
        return nid

    # Trigger
    trigger_desc = "Watches for the triggering event"
    if trigger_type == "schedule":
        trigger_desc = "Runs on the configured schedule"
    prev = add_node(
        type="trigger",
        label="Start",
        description=trigger_desc,
        trigger_type=trigger_type,
    )

    # Research agent
    current = add_node(
        type="agent",
        label="Research & Gather Context",
        description="Collects relevant data from connected systems and institutional memory",
        agent_role="researcher",
    )
    edges.append(WorkflowEdge(id=f"e-{prev}-{current}", source=prev, target=current))
    prev = current

    # Actions for each integration
    for provider in integrations_found[:3]:  # Cap at 3 to keep it clean
        tools = REGISTRY.get_tools(provider)
        # Pick the most relevant tool (first write tool, or first read if all read)
        write_tools = [t for t in tools if not t.name.startswith(("get_", "list_", "search_"))]
        tool = write_tools[0] if write_tools else tools[0]

        risk = tool.risk_level
        needs_approval = risk in ("HIGH", "CRITICAL")

        if needs_approval:
            # Add approval before high-risk action
            approval = add_node(
                type="approval",
                label=f"Approve {provider.replace('_', ' ').title()} action",
                description=f"Human review required before {tool.name}",
                sla_minutes=30 if risk == "HIGH" else 60,
                risk_level=risk,
            )
            edges.append(WorkflowEdge(id=f"e-{prev}-{approval}", source=prev, target=approval))
            prev = approval

        current = add_node(
            type="action",
            label=f"{tool.name.replace('_', ' ').title()}",
            description=tool.description,
            provider=provider,
            tool_name=tool.name,
            risk_level=risk,
        )
        edges.append(WorkflowEdge(id=f"e-{prev}-{current}", source=prev, target=current))
        prev = current

    # Notification at the end if Slack is available
    if "slack" in integrations_found:
        current = add_node(
            type="action",
            label="Notify Team",
            description="Send completion notification to the team channel",
            provider="slack",
            tool_name="send_message",
            risk_level="LOW",
        )
        edges.append(WorkflowEdge(id=f"e-{prev}-{current}", source=prev, target=current))
        prev = current

    # Verification agent
    current = add_node(
        type="agent",
        label="Verify & Report",
        description="Confirms all actions completed successfully and generates a summary",
        agent_role="verifier",
    )
    edges.append(WorkflowEdge(id=f"e-{prev}-{current}", source=prev, target=current))

    # Determine overall risk
    risks = [n.risk_level for n in nodes if n.risk_level]
    overall = "LOW"
    if "CRITICAL" in risks:
        overall = "CRITICAL"
    elif "HIGH" in risks:
        overall = "HIGH"
    elif "MEDIUM" in risks:
        overall = "MEDIUM"

    return GeneratedWorkflow(
        name=f"Workflow: {description[:60]}",
        description=description,
        nodes=nodes,
        edges=edges,
        integrations_used=integrations_found,
        estimated_risk=overall,
    )
