"""Composio SDK adapter for managed SaaS connectors.

Composio provides 250+ managed connectors. This adapter normalizes
their API into Helix's IntegrationTool model.
"""

from typing import Any

import structlog

from helix.config import get_settings
from helix.integrations.bus import IntegrationTool, ToolCallResult

logger = structlog.get_logger()


async def get_composio_tools(provider: str) -> list[IntegrationTool]:
    """Fetch available tools from Composio for a provider.

    In production, calls composio SDK:
        from composio import ComposioToolSet
        toolset = ComposioToolSet(api_key=settings.composio_api_key)
        actions = toolset.get_actions(apps=[provider])
    """
    settings = get_settings()
    if not settings.composio_api_key:
        logger.warning("composio.no_api_key", provider=provider)
        return []

    # In production: return real Composio tools
    logger.info("composio.get_tools", provider=provider)
    return []


async def execute_composio_tool(
    provider: str,
    tool_name: str,
    arguments: dict[str, Any],
    connection_id: str | None = None,
) -> ToolCallResult:
    """Execute a tool via Composio SDK.

    In production:
        result = toolset.execute_action(
            action=tool_name, params=arguments, entity_id=connection_id
        )
    """
    logger.info("composio.execute", provider=provider, tool=tool_name)

    # Stub: return success for development
    return ToolCallResult(
        tool_name=tool_name,
        output={"status": "executed_via_composio", "provider": provider},
        risk_level="LOW",
    )


async def initiate_oauth(provider: str, org_id: str, redirect_uri: str) -> str:
    """Initiate OAuth flow for connecting an integration via Composio."""
    logger.info("composio.oauth_initiate", provider=provider, org_id=org_id)
    return f"https://app.composio.dev/oauth/{provider}?org_id={org_id}&redirect_uri={redirect_uri}"
