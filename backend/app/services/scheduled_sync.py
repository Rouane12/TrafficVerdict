from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.connection import Connection
from app.models.metric_snapshot import MetricSnapshot
from app.models.sync_job import SyncJob
from app.services.cloudflare import CloudflareError, fetch_cloudflare_snapshot
from app.services.google_analytics import GoogleAnalyticsError, fetch_ga4_snapshot
from app.services.google_search_console import SearchConsoleError, fetch_search_console_snapshot

PROVIDERS = ("google_analytics", "google_search_console", "cloudflare")
RETRYABLE_ERRORS = (GoogleAnalyticsError, SearchConsoleError, CloudflareError)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _job_bucket(now: datetime) -> str:
    return now.astimezone(timezone.utc).date().isoformat()


def _idempotency_key(site_id: UUID, provider: str, now: datetime) -> str:
    return f"scheduled_sync:{site_id}:{provider}:{_job_bucket(now)}"


def _is_due(connection: Connection, now: datetime, interval_hours: int) -> bool:
    last_synced = _aware(connection.last_synced_at)
    if last_synced is None:
        return True
    return last_synced <= now - timedelta(hours=interval_hours)


def enqueue_due_sync_jobs(
    db: Session,
    *,
    now: datetime | None = None,
    interval_hours: int = 24,
    max_attempts: int = 3,
) -> list[SyncJob]:
    now = _aware(now) or _utcnow()
    connections = db.scalars(
        select(Connection).where(
            Connection.provider.in_(PROVIDERS),
            Connection.status == "connected",
            Connection.external_resource_id.is_not(None),
        )
    ).all()

    created: list[SyncJob] = []
    for connection in connections:
        if not _is_due(connection, now, interval_hours):
            continue

        key = _idempotency_key(connection.site_id, connection.provider, now)
        existing = db.scalar(select(SyncJob).where(SyncJob.idempotency_key == key))
        if existing is not None:
            continue

        job = SyncJob(
            site_id=connection.site_id,
            provider=connection.provider,
            job_type="scheduled_sync",
            status="queued",
            scheduled_for=now,
            attempt_count=0,
            max_attempts=max_attempts,
            idempotency_key=key,
        )
        try:
            with db.begin_nested():
                db.add(job)
                db.flush()
        except IntegrityError:
            continue
        created.append(job)

    if created:
        db.commit()
        for job in created:
            db.refresh(job)
    return created


def recover_stale_jobs(
    db: Session,
    *,
    now: datetime | None = None,
    stale_after_minutes: int = 30,
) -> int:
    now = _aware(now) or _utcnow()
    stale_before = now - timedelta(minutes=stale_after_minutes)
    jobs = db.scalars(
        select(SyncJob).where(
            SyncJob.status == "running",
            SyncJob.started_at.is_not(None),
            SyncJob.started_at <= stale_before,
        )
    ).all()
    for job in jobs:
        job.status = "queued"
        job.scheduled_for = now
        job.last_error = "Recovered after worker interruption"
        job.started_at = None
    if jobs:
        db.commit()
    return len(jobs)


async def _fetch_snapshot(connection: Connection, db: Session) -> dict:
    if connection.provider == "google_analytics":
        return await fetch_ga4_snapshot(connection, db)
    if connection.provider == "google_search_console":
        return await fetch_search_console_snapshot(connection, db)
    if connection.provider == "cloudflare":
        return await fetch_cloudflare_snapshot(connection)
    raise ValueError(f"Unsupported sync provider: {connection.provider}")


async def run_sync_job(
    db: Session,
    job: SyncJob,
    *,
    now: datetime | None = None,
) -> SyncJob:
    now = _aware(now) or _utcnow()
    if job.status not in {"queued", "retry"}:
        return job
    if _aware(job.scheduled_for) and _aware(job.scheduled_for) > now:
        return job

    connection = db.scalar(
        select(Connection).where(
            Connection.site_id == job.site_id,
            Connection.provider == job.provider,
        )
    )
    if connection is None or connection.status not in {"connected", "error"} or not connection.external_resource_id:
        job.status = "skipped"
        job.finished_at = now
        job.last_error = "Connection is not ready for scheduled sync"
        db.commit()
        db.refresh(job)
        return job

    job.status = "running"
    job.started_at = now
    job.attempt_count += 1
    job.last_error = None
    db.commit()

    try:
        normalized = await _fetch_snapshot(connection, db)
        snapshot = MetricSnapshot(
            site_id=job.site_id,
            source=job.provider,
            period_start=normalized["period_start"],
            period_end=normalized["period_end"],
            metrics=normalized["metrics"],
            breakdowns=normalized["breakdowns"],
        )
        db.add(snapshot)
        connection.status = "connected"
        connection.last_synced_at = _utcnow()
        connection.last_error = None

        job.status = "succeeded"
        job.finished_at = _utcnow()
        job.last_error = None
        db.commit()
        db.refresh(job)
        return job
    except Exception as exc:
        message = str(exc) or exc.__class__.__name__
        job_id = job.id
        db.rollback()

        job = db.get(SyncJob, job_id)
        connection = db.scalar(
            select(Connection).where(
                Connection.site_id == job.site_id,
                Connection.provider == job.provider,
            )
        )
        if job is None or connection is None:
            raise

        connection.last_error = message

        if job.attempt_count < job.max_attempts:
            backoff_minutes = min(5 * (2 ** (job.attempt_count - 1)), 60)
            job.status = "queued"
            job.scheduled_for = _utcnow() + timedelta(minutes=backoff_minutes)
            job.started_at = None
            job.finished_at = None
        else:
            job.status = "failed"
            job.finished_at = _utcnow()
            connection.status = "error"

        job.last_error = message
        db.commit()
        db.refresh(job)
        return job


async def process_due_sync_jobs(
    db: Session,
    *,
    now: datetime | None = None,
    limit: int = 10,
) -> list[SyncJob]:
    now = _aware(now) or _utcnow()
    jobs = db.scalars(
        select(SyncJob)
        .where(
            SyncJob.status == "queued",
            SyncJob.scheduled_for <= now,
        )
        .order_by(SyncJob.scheduled_for.asc(), SyncJob.created_at.asc())
        .limit(limit)
    ).all()

    processed: list[SyncJob] = []
    for job in jobs:
        processed.append(await run_sync_job(db, job, now=now))
    return processed


def latest_jobs_for_site(db: Session, site_id: UUID, limit: int = 12) -> list[SyncJob]:
    return list(
        db.scalars(
            select(SyncJob)
            .where(SyncJob.site_id == site_id)
            .order_by(SyncJob.created_at.desc())
            .limit(limit)
        ).all()
    )
