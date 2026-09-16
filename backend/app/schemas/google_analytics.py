from datetime import date, datetime

from pydantic import BaseModel, Field


class GooglePropertyOption(BaseModel):
    property_id: str
    property_name: str
    account_id: str
    account_name: str


class GooglePropertySelection(BaseModel):
    property_id: str = Field(min_length=1, max_length=255)


class GoogleSnapshotResponse(BaseModel):
    period_start: date
    period_end: date
    metrics: dict
    breakdowns: dict
    created_at: datetime


class GoogleConnectionStatus(BaseModel):
    configured: bool
    status: str
    property_id: str | None = None
    property_name: str | None = None
    account_id: str | None = None
    last_synced_at: datetime | None = None
    last_error: str | None = None
    latest_snapshot: GoogleSnapshotResponse | None = None
