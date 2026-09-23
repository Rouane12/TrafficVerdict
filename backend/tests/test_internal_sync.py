from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.routes import internal
from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_scheduled_sync_trigger_rejects_missing_secret(monkeypatch) -> None:
    monkeypatch.setattr(settings, "sync_trigger_secret", "")
    response = client.post("/api/internal/scheduled-sync")
    assert response.status_code == 503


def test_scheduled_sync_trigger_rejects_bad_bearer(monkeypatch) -> None:
    monkeypatch.setattr(settings, "sync_trigger_secret", "x" * 48)
    response = client.post(
        "/api/internal/scheduled-sync",
        headers={"Authorization": "Bearer wrong"},
    )
    assert response.status_code == 401


def test_scheduled_sync_trigger_runs_one_cycle(monkeypatch) -> None:
    monkeypatch.setattr(settings, "sync_trigger_secret", "x" * 48)

    async def fake_run_cycle(*, force: bool = False) -> dict[str, object]:
        assert force is False
        return {
            "recovered": 0,
            "queued": 3,
            "processed": 3,
            "succeeded": 3,
            "retrying": 0,
            "failed": 0,
            "skipped": 0,
            "other": 0,
            "outcomes": [
                "google_analytics:succeeded",
                "google_search_console:succeeded",
                "cloudflare:succeeded",
            ],
        }

    monkeypatch.setattr(internal, "run_cycle", fake_run_cycle)
    response = client.post(
        "/api/internal/scheduled-sync",
        headers={"Authorization": f"Bearer {'x' * 48}"},
    )

    assert response.status_code == 200
    assert response.json()["succeeded"] == 3
