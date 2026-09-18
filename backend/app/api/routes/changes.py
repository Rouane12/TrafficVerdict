from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.database import get_db
from app.models.connection import Connection
from app.models.metric_snapshot import MetricSnapshot
from app.models.site import Site
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.schemas.changes import ChangeDetectionResponse
from app.services.change_detection import build_change_detection
from app.services.normalization import SOURCES, normalize_site_evidence

router = APIRouter(tags=["changes"])


def _require_site_access(db: Session, site_id: UUID, user_id: UUID) -> Site:
    statement = (
        select(Site)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Site.workspace_id)
        .where(Site.id == site_id, WorkspaceMember.user_id == user_id)
    )
    site = db.scalar(statement)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


def _snapshot_dict(snapshot: MetricSnapshot) -> dict:
    return {
        "period_start": snapshot.period_start,
        "period_end": snapshot.period_end,
        "metrics": snapshot.metrics,
        "breakdowns": snapshot.breakdowns,
    }


@router.get("/sites/{site_id}/changes", response_model=ChangeDetectionResponse)
def site_changes(
    site_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChangeDetectionResponse:
    site = _require_site_access(db, site_id, current_user.id)

    snapshot_rows = db.scalars(
        select(MetricSnapshot)
        .where(MetricSnapshot.site_id == site_id, MetricSnapshot.source.in_(SOURCES))
        .order_by(MetricSnapshot.created_at.desc())
    ).all()
    latest: dict[str, MetricSnapshot] = {}
    for snapshot in snapshot_rows:
        latest.setdefault(snapshot.source, snapshot)

    connection_rows = db.scalars(
        select(Connection).where(Connection.site_id == site_id, Connection.provider.in_(SOURCES))
    ).all()
    connections = {connection.provider: connection for connection in connection_rows}

    now = datetime.now(timezone.utc)
    normalized = normalize_site_evidence(
        site_id=str(site.id),
        site_domain=site.domain,
        site_timezone=site.timezone,
        snapshots={source: _snapshot_dict(latest[source]) if source in latest else None for source in SOURCES},
        connection_states={source: connections[source].status if source in connections else "disconnected" for source in SOURCES},
        last_synced_at={
            source: connections[source].last_synced_at.isoformat()
            if source in connections and connections[source].last_synced_at
            else None
            for source in SOURCES
        },
        as_of_date=now.date(),
        requested_days=14,
    )
    return ChangeDetectionResponse.model_validate(build_change_detection(normalized))
