from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.database import get_db
from app.models.site import Site
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.schemas.site import SiteCreate, SiteResponse

router = APIRouter(prefix="/workspaces", tags=["sites"])


def _require_membership(db: Session, workspace_id: UUID, user_id: UUID) -> None:
    membership = db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")


def _normalize_domain(raw_domain: str) -> str:
    candidate = raw_domain.strip()
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    domain = (parsed.hostname or "").lower().strip(".")
    if not domain:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Enter a valid domain")
    return domain


@router.get("/{workspace_id}/sites", response_model=list[SiteResponse])
def list_sites(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Site]:
    _require_membership(db, workspace_id, current_user.id)
    statement = select(Site).where(Site.workspace_id == workspace_id).order_by(Site.created_at.asc())
    return list(db.scalars(statement).all())


@router.post("/{workspace_id}/sites", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
def create_site(
    workspace_id: UUID,
    payload: SiteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Site:
    _require_membership(db, workspace_id, current_user.id)
    site = Site(
        workspace_id=workspace_id,
        name=payload.name.strip(),
        domain=_normalize_domain(payload.domain),
        timezone=payload.timezone.strip(),
    )
    db.add(site)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This domain is already in the workspace",
        ) from exc
    db.refresh(site)
    return site
