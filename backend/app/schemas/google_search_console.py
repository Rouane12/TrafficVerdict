from datetime import date, datetime

from pydantic import BaseModel, Field


class SearchConsoleSiteOption(BaseModel):
    site_url: str
    display_name: str
    permission_level: str


class SearchConsoleSiteSelection(BaseModel):
    site_url: str = Field(min_length=1, max_length=255)


class SearchConsoleSnapshotResponse(BaseModel):
    period_start: date
    period_end: date
    metrics: dict
    breakdowns: dict
    created_at: datetime


class SearchConsoleConnectionStatus(BaseModel):
    configured: bool
    status: str
    site_url: str | None = None
    site_name: str | None = None
    permission_level: str | None = None
    last_synced_at: datetime | None = None
    last_error: str | None = None
    latest_snapshot: SearchConsoleSnapshotResponse | None = None
