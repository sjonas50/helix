"""Tests for enterprise agent skill definitions."""

from helix.integrations.skills import (
    SKILLS,
    get_skill,
    get_skills_by_category,
    get_skills_for_integrations,
)


class TestSkillDefinitions:
    def test_all_10_skills_defined(self) -> None:
        assert len(SKILLS) == 10

    def test_get_skill_by_name(self) -> None:
        skill = get_skill("draft_email")
        assert skill is not None
        assert skill.category == "sales"
        assert skill.requires_approval is True

    def test_get_skill_not_found(self) -> None:
        assert get_skill("nonexistent") is None

    def test_get_skills_by_category(self) -> None:
        sales = get_skills_by_category("sales")
        assert len(sales) == 2
        assert all(s.category == "sales" for s in sales)

    def test_skill_categories_covered(self) -> None:
        categories = {s.category for s in SKILLS}
        expected = {"sales", "support", "ops", "hr", "finance", "devops"}
        assert categories == expected

    def test_skills_for_available_integrations(self) -> None:
        # Only Slack + Google Workspace available
        available = ["slack", "google_workspace"]
        skills = get_skills_for_integrations(available)
        names = {s.name for s in skills}
        assert "summarize_thread" in names
        assert "schedule_meeting" in names
        # draft_email requires salesforce — should NOT be included
        assert "draft_email" not in names

    def test_skills_for_all_integrations(self) -> None:
        all_integrations = [
            "slack",
            "google_workspace",
            "salesforce",
            "hubspot",
            "zendesk",
            "jira",
            "github",
            "servicenow",
        ]
        skills = get_skills_for_integrations(all_integrations)
        assert len(skills) == 10

    def test_all_skills_have_required_fields(self) -> None:
        for skill in SKILLS:
            assert skill.name
            assert skill.description
            assert len(skill.required_integrations) >= 1
            assert len(skill.tools_used) >= 1
            assert skill.risk_level in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
            assert skill.category in {
                "sales",
                "support",
                "ops",
                "hr",
                "finance",
                "devops",
            }
