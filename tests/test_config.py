"""Tests for Helix configuration."""


import pytest

from helix.config import Environment, Settings, get_settings


class TestSettings:
    """Test configuration loading from environment."""

    def test_default_settings(self) -> None:
        settings = Settings(_env_file=None)
        assert settings.environment == Environment.DEVELOPMENT
        assert settings.debug is False
        assert settings.compaction_threshold_pct == 83.5
        assert settings.circuit_breaker_failure_threshold == 3
        assert settings.dream_default_min_hours == 24
        assert settings.dream_default_min_sessions == 5
        assert settings.speculation_default_depth == 2

    def test_environment_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "a-very-long-production-secret-key")
        settings = Settings()
        assert settings.environment == Environment.PRODUCTION
        assert settings.secret_key == "a-very-long-production-secret-key"

    def test_database_url_default(self) -> None:
        settings = Settings()
        assert "asyncpg" in settings.database_url
        assert "helix" in settings.database_url

    def test_llm_defaults(self) -> None:
        settings = Settings()
        assert settings.default_primary_model == "claude-sonnet-4-6"
        assert settings.default_fallback_model == "claude-haiku-4-5"
        assert settings.default_embedding_model == "text-embedding-3-large"

    def test_dream_cycle_defaults(self) -> None:
        settings = Settings()
        assert settings.dream_cycle_enabled is True
        assert settings.dream_pii_strip_enabled is True

    def test_speculation_defaults(self) -> None:
        settings = Settings()
        assert settings.speculation_enabled is True
        assert settings.speculation_default_depth == 2

    def test_get_settings_factory(self) -> None:
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_secret_key_min_length(self) -> None:
        with pytest.raises(ValueError, match="String should have at least 16 characters"):
            Settings(secret_key="short")
