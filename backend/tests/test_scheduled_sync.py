from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import app.models  # noqa: F401
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.connection import Connection
from app.models.sync_job import SyncJob
from app.services.scheduled_sync import _idempotency_key, _is_due, enqueue_due_sync_jobs


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


def test_due_job_enqueue_is_deduplicated_by_site_provider_and_day() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    now = datetime(2026, 9, 18, 18, 0, tzinfo=timezone.utc)
    site_id = UUID("11111111-1111-1111-1111-111111111111")

    with Session() as db:
        db.add(
            Connection(
                site_id=site_id,
                provider="cloudflare",
                status="connected",
                external_resource_id="zone-123",
                last_synced_at=now - timedelta(hours=30),
            )
        )
        db.commit()

        first = enqueue_due_sync_jobs(db, now=now, interval_hours=24)
        second = enqueue_due_sync_jobs(db, now=now, interval_hours=24)

        assert len(first) == 1
        assert second == []
        jobs = db.scalars(select(SyncJob)).all()
        assert len(jobs) == 1
        assert jobs[0].status == "queued"
