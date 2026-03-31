"""Dynamic tool registry — loads tool definitions per (org_id, integration_id).

Alphabetical sort for prompt cache optimization (from Claude Code).
"""

import structlog

from helix.integrations.bus import SALESFORCE_TOOLS, IntegrationTool

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Static tool registries per provider
# ---------------------------------------------------------------------------

SLACK_TOOLS: list[IntegrationTool] = [
    IntegrationTool(
        name="send_message",
        description="Send a message to a Slack channel or user",
        risk_level="LOW",
        parallel_safe=True,
        idempotent=False,
    ),
    IntegrationTool(
        name="list_channels",
        description="List available Slack channels",
        risk_level="LOW",
        parallel_safe=True,
        idempotent=True,
    ),
    IntegrationTool(
        name="search_messages",
        description="Search Slack messages by keyword or filter",
        risk_level="LOW",
        parallel_safe=True,
        idempotent=True,
    ),
    IntegrationTool(
        name="create_channel",
        description="Create a new Slack channel",
        risk_level="MEDIUM",
        parallel_safe=False,
        idempotent=False,
    ),
    IntegrationTool(
        name="invite_to_channel",
        description="Invite a user to a Slack channel",
        risk_level="MEDIUM",
        parallel_safe=False,
        idempotent=False,
    ),
]

JIRA_TOOLS: list[IntegrationTool] = [
    IntegrationTool(
        name="get_issue",
        description="Retrieve a Jira issue by key",
        risk_level="LOW",
        parallel_safe=True,
        idempotent=True,
    ),
    IntegrationTool(
        name="list_issues",
        description="List Jira issues with JQL filter",
        risk_level="LOW",
        parallel_safe=True,
        idempotent=True,
    ),
    IntegrationTool(
        name="create_issue",
        description="Create a new Jira issue",
        risk_level="MEDIUM",
        parallel_safe=False,
        idempotent=False,
    ),
    IntegrationTool(
        name="update_issue",
        description="Update fields on an existing Jira issue",
        risk_level="MEDIUM",
        parallel_safe=False,
        idempotent=False,
    ),
    IntegrationTool(
        name="transition_issue",
        description="Transition a Jira issue to a new status",
        risk_level="HIGH",
        requires_approval=True,
        parallel_safe=False,
        idempotent=False,
    ),
]

GOOGLE_WORKSPACE_TOOLS: list[IntegrationTool] = [
    IntegrationTool(
        name="send_email",
        description="Send an email via Gmail",
        risk_level="MEDIUM",
        parallel_safe=False,
        idempotent=False,
    ),
    IntegrationTool(
        name="create_doc",
        description="Create a new Google Doc",
        risk_level="LOW",
        parallel_safe=False,
        idempotent=False,
    ),
    IntegrationTool(
        name="list_files",
        description="List files in Google Drive",
        risk_level="LOW",
        parallel_safe=True,
        idempotent=True,
    ),
    IntegrationTool(
        name="create_event",
        description="Create a Google Calendar event",
        risk_level="LOW",
        parallel_safe=False,
        idempotent=False,
    ),
    IntegrationTool(
        name="share_file",
        description="Share a Google Drive file with a user or group",
        risk_level="MEDIUM",
        parallel_safe=False,
        idempotent=False,
    ),
]

HUBSPOT_TOOLS: list[IntegrationTool] = [
    IntegrationTool(
        name="get_contact",
        description="Retrieve a HubSpot contact by ID or email",
        risk_level="LOW",
        parallel_safe=True,
        idempotent=True,
    ),
    IntegrationTool(
        name="list_deals",
        description="List HubSpot deals with optional filters",
        risk_level="LOW",
        parallel_safe=True,
        idempotent=True,
    ),
    IntegrationTool(
        name="create_contact",
        description="Create a new contact in HubSpot",
        risk_level="MEDIUM",
        parallel_safe=False,
        idempotent=False,
    ),
    IntegrationTool(
        name="update_deal",
        description="Update a HubSpot deal stage or properties",
        risk_level="HIGH",
        requires_approval=True,
        parallel_safe=False,
        idempotent=False,
    ),
    IntegrationTool(
        name="create_task",
        description="Create a task in HubSpot CRM",
        risk_level="LOW",
        parallel_safe=False,
        idempotent=False,
    ),
]

SERVICENOW_TOOLS: list[IntegrationTool] = [
    IntegrationTool(
        name="get_incident",
        description="Retrieve a ServiceNow incident by ID",
        risk_level="LOW",
        parallel_safe=True,
        idempotent=True,
    ),
    IntegrationTool(
        name="list_incidents",
        description="List ServiceNow incidents with filters",
        risk_level="LOW",
        parallel_safe=True,
        idempotent=True,
    ),
    IntegrationTool(
        name="create_incident",
        description="Create a new ServiceNow incident",
        risk_level="MEDIUM",
        parallel_safe=False,
        idempotent=False,
    ),
    IntegrationTool(
        name="update_incident",
        description="Update a ServiceNow incident",
        risk_level="MEDIUM",
        parallel_safe=False,
        idempotent=False,
    ),
    IntegrationTool(
        name="assign_incident",
        description="Reassign a ServiceNow incident to a different team or individual",
        risk_level="HIGH",
        requires_approval=True,
        parallel_safe=False,
        idempotent=False,
    ),
]

