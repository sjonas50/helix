import pytest

from helix.integrations.nango import (
    _build_url,
    execute_tool,
    get_nango_token,
    initiate_oauth,
)


class TestGetNangoToken:
    @pytest.mark.asyncio
    async def test_returns_none_without_secret_key(self):
        # Default settings have empty nango_secret_key
        token = await get_nango_token("salesforce", "conn_123")
        assert token is None

    def test_build_url_get_account(self):
        url = _build_url("github", "get_issue", {"id": "42"}, None)
        assert "issue/42" in url

    def test_build_url_list(self):
        url = _build_url("github", "list_prs", {}, None)
        assert "prs" in url


class TestExecuteTool:
    @pytest.mark.asyncio
    async def test_dev_mode_returns_mock(self):
        result = await execute_tool("salesforce", "get_account", {"id": "123"})
        assert result.output["status"] == "mock"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_dev_mode_includes_tool_name(self):
        result = await execute_tool("slack", "send_message", {"channel": "#general"})
        assert result.tool_name == "send_message"


class TestInitiateOAuth:
    @pytest.mark.asyncio
    async def test_returns_nango_url(self):
        url = await initiate_oauth("salesforce", "org_123", "https://app.helix.dev/callback")
        assert "nango.dev" in url
        assert "salesforce" in url
