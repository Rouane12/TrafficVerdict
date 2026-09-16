from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.connection import Connection
from app.models.metric_snapshot import MetricSnapshot
from app.models.site import Site
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.schemas.google_analytics import (
    GoogleConnectionStatus,
    GooglePropertyOption,
    GooglePropertySelection,
    GoogleSnapshotResponse,
)
from app.services.google_analytics import (
    GoogleAnalyticsError,
    apply_token_payload,
    build_authorization_url,
    decode_oauth_state,
    exchange_authorization_code,
    fetch_ga4_snapshot,
    google_oauth_configured,
    list_ga4_properties,
    revoke_connection_tokens,
)

router = APIRouter(tags=["google-analytics"])
PROVIDER = "google_analytics"


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


def _snapshot_response(snapshot: MetricSnapshot | None) -> GoogleSnapshotResponse | None:
    if snapshot is None:
        return None
    return GoogleSnapshotResponse(
        period_start=snapshot.period_start,
        period_end=snapshot.period_end,
        metrics=snapshot.metrics,
        breakdowns=snapshot.breakdowns,
        created_at=snapshot.created_at,
    )


def _status_response(db: Session, site_id: UUID, connection: Connection | None) -> GoogleConnectionStatus:
    if connection is None:
        return GoogleConnectionStatus(configured=google_oauth_configured(), status="disconnected")
    return GoogleConnectionStatus(
        configured=google_oauth_configured(),
        status=connection.status,
        property_id=connection.external_resource_id,
        property_name=connection.provider_display_name,
        account_id=connection.provider_account_id,
        last_synced_at=connection.last_synced_at,
        last_error=connection.last_error,
        latest_snapshot=_snapshot_response(_latest_snapshot(db, site_id)),
    )


def _google_error(exc: GoogleAnalyticsError, fallback_status: int = status.HTTP_502_BAD_GATEWAY) -> HTTPException:
    return HTTPException(status_code=fallback_status, detail=str(exc))


@router.get("/sites/{site_id}/integrations/google/status", response_model=GoogleConnectionStatus)
def google_status(
    site_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoogleConnectionStatus:
    _require_site_access(db, site_id, current_user.id)
    return _status_response(db, site_id, _connection(db, site_id))


@router.get("/sites/{site_id}/integrations/google/start")
def google_start(
    site_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    _require_site_access(db, site_id, current_user.id)
    if not google_oauth_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured yet",
        )
    try:
        url = build_authorization_url(current_user.id, site_id)
    except GoogleAnalyticsError as exc:
        raise _google_error(exc, status.HTTP_503_SERVICE_UNAVAILABLE) from exc
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/integrations/google/callback")
async def google_callback(
    state_token: str = Query(alias="state"),
    code: str | None = None,
    error: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    try:
        state_user_id, site_id = decode_oauth_state(state_token)
    except GoogleAnalyticsError as exc:
        raise _google_error(exc, status.HTTP_400_BAD_REQUEST) from exc

    if state_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="OAuth state does not match this account")
    _require_site_access(db, site_id, current_user.id)

    if error:
        return RedirectResponse(
            url=f"{settings.frontend_origin}/dashboard?google=denied&site={site_id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google did not return an authorization code")

    try:
        token_payload = await exchange_authorization_code(code)
    except GoogleAnalyticsError as exc:
        raise _google_error(exc) from exc

    connection = _connection(db, site_id)
    if connection is None:
        connection = Connection(site_id=site_id, provider=PROVIDER)
        db.add(connection)

    apply_token_payload(connection, token_payload)
    connection.status = "property_required"
    connection.external_resource_id = None
    connection.provider_display_name = None
    connection.provider_account_id = None
    connection.last_error = None
    db.commit()

    return RedirectResponse(
        url=f"{settings.frontend_origin}/dashboard?google=property_required&site={site_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get(
    "/sites/{site_id}/integrations/google/properties",
    response_model=list[GooglePropertyOption],
)
async def google_properties(
    site_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GooglePropertyOption]:
    _require_site_access(db, site_id, current_user.id)
    connection = _connection(db, site_id)
    if connection is None or not connection.encrypted_refresh_token:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Connect Google Analytics first")
    try:
        properties = await list_ga4_properties(connection, db)
    except GoogleAnalyticsError as exc:
        connection.last_error = str(exc)
        db.commit()
        raise _google_error(exc) from exc
    return [GooglePropertyOption(**item) for item in properties]


@router.post("/sites/{site_id}/integrations/google/property", response_model=GoogleConnectionStatus)
async def select_google_property(
    site_id: UUID,
    payload: GooglePropertySelection,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoogleConnectionStatus:
    _require_site_access(db, site_id, current_user.id)
    connection = _connection(db, site_id)
    if connection is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Connect Google Analytics first")

    try:
        properties = await list_ga4_properties(connection, db)
    except GoogleAnalyticsError as exc:
        raise _google_error(exc) from exc

    selected = next((item for item in properties if item["property_id"] == payload.property_id), None)
    if selected is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Choose an accessible GA4 property")

    connection.external_resource_id = selected["property_id"]
    connection.provider_display_name = selected["property_name"]
    connection.provider_account_id = selected["account_id"]
    connection.status = "connected"
    connection.last_error = None
    db.commit()
    db.refresh(connection)
    return _status_response(db, site_id, connection)


@router.post("/sites/{site_id}/integrations/google/sync", response_model=GoogleConnectionStatus)
async def sync_google_analytics(
    site_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoogleConnectionStatus:
    _require_site_access(db, site_id, current_user.id)
    connection = _connection(db, site_id)
    if connection is None or connection.status != "connected" or not connection.external_resource_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Select a GA4 property before syncing")

    try:
        normalized = await fetch_ga4_snapshot(connection, db)
    except GoogleAnalyticsError as exc:
        connection.status = "error"
        connection.last_error = str(exc)
        db.commit()
        raise _google_error(exc) from exc

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


@router.delete("/sites/{site_id}/integrations/google", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_google_analytics(
    site_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    _require_site_access(db, site_id, current_user.id)
    connection = _connection(db, site_id)
    if connection is None:
        return

    try:
        await revoke_connection_tokens(connection)
    except Exception:
        # Revocation is best-effort. Local credentials are cleared regardless.
        pass

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
