"""Tests for /usage/stats endpoint."""

import uuid

import pytest
from fastapi.testclient import TestClient

from helix.auth.tokens import create_token_claims, encode_token
from helix.main import app

client = TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    claims = create_token_claims(
        subject_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        roles=["admin"],
    )
    token = encode_token(claims)
    return {"Authorization": f"Bearer {token}"}


class TestUsageStats:
    def test_returns_correct_structure(self, auth_headers: dict[str, str]) -> None:
        r = client.get("/api/v1/usage/stats", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "total_input_tokens" in data
        assert "total_output_tokens" in data
        assert "total_cost_usd" in data
        assert "by_model" in data
        assert "by_workflow" in data
        assert isinstance(data["total_cost_usd"], float)

    def test_returns_401_without_auth(self) -> None:
        r = client.get("/api/v1/usage/stats")
        assert r.status_code == 401
