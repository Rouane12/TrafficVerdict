from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ChangeComparison(BaseModel):
    source: str
    label: str
    metric: str
    previous: float
    current: float
    change_percent: float | None = None
    direction: str
    baseline_sufficient: bool | None = None
    previous_start: str | None = None
    previous_end: str | None = None
    current_start: str | None = None
    current_end: str | None = None
    previous_date: str | None = None
    current_date: str | None = None


class ChangeAnomaly(BaseModel):
    anomaly_type: str
    severity: str
    title: str
    explanation: str
    confidence: str
    source_evidence: list[dict[str, Any]]


class ChangeDetectionResponse(BaseModel):
    site_id: UUID
    state: str
    summary: str
    analysis_window: dict[str, Any] | None = None
    weekly_comparisons: list[ChangeComparison]
    daily_comparisons: list[ChangeComparison]
    anomalies: list[ChangeAnomaly]
    change_detection_version: str
