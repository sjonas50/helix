"""Tests for API routes with authentication."""

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


class TestHealthRoute:
    def test_health_no_auth_required(self) -> None:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


class TestAuthEnforcement:
    def test_unauthenticated_request_returns_401(self) -> None:
        r = client.get("/api/v1/workflows/")
        assert r.status_code == 401

    def test_invalid_token_returns_401(self) -> None:
        r = client.get(
            "/api/v1/workflows/",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert r.status_code == 401

    def test_authenticated_request_succeeds(self, auth_headers: dict) -> None:
        r = client.get("/api/v1/workflows/", headers=auth_headers)
        assert r.status_code == 200


class TestOrgRoutes:
    def test_create_org(self, auth_headers: dict) -> None:
        r = client.post(
            "/api/v1/orgs/",
            json={"name": "Acme Corp", "slug": "acme-corp"},
            headers=auth_headers,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Acme Corp"
        assert data["slug"] == "acme-corp"
        assert data["plan"] == "enterprise"

    def test_create_org_invalid_slug(self, auth_headers: dict) -> None:
        r = client.post(
            "/api/v1/orgs/",
            json={"name": "Test", "slug": "Invalid Slug!"},
            headers=auth_headers,
        )
        assert r.status_code == 422

    def test_get_org_not_found(self, auth_headers: dict) -> None:
        r = client.get(
            "/api/v1/orgs/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert r.status_code == 404


class TestWorkflowRoutes:
    def test_list_workflows_empty(self, auth_headers: dict) -> None:
        r = client.get("/api/v1/workflows/", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == []

    def test_create_workflow_not_implemented(self, auth_headers: dict) -> None:
        r = client.post("/api/v1/workflows/", json={}, headers=auth_headers)
        assert r.status_code == 501


class TestMemoryRoutes:
    def test_search_memory_empty(self, auth_headers: dict) -> None:
        r = client.post(
            "/api/v1/memory/search",
            json={"query": "test"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json() == []

    def test_list_dream_runs_empty(self, auth_headers: dict) -> None:
        r = client.get("/api/v1/memory/dream-runs", headers=auth_headers)
        assert r.status_code == 200


class TestApprovalRoutes:
    def test_list_approvals_empty(self, auth_headers: dict) -> None:
        r = client.get("/api/v1/approvals/", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == []

    def test_decide_approval_not_found(self, auth_headers: dict) -> None:
        r = client.post(
            "/api/v1/approvals/00000000-0000-0000-0000-000000000000/decide",
            json={"decision": "APPROVED", "reason": "test"},
            headers=auth_headers,
        )
        assert r.status_code == 404
