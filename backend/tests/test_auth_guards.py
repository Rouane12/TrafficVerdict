from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_me_requires_authentication() -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_workspaces_require_authentication() -> None:
    response = client.get("/api/workspaces")
    assert response.status_code == 401
