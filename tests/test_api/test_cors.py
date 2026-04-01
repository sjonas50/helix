"""Tests for CORS middleware configuration."""

import uuid

import pytest
from fastapi.testclient import TestClient

from helix.auth.tokens import create_token_claims, encode_token
from helix.main import app

client = TestClient(app)

ORIGIN = "http://localhost:3000"


@pytest.fixture
def auth_headers() -> dict[str, str]:
    claims = create_token_claims(
        subject_id=uuid.uuid4(),
        org_id=uuid.uuid4(),
        roles=["admin"],
    )
    token = encode_token(claims)
    return {"Authorization": f"Bearer {token}"}


class TestCORSPreflight:
    def test_options_returns_cors_headers(self) -> None:
        r = client.options(
            "/api/v1/workflows/",
            headers={
                "Origin": ORIGIN,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
        assert r.status_code == 200
        assert r.headers["access-control-allow-origin"] == ORIGIN
        assert "GET" in r.headers["access-control-allow-methods"]

    def test_options_disallowed_origin(self) -> None:
        r = client.options(
            "/api/v1/workflows/",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" not in r.headers


class TestCORSOnResponses:
    def test_get_with_origin_returns_allow_origin(
        self, auth_headers: dict[str, str]
    ) -> None:
        headers = {**auth_headers, "Origin": ORIGIN}
        r = client.get("/api/v1/workflows/", headers=headers)
        assert r.status_code == 200
        assert r.headers["access-control-allow-origin"] == ORIGIN

    def test_get_without_origin_has_no_cors_header(
        self, auth_headers: dict[str, str]
    ) -> None:
        r = client.get("/api/v1/workflows/", headers=auth_headers)
        assert "access-control-allow-origin" not in r.headers
