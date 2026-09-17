from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.credentials import encrypt_secret
from app.db.database import get_db
from app.models.connection import Connection
from app.models.metric_snapshot import MetricSnapshot
from app.models.site import Site
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.schemas.cloudflare import (
    CloudflareConnectionStatus,
    CloudflareSnapshotResponse,
    CloudflareTokenRequest,
    CloudflareZoneOption,
    CloudflareZoneSelection,
)
from app.services.cloudflare import (
    CloudflareError,
    fetch_cloudflare_snapshot,
    list_cloudflare_zones,
    list_connection_zones,
)

router = APIRouter(tags=["cloudflare"])
PROVIDER = "cloudflare"


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


def _connection(db: Session, site_id: UUID) -> Connection | None:
    return db.scalar(
        select(Connection).where(Connection.site_id == site_id, Connection.provider == PROVIDER)
    )


def _latest_snapshot(db: Session, site_id: UUID) -> MetricSnapshot | None:
    return db.scalar(
        select(MetricSnapshot)
        .where(MetricSnapshot.site_id == site_id, MetricSnapshot.source == PROVIDER)
        .order_by(MetricSnapshot.created_at.desc())
        .limit(1)
    )


def _snapshot_response(snapshot: MetricSnapshot | None) -> CloudflareSnapshotResponse | None:
    if snapshot is None:
        return None
    return CloudflareSnapshotResponse(
        period_start=snapshot.period_start,
        period_end=snapshot.period_end,
        metrics=snapshot.metrics,
        breakdowns=snapshot.breakdowns,
        created_at=snapshot.created_at,
    )


def _status_response(
    db: Session,
    site_id: UUID,
    connection: Connection | None,
) -> CloudflareConnectionStatus:
    if connection is None:
        return CloudflareConnectionStatus(status="disconnected")
    return CloudflareConnectionStatus(
        status=connection.status,
        zone_id=connection.external_resource_id,
        zone_name=connection.provider_display_name,
        account_name=connection.provider_account_id,
        last_synced_at=connection.last_synced_at,
        last_error=connection.last_error,
        latest_snapshot=_snapshot_response(_latest_snapshot(db, site_id)),
    )


def _cloudflare_error(
    exc: CloudflareError,
    fallback_status: int = status.HTTP_502_BAD_GATEWAY,
) -> HTTPException:
    return HTTPException(status_code=fallback_status, detail=str(exc))


@router.get("/sites/{site_id}/integrations/cloudflare/status", response_model=CloudflareConnectionStatus)
def cloudflare_status(
    site_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CloudflareConnectionStatus:
    _require_site_access(db, site_id, current_user.id)
    return _status_response(db, site_id, _connection(db, site_id))


@router.post("/sites/{site_id}/integrations/cloudflare/connect", response_model=CloudflareConnectionStatus)
async def connect_cloudflare(
    site_id: UUID,
    payload: CloudflareTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CloudflareConnectionStatus:
    _require_site_access(db, site_id, current_user.id)

    try:
        zones = await list_cloudflare_zones(payload.api_token)
    except CloudflareError as exc:
        raise _cloudflare_error(exc, status.HTTP_401_UNAUTHORIZED) from exc

    if not zones:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This Cloudflare token cannot access any zones",
        )

    connection = _connection(db, site_id)
    if connection is None:
        connection = Connection(site_id=site_id, provider=PROVIDER)
        db.add(connection)

    connection.encrypted_access_token = encrypt_secret(payload.api_token)
    connection.encrypted_refresh_token = None
    connection.token_expires_at = None
    connection.granted_scopes = "Zone Read, Analytics Read"
    connection.status = "zone_required"
    connection.external_resource_id = None
    connection.provider_display_name = None
    connection.provider_account_id = None
    connection.last_error = None
    db.commit()
    db.refresh(connection)
    return _status_response(db, site_id, connection)


@router.get(
    "/sites/{site_id}/integrations/cloudflare/zones",
    response_model=list[CloudflareZoneOption],
)
async def cloudflare_zones(
    site_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CloudflareZoneOption]:
    _require_site_access(db, site_id, current_user.id)
    connection = _connection(db, site_id)
    if connection is None or not connection.encrypted_access_token:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Connect Cloudflare first")

    try:
        zones = await list_connection_zones(connection)
    except CloudflareError as exc:
        connection.last_error = str(exc)
        db.commit()
        raise _cloudflare_error(exc) from exc

    return [CloudflareZoneOption(**item) for item in zones]


@router.post("/sites/{site_id}/integrations/cloudflare/zone", response_model=CloudflareConnectionStatus)
async def select_cloudflare_zone(
    site_id: UUID,
    payload: CloudflareZoneSelection,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CloudflareConnectionStatus:
    _require_site_access(db, site_id, current_user.id)
    connection = _connection(db, site_id)
    if connection is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Connect Cloudflare first")

    try:
        zones = await list_connection_zones(connection)
    except CloudflareError as exc:
        raise _cloudflare_error(exc) from exc

    selected = next((item for item in zones if item["zone_id"] == payload.zone_id), None)
    if selected is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Choose a Cloudflare zone accessible to this API token",
        )

    connection.external_resource_id = str(selected["zone_id"])
    connection.provider_display_name = str(selected["name"])
    connection.provider_account_id = str(selected["account_name"] or "") or None
    connection.status = "connected"
    connection.last_error = None
    db.commit()
    db.refresh(connection)
    return _status_response(db, site_id, connection)


@router.post("/sites/{site_id}/integrations/cloudflare/sync", response_model=CloudflareConnectionStatus)
async def sync_cloudflare(
    site_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CloudflareConnectionStatus:
    _require_site_access(db, site_id, current_user.id)
    connection = _connection(db, site_id)
    if connection is None or connection.status != "connected" or not connection.external_resource_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Select a Cloudflare zone before syncing",
        )

    try:
        normalized = await fetch_cloudflare_snapshot(connection)
    except CloudflareError as exc:
        connection.status = "error"
        connection.last_error = str(exc)
        db.commit()
        raise _cloudflare_error(exc) from exc

    snapshot = MetricSnapshot(
        site_id=site_id,
        source=PROVIDER,
        period_start=normalized["period_start"],
        period_end=normalized["period_end"],
        metrics=normalized["metrics"],
        breakdowns=normalized["breakdowns"],
    )
    db.add(snapshot)
    connection.status = "connected"
    connection.last_synced_at = datetime.now(timezone.utc)
    connection.last_error = None
    db.commit()
    db.refresh(connection)
    return _status_response(db, site_id, connection)


@router.delete("/sites/{site_id}/integrations/cloudflare", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_cloudflare(
    site_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    _require_site_access(db, site_id, current_user.id)
    connection = _connection(db, site_id)
    if connection is None:
        return

    connection.status = "disconnected"
    connection.external_resource_id = None
    connection.provider_display_name = None
    connection.provider_account_id = None
    connection.encrypted_access_token = None
    connection.encrypted_refresh_token = None
    connection.token_expires_at = None
    connection.granted_scopes = None
    connection.last_error = None
    db.commit()
