"""Enterprise agent skill definitions.

Skills are high-level capabilities composed from multiple tools + LLM calls.
Each skill defines what it does, which integrations it needs, and approval requirements.
"""

import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


class AgentSkill(BaseModel):
    """Definition of an agent skill."""

    name: str
    description: str
    required_integrations: list[str]
    tools_used: list[str]
    risk_level: str  # Overall risk of the skill
    requires_approval: bool
    category: str  # sales | support | ops | hr | finance | devops


# ---------------------------------------------------------------------------
# 10 enterprise skills
# ---------------------------------------------------------------------------

SKILLS: list[AgentSkill] = [
    AgentSkill(
        name="summarize_thread",
        description="Summarize a Slack thread or email chain into key points and action items",
        required_integrations=["slack", "google_workspace"],
        tools_used=["search_messages", "send_email"],
        risk_level="LOW",
        requires_approval=False,
        category="ops",
    ),
    AgentSkill(
        name="draft_email",
        description="Draft a contextual email using CRM data and conversation history",
        required_integrations=["salesforce", "google_workspace"],
        tools_used=["get_account", "list_opportunities", "send_email"],
        risk_level="MEDIUM",
        requires_approval=True,
        category="sales",
    ),
    AgentSkill(
        name="score_lead",
        description="Score an inbound lead using firmographic and behavioral data",
        required_integrations=["salesforce", "hubspot"],
        tools_used=["get_contact", "list_deals"],
        risk_level="LOW",
        requires_approval=False,
        category="sales",
    ),
    AgentSkill(
        name="create_report",
        description="Generate a weekly/monthly report from multiple data sources",
        required_integrations=["salesforce", "google_workspace"],
        tools_used=["list_opportunities", "create_doc"],
        risk_level="LOW",
        requires_approval=False,
        category="ops",
    ),
    AgentSkill(
        name="route_ticket",
        description="Classify and route a support ticket to the correct team",
        required_integrations=["zendesk", "slack"],
        tools_used=["get_ticket", "update_ticket", "send_message"],
        risk_level="MEDIUM",
        requires_approval=False,
        category="support",
    ),
    AgentSkill(
        name="schedule_meeting",
        description="Find availability and schedule a meeting across calendars",
        required_integrations=["google_workspace", "slack"],
        tools_used=["create_event", "send_message"],
        risk_level="LOW",
        requires_approval=False,
        category="ops",
    ),
    AgentSkill(
        name="onboard_user",
        description="Multi-system user provisioning: create accounts across HR, Slack, Jira, GitHub",
        required_integrations=["slack", "jira", "github"],
        tools_used=["invite_to_channel", "create_issue", "create_issue"],
        risk_level="HIGH",
        requires_approval=True,
        category="hr",
    ),
    AgentSkill(
        name="detect_churn_risk",
        description="Monitor usage and sentiment signals to identify at-risk accounts",
        required_integrations=["salesforce", "zendesk"],
        tools_used=["get_account", "list_tickets"],
        risk_level="LOW",
        requires_approval=False,
        category="support",
    ),
    AgentSkill(
        name="process_invoice",
        description="Extract invoice fields, match to PO, route for approval, and post",
        required_integrations=["google_workspace", "slack"],
        tools_used=["list_files", "send_message"],
        risk_level="HIGH",
        requires_approval=True,
        category="finance",
    ),
    AgentSkill(
        name="incident_response",
        description="Alert triage: create ticket, notify on-call, escalate if needed, create postmortem",
        required_integrations=["servicenow", "slack", "google_workspace"],
        tools_used=["create_incident", "send_message", "create_doc"],
        risk_level="HIGH",
        requires_approval=True,
        category="devops",
    ),
]


def get_skill(name: str) -> AgentSkill | None:
    """Get a skill by name."""
    return next((s for s in SKILLS if s.name == name), None)


def get_skills_by_category(category: str) -> list[AgentSkill]:
    """Get all skills in a given category."""
    return [s for s in SKILLS if s.category == category]


def get_skills_for_integrations(available_integrations: list[str]) -> list[AgentSkill]:
    """Return skills that can be executed with the given set of integrations."""
    available = set(available_integrations)
    return [s for s in SKILLS if set(s.required_integrations).issubset(available)]
