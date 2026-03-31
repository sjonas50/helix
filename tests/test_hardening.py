"""Hardening tests — security audit, observability setup, deployment config."""

import os

import pytest

from helix.config import Environment, Settings
from helix.observability import init_observability, setup_logging


class TestSecurityAudit:
    """Verify no hardcoded secrets or security anti-patterns."""

    def test_no_hardcoded_api_keys_in_source(self) -> None:
        """Scan source files for hardcoded API keys."""
        import re

        key_patterns = [
            r"sk-[a-zA-Z0-9]{20,}",  # OpenAI
            r"sk-ant-[a-zA-Z0-9]{20,}",  # Anthropic
            r"xoxb-[a-zA-Z0-9-]+",  # Slack bot token
        ]
        src_dir = os.path.join(os.path.dirname(__file__), "..", "src")

        for root, _dirs, files in os.walk(src_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath) as f:
                    content = f.read()
                for pattern in key_patterns:
                    matches = re.findall(pattern, content)
                    assert not matches, f"Possible hardcoded key in {fpath}: {matches[0][:10]}..."

    def test_env_file_not_committed(self) -> None:
        """Verify .env is in .gitignore."""
        gitignore = os.path.join(os.path.dirname(__file__), "..", ".gitignore")
        with open(gitignore) as f:
            content = f.read()
        assert ".env" in content

    def test_secret_key_has_minimum_length(self) -> None:
        """Ensure secret key validation enforces minimum length."""
        with pytest.raises(ValueError):
            Settings(_env_file=None, secret_key="short")

    def test_default_secret_key_not_production_safe(self) -> None:
        """Default key contains 'change-me' — must be overridden in production."""
        settings = Settings(_env_file=None)
        assert "change-me" in settings.secret_key


class TestObservability:
    def test_setup_logging_dev(self) -> None:
        settings = Settings(_env_file=None, environment=Environment.DEVELOPMENT)
        setup_logging(settings)  # Should not raise

    def test_setup_logging_production(self) -> None:
        settings = Settings(_env_file=None, environment=Environment.PRODUCTION, secret_key="a-long-production-secret-key-here")
        setup_logging(settings)  # Should not raise

    def test_init_observability_no_crash(self) -> None:
        settings = Settings(_env_file=None)
        init_observability(settings)  # Should not raise even without Sentry/OTEL


class TestDeploymentConfig:
    def test_dockerfile_exists(self) -> None:
        assert os.path.exists(
            os.path.join(os.path.dirname(__file__), "..", "Dockerfile")
        )

    def test_docker_compose_exists(self) -> None:
        assert os.path.exists(
            os.path.join(os.path.dirname(__file__), "..", "docker-compose.yml")
        )

    def test_helm_chart_exists(self) -> None:
        chart = os.path.join(
            os.path.dirname(__file__), "..", "deploy", "helm", "helix", "Chart.yaml"
        )
        assert os.path.exists(chart)

    def test_helm_values_exists(self) -> None:
        values = os.path.join(
            os.path.dirname(__file__), "..", "deploy", "helm", "helix", "values.yaml"
        )
        assert os.path.exists(values)

    def test_alembic_ini_exists(self) -> None:
        assert os.path.exists(
            os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
        )

    def test_env_example_exists(self) -> None:
        assert os.path.exists(
            os.path.join(os.path.dirname(__file__), "..", ".env.example")
        )
