from __future__ import annotations

import secrets

from fastapi import APIRouter, Header, HTTPException, status

from app.core.config import settings
from app.sync_worker import run_cycle

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/scheduled-sync")
async def scheduled_sync(authorization: str | None = Header(default=None)) -> dict[str, object]:
    expected = settings.sync_trigger_secret
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduled sync trigger is not configured",
        )

    prefix = "Bearer "
    if not authorization or not authorization.startswith(prefix):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    provided = authorization[len(prefix):]
    if not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    return await run_cycle(force=False)
