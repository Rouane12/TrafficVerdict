from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "trafficverdict-api",
    }


def test_api_security_headers() -> None:
    response = client.get("/api/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "same-origin"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert response.headers["cache-control"] == "no-store"


def test_state_changing_requests_reject_mismatched_origin() -> None:
    response = client.post(
        "/api/auth/logout",
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-origin state-changing request rejected"


def test_state_changing_requests_allow_configured_origin() -> None:
    response = client.post(
        "/api/auth/logout",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 204
