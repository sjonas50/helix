"""Tests for dynamic tool registry — provider lookup, risk filtering, schema generation."""

from helix.integrations.registry import TOOL_REGISTRIES, ToolRegistry


class TestToolRegistries:
    def test_all_10_providers_registered(self) -> None:
        expected = {
            "salesforce",
            "slack",
            "jira",
            "google_workspace",
            "hubspot",
            "servicenow",
            "zendesk",
            "github",
            "notion",
            "docusign",
        }
        assert set(TOOL_REGISTRIES.keys()) == expected

    def test_salesforce_tools_count(self) -> None:
        assert len(TOOL_REGISTRIES["salesforce"]) == 5

    def test_slack_tools_count(self) -> None:
        assert len(TOOL_REGISTRIES["slack"]) == 5

    def test_all_tools_have_required_fields(self) -> None:
        for provider, tools in TOOL_REGISTRIES.items():
            for tool in tools:
                assert tool.name, f"{provider} tool missing name"
                assert tool.description, f"{provider}/{tool.name} missing description"
                assert tool.risk_level in {
                    "LOW",
                    "MEDIUM",
                    "HIGH",
                    "CRITICAL",
                }, f"{provider}/{tool.name} has invalid risk_level={tool.risk_level}"

    def test_github_merge_is_critical(self) -> None:
        merge_tool = next(t for t in TOOL_REGISTRIES["github"] if t.name == "merge_pr")
        assert merge_tool.risk_level == "CRITICAL"
        assert merge_tool.requires_approval is True


class TestToolRegistryClass:
    def setup_method(self) -> None:
        self.registry = ToolRegistry()

    def test_tools_sorted_alphabetically(self) -> None:
        for provider in self.registry.get_all_providers():
            tools = self.registry.get_tools(provider)
            names = [t.name for t in tools]
            assert names == sorted(names), f"{provider} tools not sorted: {names}"

    def test_get_tools_by_risk_filter(self) -> None:
        low_only = self.registry.get_tools_by_risk("github", max_risk="LOW")
        assert all(t.risk_level == "LOW" for t in low_only)
        assert len(low_only) >= 2  # get_issue, list_prs

        up_to_medium = self.registry.get_tools_by_risk("github", max_risk="MEDIUM")
        assert all(t.risk_level in {"LOW", "MEDIUM"} for t in up_to_medium)
        assert len(up_to_medium) >= 3

    def test_tool_schema_for_prompt(self) -> None:
        schemas = self.registry.get_tool_schema_for_prompt("slack")
        assert len(schemas) == 5
        for s in schemas:
            assert "name" in s
            assert "description" in s
            assert "risk_level" in s
            assert "parameters" in s

    def test_get_all_providers(self) -> None:
        providers = self.registry.get_all_providers()
        assert len(providers) == 10
        # Should be sorted
        assert providers == sorted(providers)

    def test_unknown_provider_returns_empty(self) -> None:
        assert self.registry.get_tools("nonexistent") == []
