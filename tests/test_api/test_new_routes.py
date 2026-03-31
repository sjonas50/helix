"""Tests for Phase 13 API routes: agents, integrations, audit."""

import uuid

import pytest
from fastapi.testclient import TestClient

from helix.auth.tokens import create_token_claims, encode_token
from helix.main import app

client = TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Generate valid auth headers for testing."""
    claims = create_token_claims(
        subject_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        roles=["admin"],
    )
    token = encode_token(claims)
    return {"Authorization": f"Bearer {token}"}


# ---- Agent routes ----


class TestAgentRoutes:
    def test_list_agents_empty(self, auth_headers: dict) -> None:
        wf_id = uuid.uuid4()
        r = client.get(f"/api/v1/agents/workflow/{wf_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == []

    def test_get_agent_not_found(self, auth_headers: dict) -> None:
        agent_id = uuid.uuid4()
        r = client.get(f"/api/v1/agents/{agent_id}", headers=auth_headers)
        assert r.status_code == 404

    def test_get_agent_messages_empty(self, auth_headers: dict) -> None:
        agent_id = uuid.uuid4()
        r = client.get(f"/api/v1/agents/{agent_id}/messages", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == []


# ---- Integration routes ----


class TestIntegrationRoutes:
    def test_list_integrations_empty(self, auth_headers: dict) -> None:
        r = client.get("/api/v1/integrations/", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == []

    def test_list_providers_returns_list(self, auth_headers: dict) -> None:
        r = client.get("/api/v1/integrations/providers", headers=auth_headers)
        assert r.status_code == 200
        providers = r.json()
        assert isinstance(providers, list)
        assert len(providers) > 0
        # Providers from registry should be sorted strings
        assert all(isinstance(p, str) for p in providers)

    def test_get_integration_not_found(self, auth_headers: dict) -> None:
        integration_id = uuid.uuid4()
        r = client.get(
            f"/api/v1/integrations/{integration_id}", headers=auth_headers
        )
        assert r.status_code == 404

    def test_add_integration_not_implemented(self, auth_headers: dict) -> None:
        r = client.post(
            "/api/v1/integrations/",
            json={"provider": "slack", "connector_type": "composio", "config": {}},
            headers=auth_headers,
        )
        assert r.status_code == 501

    def test_delete_integration_not_found(self, auth_headers: dict) -> None:
        integration_id = uuid.uuid4()
        r = client.delete(
            f"/api/v1/integrations/{integration_id}", headers=auth_headers
        )
        assert r.status_code == 404

    def test_list_integration_tools_empty(self, auth_headers: dict) -> None:
        integration_id = uuid.uuid4()
        r = client.get(
            f"/api/v1/integrations/{integration_id}/tools", headers=auth_headers
        )
        assert r.status_code == 200
        assert r.json() == []


# ---- Audit routes ----


class TestAuditRoutes:
    def test_audit_events_empty(self, auth_headers: dict) -> None:
        r = client.get("/api/v1/audit/events", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["events"] == []
        assert data["total"] == 0

    def test_audit_integrity_ok(self, auth_headers: dict) -> None:
        r = client.get("/api/v1/audit/integrity", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["chain_valid"] is True

    def test_get_audit_event_not_found(self, auth_headers: dict) -> None:
        event_id = uuid.uuid4()
        r = client.get(f"/api/v1/audit/events/{event_id}", headers=auth_headers)
        assert r.status_code == 404


# ---- Auth enforcement on new routes ----


class TestUnauthenticatedAccess:
    def test_unauthenticated_agents_401(self) -> None:
        wf_id = uuid.uuid4()
        r = client.get(f"/api/v1/agents/workflow/{wf_id}")
        assert r.status_code == 401

    def test_unauthenticated_integrations_401(self) -> None:
        r = client.get("/api/v1/integrations/")
        assert r.status_code == 401

    def test_unauthenticated_audit_401(self) -> None:
        r = client.get("/api/v1/audit/events")
        assert r.status_code == 401
