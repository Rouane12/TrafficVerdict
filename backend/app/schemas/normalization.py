from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class CanonicalWindow(BaseModel):
    start: date
    end: date
    days: int
    rule: str
    requested_days: int | None = None
    available_days: int


class SourceFreshness(BaseModel):
    state: str
    data_lag_days: int | None = None
    expected_lag_days: int
    delayed: bool


class DateAlignment(BaseModel):
    source_timezone: str
    target_timezone: str
    mode: str


class NormalizedSource(BaseModel):
    source: str
    label: str
    connection_state: str
    availability: str
    native_period_start: date | None = None
    native_period_end: date | None = None
    freshness: SourceFreshness
    date_alignment: DateAlignment
    metrics: dict[str, Any]
    canonical_metrics: dict[str, Any]
    normalized_breakdowns: dict[str, Any]
    missing_dates: list[date]
    last_synced_at: str | None = None


class NormalizedDimension(BaseModel):
    key: str
    label: str
    comparison_mode: str
    note: str
    values: list[dict[str, Any]]


class NormalizationResponse(BaseModel):
    site_id: UUID
    canonical_hostname: str
    canonical_timezone: str
    as_of_date: date
    canonical_window: CanonicalWindow | None = None
    sources: dict[str, NormalizedSource]
    dimensions: list[NormalizedDimension]
    warnings: list[str]
    normalization_version: str
