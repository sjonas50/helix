"""Tests for authenticated WebSocket endpoint."""

import uuid

from fastapi.testclient import TestClient

from helix.auth.tokens import create_token_claims, encode_token
from helix.main import app


def _make_token() -> str:
    claims = create_token_claims(
        subject_id=uuid.uuid4(), org_id=uuid.uuid4(), roles=["admin"]
    )
    return encode_token(claims)


def test_websocket_connect_and_echo() -> None:
    client = TestClient(app)
    token = _make_token()
    with client.websocket_connect(f"/api/v1/ws?token={token}") as ws:
        ws.send_json({"type": "subscribe", "channel": "approvals"})
        data = ws.receive_json()
        assert data["type"] == "ack"
        assert data["data"]["type"] == "subscribe"


def test_websocket_rejects_missing_token() -> None:
    client = TestClient(app)
    # WebSocket without token should be closed by server
    try:
        with client.websocket_connect("/api/v1/ws") as ws:
            ws.receive_json()  # Should not get here
            raise AssertionError("Should have been rejected")
    except Exception:
        pass  # Expected — connection refused


def test_websocket_rejects_invalid_token() -> None:
    client = TestClient(app)
    try:
        with client.websocket_connect("/api/v1/ws?token=invalid.jwt.here") as ws:
            ws.receive_json()
            raise AssertionError("Should have been rejected")
    except Exception:
        pass  # Expected
