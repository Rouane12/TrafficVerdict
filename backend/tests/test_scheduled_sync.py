from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.models.connection import Connection
from app.services.scheduled_sync import _idempotency_key, _is_due


def test_scheduled_sync_due_logic_uses_last_successful_sync() -> None:
    now = datetime(2026, 9, 18, 18, 0, tzinfo=timezone.utc)
    connection = Connection(
        site_id=UUID("11111111-1111-1111-1111-111111111111"),
        provider="google_analytics",
        status="connected",
        external_resource_id="properties/123",
    )

    connection.last_synced_at = now - timedelta(hours=25)
    assert _is_due(connection, now, 24) is True

    connection.last_synced_at = now - timedelta(hours=3)
    assert _is_due(connection, now, 24) is False


def test_scheduled_sync_idempotency_key_is_stable_within_utc_day() -> None:
    site_id = UUID("11111111-1111-1111-1111-111111111111")
    morning = datetime(2026, 9, 18, 1, 0, tzinfo=timezone.utc)
    evening = datetime(2026, 9, 18, 22, 0, tzinfo=timezone.utc)

    assert _idempotency_key(site_id, "cloudflare", morning) == _idempotency_key(site_id, "cloudflare", evening)
    assert _idempotency_key(site_id, "cloudflare", morning).endswith("2026-09-18")
