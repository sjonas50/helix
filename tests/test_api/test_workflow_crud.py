"""Tests for workflow CRUD API endpoints."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

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


class TestDeployWorkflow:
    @patch("helix.api.routes.workflows.get_session_factory")
    def test_deploy_workflow_creates_record(
        self, mock_factory: MagicMock, auth_headers: dict
    ) -> None:
        mock_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = MagicMock(return_value=mock_session_ctx)

        r = client.post(
            "/api/v1/workflows/deploy",
            json={
                "name": "Test Workflow",
                "description": "A test",
                "workflow_json": '{"name":"test","description":"d","nodes":[],"edges":[]}',
            },
            headers=auth_headers,
        )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Test Workflow"
        assert data["status"] == "PLANNING"
        assert "id" in data

    def test_deploy_workflow_requires_auth(self) -> None:
        r = client.post(
            "/api/v1/workflows/deploy",
            json={"name": "Test", "workflow_json": "{}"},
        )
        assert r.status_code == 401


class TestRunWorkflow:
    @patch("helix.api.routes.workflows.get_session_factory")
    def test_run_not_found(self, mock_factory: MagicMock, auth_headers: dict) -> None:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = MagicMock(return_value=mock_session_ctx)

        wf_id = str(uuid.uuid4())
        r = client.post(f"/api/v1/workflows/{wf_id}/run", headers=auth_headers)
        assert r.status_code == 404

    @patch("helix.workers.workflow_tasks.execute_workflow_task.delay")
    @patch("helix.api.routes.workflows.get_session_factory")
    def test_run_dispatches_to_celery(
        self, mock_factory: MagicMock, mock_delay: MagicMock, auth_headers: dict
    ) -> None:
        wf_id = str(uuid.uuid4())
        mock_session = AsyncMock()

        # First call: SELECT (find workflow)
        mock_select_result = MagicMock()
        mock_select_result.fetchone.return_value = (
            wf_id,
            str(uuid.uuid4()),
            "PLANNING",
            {"workflow": '{"nodes":[],"edges":[]}'},
        )

        mock_session.execute = AsyncMock(return_value=mock_select_result)
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = MagicMock(return_value=mock_session_ctx)

        r = client.post(f"/api/v1/workflows/{wf_id}/run", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "EXECUTING"
        assert data["message"] == "Workflow dispatched for execution"

        mock_delay.assert_called_once()

    @patch("helix.api.routes.workflows.get_session_factory")
    def test_run_rejects_already_executing(
        self, mock_factory: MagicMock, auth_headers: dict
    ) -> None:
        wf_id = str(uuid.uuid4())
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (
            wf_id,
            str(uuid.uuid4()),
            "EXECUTING",
            {},
        )
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = MagicMock(return_value=mock_session_ctx)

        r = client.post(f"/api/v1/workflows/{wf_id}/run", headers=auth_headers)
        assert r.status_code == 409


class TestGetWorkflow:
    @patch("helix.api.routes.workflows.get_session_factory")
    def test_get_not_found(self, mock_factory: MagicMock, auth_headers: dict) -> None:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = MagicMock(return_value=mock_session_ctx)

        wf_id = str(uuid.uuid4())
        r = client.get(f"/api/v1/workflows/{wf_id}", headers=auth_headers)
        assert r.status_code == 404

    def test_get_workflow_requires_auth(self) -> None:
        wf_id = str(uuid.uuid4())
        r = client.get(f"/api/v1/workflows/{wf_id}")
        assert r.status_code == 401


class TestListWorkflows:
    @patch("helix.api.routes.workflows.get_session_factory")
    def test_list_returns_empty(self, mock_factory: MagicMock, auth_headers: dict) -> None:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = MagicMock(return_value=mock_session_ctx)

        r = client.get("/api/v1/workflows/", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == []
