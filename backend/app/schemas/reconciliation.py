from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ReconciliationFinding(BaseModel):
    finding_type: str
    severity: str
    title: str
    explanation: str
    source_evidence: list[dict[str, Any]]
    confidence: str
    suggested_next_check: str
    generated_at: str
    rule_version: str
    rule_id: str


class ReconciliationResponse(BaseModel):
    site_id: UUID
    canonical_window: dict[str, Any] | None = None
    normalization_version: str
    engine_version: str
    overall_state: str
    finding_count: int
    findings: list[ReconciliationFinding]
    generated_at: str
