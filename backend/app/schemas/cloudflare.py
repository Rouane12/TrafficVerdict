from datetime import date, datetime

from pydantic import BaseModel, Field


class CloudflareTokenRequest(BaseModel):
    api_token: str = Field(min_length=20, max_length=2048)


class CloudflareZoneOption(BaseModel):
    zone_id: str
    name: str
    status: str
    account_name: str | None = None


class CloudflareZoneSelection(BaseModel):
    zone_id: str = Field(min_length=1, max_length=64)


class CloudflareSnapshotResponse(BaseModel):
    period_start: date
    period_end: date
    metrics: dict
    breakdowns: dict
    created_at: datetime


class CloudflareConnectionStatus(BaseModel):
    configured: bool = True
    status: str
    zone_id: str | None = None
    zone_name: str | None = None
    account_name: str | None = None
    last_synced_at: datetime | None = None
    last_error: str | None = None
    latest_snapshot: CloudflareSnapshotResponse | None = None
