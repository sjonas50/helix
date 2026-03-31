"""Tests for WebSocket endpoint."""

from fastapi.testclient import TestClient

from helix.main import app


def test_websocket_connect_and_echo() -> None:
    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws/test-org-id") as ws:
        ws.send_json({"type": "subscribe", "channel": "approvals"})
        data = ws.receive_json()
        assert data["type"] == "ack"
        assert data["data"]["type"] == "subscribe"
        assert data["data"]["channel"] == "approvals"


def test_websocket_multiple_messages() -> None:
    client = TestClient(app)
    with client.websocket_connect("/api/v1/ws/org-123") as ws:
        for i in range(3):
            ws.send_json({"type": "ping", "seq": i})
            data = ws.receive_json()
            assert data["type"] == "ack"
            assert data["data"]["seq"] == i
