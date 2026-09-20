import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.core.config import settings
from app.core.security import create_session_token, hash_password, verify_password
from app.db.database import get_db
from app.models.connection import Connection
from app.models.metric_snapshot import MetricSnapshot
from app.models.password_reset_token import PasswordResetToken
from app.models.site import Site
from app.models.sync_job import SyncJob
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.schemas.auth import (
    DeleteAccountRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
)
from app.services.google_analytics import revoke_connection_tokens
from app.services.password_reset_email import (
    PasswordResetEmailError,
    password_reset_email_configured,
    send_password_reset_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)
PASSWORD_RESET_MESSAGE = "If an account exists for that email, a password reset link has been sent."


def _set_session_cookie(response: Response, user: User) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=create_session_token(user.id),
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> User:
    email = str(payload.email).strip().lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    display_name = payload.display_name.strip() if payload.display_name else None
    user = User(
        email=email,
        display_name=display_name or None,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    _set_session_cookie(response, user)
    return user


@router.post("/login", response_model=UserResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> User:
    if not password_reset_email_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset email is temporarily unavailable",
        )

    email = str(payload.email).strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    _set_session_cookie(response, user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        samesite="lax",
    )




def _password_reset_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/forgot-password", response_model=MessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    email = str(payload.email).strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        return MessageResponse(message=PASSWORD_RESET_MESSAGE)

    now = datetime.now(timezone.utc)
    recent = db.scalar(
        select(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
            PasswordResetToken.created_at >= now - timedelta(seconds=60),
        )
        .order_by(PasswordResetToken.created_at.desc())
        .limit(1)
    )
    if recent is not None:
        return MessageResponse(message=PASSWORD_RESET_MESSAGE)

    token = secrets.token_urlsafe(32)
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=_password_reset_hash(token),
        expires_at=now + timedelta(minutes=settings.password_reset_ttl_minutes),
    )
    db.add(reset)
    db.commit()

    try:
        await send_password_reset_email(user.email, token)
    except PasswordResetEmailError:
        logger.exception("Unable to deliver password reset email")
        db.delete(reset)
        db.commit()
        return MessageResponse(message=PASSWORD_RESET_MESSAGE)

    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.id != reset.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    db.commit()
    return MessageResponse(message=PASSWORD_RESET_MESSAGE)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    now = datetime.now(timezone.utc)
    token_hash = _password_reset_hash(payload.token)
    reset = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    if reset is None or reset.used_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link is invalid or has already been used",
        )

    expires_at = reset.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link has expired",
        )

    user = db.get(User, reset.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset link is invalid",
        )

    user.password_hash = hash_password(payload.password)
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    db.commit()
    return MessageResponse(message="Password updated. You can now sign in.")


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user



@router.get("/export")
def export_account_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    memberships = list(
        db.scalars(
            select(WorkspaceMember)
            .where(WorkspaceMember.user_id == current_user.id)
            .order_by(WorkspaceMember.created_at.asc())
        ).all()
    )

    exported_workspaces: list[dict] = []
    for membership in memberships:
        workspace = db.get(Workspace, membership.workspace_id)
        if workspace is None:
            continue

        sites = list(
            db.scalars(
                select(Site)
                .where(Site.workspace_id == workspace.id)
                .order_by(Site.created_at.asc())
            ).all()
        )
        exported_sites: list[dict] = []
        for site in sites:
            connections = list(
                db.scalars(
                    select(Connection)
                    .where(Connection.site_id == site.id)
                    .order_by(Connection.provider.asc())
                ).all()
            )
            snapshots = list(
                db.scalars(
                    select(MetricSnapshot)
                    .where(MetricSnapshot.site_id == site.id)
                    .order_by(MetricSnapshot.created_at.asc())
                ).all()
            )
            jobs = list(
                db.scalars(
                    select(SyncJob)
                    .where(SyncJob.site_id == site.id)
                    .order_by(SyncJob.created_at.asc())
                ).all()
            )

            exported_sites.append(
                {
                    "id": site.id,
                    "name": site.name,
                    "domain": site.domain,
                    "timezone": site.timezone,
                    "created_at": site.created_at,
                    "connections": [
                        {
                            "provider": connection.provider,
                            "status": connection.status,
                            "external_resource_id": connection.external_resource_id,
                            "provider_display_name": connection.provider_display_name,
                            "provider_account_id": connection.provider_account_id,
                            "granted_scopes": connection.granted_scopes,
                            "last_synced_at": connection.last_synced_at,
                            "last_error": connection.last_error,
                            "created_at": connection.created_at,
                        }
                        for connection in connections
                    ],
                    "metric_snapshots": [
                        {
                            "source": snapshot.source,
                            "period_start": snapshot.period_start,
                            "period_end": snapshot.period_end,
                            "metrics": snapshot.metrics,
                            "breakdowns": snapshot.breakdowns,
                            "created_at": snapshot.created_at,
                        }
                        for snapshot in snapshots
                    ],
                    "sync_jobs": [
                        {
                            "provider": job.provider,
                            "job_type": job.job_type,
                            "status": job.status,
                            "scheduled_for": job.scheduled_for,
                            "attempt_count": job.attempt_count,
                            "max_attempts": job.max_attempts,
                            "started_at": job.started_at,
                            "finished_at": job.finished_at,
                            "last_error": job.last_error,
                            "created_at": job.created_at,
                        }
                        for job in jobs
                    ],
                }
            )

        exported_workspaces.append(
            {
                "id": workspace.id,
                "name": workspace.name,
                "slug": workspace.slug,
                "role": membership.role,
                "created_at": workspace.created_at,
                "sites": exported_sites,
            }
        )

    return {
        "account": {
            "id": current_user.id,
            "email": current_user.email,
            "display_name": current_user.display_name,
            "created_at": current_user.created_at,
        },
        "workspaces": exported_workspaces,
    }


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    payload: DeleteAccountRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")

    memberships = list(
        db.scalars(select(WorkspaceMember).where(WorkspaceMember.user_id == current_user.id)).all()
    )
    owned_workspace_ids = [
        membership.workspace_id for membership in memberships if membership.role == "owner"
    ]

    owned_workspaces: list[Workspace] = []
    for workspace_id in owned_workspace_ids:
        other_members = db.scalar(
            select(func.count())
            .select_from(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id != current_user.id,
            )
        )
        if other_members:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This account owns a workspace with other members. Transfer ownership before deleting the account.",
            )
        workspace = db.get(Workspace, workspace_id)
        if workspace is not None:
            owned_workspaces.append(workspace)

    if owned_workspace_ids:
        site_ids = list(
            db.scalars(select(Site.id).where(Site.workspace_id.in_(owned_workspace_ids))).all()
        )
        if site_ids:
            google_connections = list(
                db.scalars(
                    select(Connection).where(
                        Connection.site_id.in_(site_ids),
                        Connection.provider.in_(("google_analytics", "google_search_console")),
                    )
                ).all()
            )
            for connection in google_connections:
                try:
                    await revoke_connection_tokens(connection)
                except Exception:
                    # Account deletion must still remove local credentials if remote
                    # token revocation is temporarily unavailable.
                    pass

    for workspace in owned_workspaces:
        db.delete(workspace)
    db.delete(current_user)
    db.commit()

    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.cookie_secure,
        samesite="lax",
    )
