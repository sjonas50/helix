"""Test the health endpoint."""

from fastapi.testclient import TestClient

from helix.main import app


class TestHealth:
    def test_health_endpoint(self) -> None:
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
