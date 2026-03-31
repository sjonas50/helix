"""Tests for API routes."""

from fastapi.testclient import TestClient

from helix.main import app

client = TestClient(app)


class TestHealthRoute:
    def test_health(self) -> None:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


class TestOrgRoutes:
    def test_create_org(self) -> None:
        r = client.post(
            "/api/v1/orgs/",
            json={"name": "Acme Corp", "slug": "acme-corp"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Acme Corp"
        assert data["slug"] == "acme-corp"
        assert data["plan"] == "enterprise"
        assert data["status"] == "active"

    def test_create_org_invalid_slug(self) -> None:
        r = client.post(
            "/api/v1/orgs/",
            json={"name": "Test", "slug": "Invalid Slug!"},
        )
        assert r.status_code == 422

    def test_get_org_not_found(self) -> None:
        r = client.get("/api/v1/orgs/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404


class TestWorkflowRoutes:
    def test_list_workflows_empty(self) -> None:
        r = client.get("/api/v1/workflows/")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_workflow_not_implemented(self) -> None:
        r = client.post("/api/v1/workflows/", json={})
        assert r.status_code == 501


class TestMemoryRoutes:
    def test_search_memory_empty(self) -> None:
        r = client.post("/api/v1/memory/search", json={"query": "test"})
        assert r.status_code == 200
        assert r.json() == []

    def test_list_dream_runs_empty(self) -> None:
        r = client.get("/api/v1/memory/dream-runs")
        assert r.status_code == 200
        assert r.json() == []


class TestApprovalRoutes:
    def test_list_approvals_empty(self) -> None:
        r = client.get("/api/v1/approvals/")
        assert r.status_code == 200
        assert r.json() == []

    def test_decide_approval_not_found(self) -> None:
        r = client.post(
            "/api/v1/approvals/00000000-0000-0000-0000-000000000000/decide",
            json={"decision": "APPROVED", "reason": "test"},
        )
        assert r.status_code == 404
