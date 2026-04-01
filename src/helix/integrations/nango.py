"""Nango integration adapter for OAuth token management and API execution.

Nango handles OAuth flows, token storage, and automatic refresh.
We call provider APIs directly using Nango-managed tokens via httpx.
"""
import time

import httpx
import structlog

from helix.config import get_settings
from helix.integrations.bus import ToolCallResult

logger = structlog.get_logger()

# Provider API base URLs
PROVIDER_BASE_URLS: dict[str, str] = {
    "salesforce": "https://{instance}.salesforce.com/services/data/v59.0",
    "slack": "https://slack.com/api",
    "jira": "https://{instance}.atlassian.net/rest/api/3",
    "github": "https://api.github.com",
    "hubspot": "https://api.hubapi.com",
    "zendesk": "https://{instance}.zendesk.com/api/v2",
    "notion": "https://api.notion.com/v1",
    "servicenow": "https://{instance}.service-now.com/api/now",
}


async def get_nango_token(provider: str, connection_id: str) -> str | None:
    """Fetch a fresh OAuth token from Nango.

    In production with Nango self-hosted:
        GET /connection/{connection_id}?provider_config_key={provider}
        Returns { access_token, ... }

    For development without Nango: returns None (use API key from env).
    """
    settings = get_settings()
    if not settings.nango_secret_key:
        logger.warning("nango.no_secret_key", msg="Using development mode — no real OAuth tokens")
        return None

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.nango.dev/connection/{connection_id}",
            headers={"Authorization": f"Bearer {settings.nango_secret_key}"},
            params={"provider_config_key": provider},
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("credentials", {}).get("access_token")
        logger.error("nango.token_failed", provider=provider, status=resp.status_code)
        return None


async def execute_tool(
    provider: str,
    tool_name: str,
    arguments: dict,
    connection_id: str | None = None,
    instance: str | None = None,
) -> ToolCallResult:
    """Execute an integration tool by calling the provider API directly.

    Uses Nango for token management, httpx for the actual API call.
    Falls back to stub response in development (no Nango key).
    """
    start = time.monotonic()

    token = await get_nango_token(provider, connection_id or "default") if connection_id else None

    if token is None:
        # Development mode: return mock response
        logger.info("tool.execute_dev", provider=provider, tool=tool_name)
        return ToolCallResult(
            tool_name=tool_name,
            output={"status": "mock", "provider": provider, "tool": tool_name, "arguments": arguments},
            risk_level="LOW",
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    # Build API call based on provider + tool
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Route to correct API endpoint based on tool name pattern
            if tool_name.startswith("get_") or tool_name.startswith("list_"):
                resp = await client.get(
                    _build_url(provider, tool_name, arguments, instance),
                    headers=headers,
                )
            else:
                resp = await client.post(
                    _build_url(provider, tool_name, arguments, instance),
                    headers=headers,
                    json=arguments,
                )

            duration = int((time.monotonic() - start) * 1000)

            if resp.status_code >= 400:
                return ToolCallResult(
                    tool_name=tool_name,
                    output={},
                    risk_level="LOW",
                    duration_ms=duration,
                    error=f"API error {resp.status_code}: {resp.text[:200]}",
                    success=False,
                )

            return ToolCallResult(
                tool_name=tool_name,
                output=(
                    resp.json()
                    if resp.headers.get("content-type", "").startswith("application/json")
                    else {"text": resp.text}
                ),
                risk_level="LOW",
                duration_ms=duration,
            )
    except httpx.HTTPError as e:
        return ToolCallResult(
            tool_name=tool_name,
            output={},
            risk_level="LOW",
            duration_ms=int((time.monotonic() - start) * 1000),
            error=str(e),
            success=False,
        )


def _build_url(provider: str, tool_name: str, arguments: dict, instance: str | None) -> str:
    """Build provider API URL from tool name and arguments."""
    # Generic URL builder — maps tool_name to REST endpoint
    base = PROVIDER_BASE_URLS.get(provider, "")
    if instance and "{instance}" in base:
        base = base.replace("{instance}", instance)

    # Convention: tool_name like "get_account" → GET /account/{id}
    # tool_name like "list_opportunities" → GET /opportunities
    parts = tool_name.split("_", 1)
    if len(parts) == 2:
        resource = parts[1]
        record_id = arguments.get("id", "")
        if record_id:
            return f"{base}/{resource}/{record_id}"
        return f"{base}/{resource}"
    return base


async def initiate_oauth(provider: str, org_id: str, redirect_uri: str) -> str:
    """Generate Nango OAuth connection URL."""
    settings = get_settings()
    from urllib.parse import quote, urlencode

    if settings.nango_public_key:
        params = urlencode({
            "connection_id": f"{org_id}",
            "provider_config_key": provider,
            "public_key": settings.nango_public_key,
        })
        return f"https://api.nango.dev/oauth/connect/{quote(provider)}?{params}"

    # Fallback for development
    return f"https://api.nango.dev/oauth/connect/{quote(provider)}?org_id={org_id}"