ZENDESK_TOOLS: list[IntegrationTool] = [
    IntegrationTool(
        name="get_ticket",
        description="Retrieve a Zendesk support ticket by ID",
        risk_level="LOW",
        parallel_safe=True,
        idempotent=True,
    ),
    IntegrationTool(
        name="list_tickets",
        description="List Zendesk tickets with filters",
        risk_level="LOW",
        parallel_safe=True,
        idempotent=True,
    ),
    IntegrationTool(
        name="create_ticket",
        description="Create a new Zendesk support ticket",
        risk_level="MEDIUM",
        parallel_safe=False,
        idempotent=False,
    ),
    IntegrationTool(
        name="update_ticket",
        description="Update a Zendesk ticket status or fields",
        risk_level="MEDIUM",
        parallel_safe=False,
        idempotent=False,
    ),
    IntegrationTool(
        name="add_comment",
        description="Add a comment to a Zendesk ticket",
        risk_level="LOW",
        parallel_safe=False,
        idempotent=False,
    ),
]

GITHUB_TOOLS: list[IntegrationTool] = [
    IntegrationTool(
        name="get_issue",
        description="Retrieve a GitHub issue by number",
        risk_level="LOW",
        parallel_safe=True,
        idempotent=True,
    ),
    IntegrationTool(
        name="list_prs",
        description="List pull requests for a GitHub repository",
        risk_level="LOW",
        parallel_safe=True,
        idempotent=True,
    ),
    IntegrationTool(
        name="create_issue",
        description="Create a new GitHub issue",
        risk_level="MEDIUM",
        parallel_safe=False,
        idempotent=False,
    ),
    IntegrationTool(
        name="create_pr",
        description="Create a new pull request on GitHub",
        risk_level="HIGH",
        requires_approval=True,
        parallel_safe=False,
        idempotent=False,
    ),
    IntegrationTool(
        name="merge_pr",
        description="Merge a pull request on GitHub (irreversible)",
        risk_level="CRITICAL",
        requires_approval=True,
        parallel_safe=False,
        idempotent=False,
    ),
]

NOTION_TOOLS: list[IntegrationTool] = [
    IntegrationTool(
        name="search_pages",
        description="Search Notion pages by title or content",
        risk_level="LOW",
        parallel_safe=True,
        idempotent=True,
    ),
    IntegrationTool(
        name="get_page",
        description="Retrieve a Notion page by ID",
        risk_level="LOW",
        parallel_safe=True,
        idempotent=True,
    ),
    IntegrationTool(
        name="create_page",
        description="Create a new Notion page",
        risk_level="MEDIUM",
        parallel_safe=False,
        idempotent=False,
    ),
    IntegrationTool(
        name="update_page",
        description="Update an existing Notion page",
        risk_level="MEDIUM",
        parallel_safe=False,
        idempotent=False,
    ),
    IntegrationTool(
        name="add_to_database",
        description="Add a new entry to a Notion database",
        risk_level="MEDIUM",
        parallel_safe=False,
        idempotent=False,
    ),
]

DOCUSIGN_TOOLS: list[IntegrationTool] = [
    IntegrationTool(
        name="get_envelope_status",
        description="Get the status of a DocuSign envelope",
        risk_level="LOW",
        parallel_safe=True,
        idempotent=True,
    ),
    IntegrationTool(
        name="list_envelopes",
        description="List DocuSign envelopes with filters",
        risk_level="LOW",
        parallel_safe=True,
        idempotent=True,
    ),
    IntegrationTool(
        name="send_envelope",
        description="Send a DocuSign envelope for signature",
        risk_level="HIGH",
        requires_approval=True,
        parallel_safe=False,
        idempotent=False,
    ),
    IntegrationTool(
        name="void_envelope",
        description="Void a DocuSign envelope (irreversible)",
        risk_level="CRITICAL",
        requires_approval=True,
        parallel_safe=False,
        idempotent=False,
    ),
]

# ---------------------------------------------------------------------------
# Master registry
# ---------------------------------------------------------------------------

TOOL_REGISTRIES: dict[str, list[IntegrationTool]] = {
    "salesforce": SALESFORCE_TOOLS,
    "slack": SLACK_TOOLS,
    "jira": JIRA_TOOLS,
    "google_workspace": GOOGLE_WORKSPACE_TOOLS,
    "hubspot": HUBSPOT_TOOLS,
    "servicenow": SERVICENOW_TOOLS,
    "zendesk": ZENDESK_TOOLS,
    "github": GITHUB_TOOLS,
    "notion": NOTION_TOOLS,
    "docusign": DOCUSIGN_TOOLS,
}


# ---------------------------------------------------------------------------
# ToolRegistry class
# ---------------------------------------------------------------------------


class ToolRegistry:
    """Manages tool definitions per org with provider lookup."""

    def get_tools(self, provider: str) -> list[IntegrationTool]:
        """Get tools for a provider, sorted alphabetically for cache optimization."""
        tools = TOOL_REGISTRIES.get(provider, [])
        return sorted(tools, key=lambda t: t.name)

    def get_all_providers(self) -> list[str]:
        """List all supported providers."""
        return sorted(TOOL_REGISTRIES.keys())

    def get_tools_by_risk(self, provider: str, max_risk: str) -> list[IntegrationTool]:
        """Get tools filtered by maximum risk level."""
        risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        max_level = risk_order.get(max_risk, 3)
        return [t for t in self.get_tools(provider) if risk_order.get(t.risk_level, 0) <= max_level]

    def get_tool_schema_for_prompt(self, provider: str) -> list[dict]:
        """Generate tool schemas for LLM system prompt injection."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "risk_level": t.risk_level,
                "parameters": t.parameters_schema,
            }
            for t in self.get_tools(provider)
        ]
