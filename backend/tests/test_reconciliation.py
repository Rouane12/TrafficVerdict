from __future__ import annotations

from app.services.normalization import normalize_site_evidence
from app.services.reconciliation import reconcile_normalized_evidence
from tests.normalization_fixtures import AS_OF, cases

GENERATED_AT = "2026-09-17T18:00:00+00:00"


def _normalized(case: dict) -> dict:
    states = {source: "connected" for source in ("google_analytics", "google_search_console", "cloudflare")}
    return normalize_site_evidence(
        site_id="11111111-1111-1111-1111-111111111111",
        site_domain="neuralcritic.net",
        site_timezone=case["timezone"],
        snapshots=case["snapshots"],
        connection_states=states,
        last_synced_at={},
        as_of_date=AS_OF,
    )


def _reconcile(case_name: str) -> dict:
    return reconcile_normalized_evidence(_normalized(cases()[case_name]), generated_at=GENERATED_AT)


def _finding_types(result: dict) -> set[str]:
    return {finding["finding_type"] for finding in result["findings"]}


def test_reconciliation_is_deterministic_for_required_fixtures() -> None:
    for name in cases():
        assert _reconcile(name) == _reconcile(name)


def test_every_finding_has_required_evidence_fields() -> None:
    required = {
        "finding_type",
        "severity",
        "title",
        "explanation",
        "source_evidence",
        "confidence",
        "suggested_next_check",
        "generated_at",
        "rule_version",
        "rule_id",
    }
    for name in cases():
        for finding in _reconcile(name)["findings"]:
            assert required.issubset(finding)
            assert finding["confidence"] in {"high", "medium", "low"}
            assert finding["source_evidence"]


def test_normal_site_explains_scope_without_claiming_failure() -> None:
    result = _reconcile("normal_site")
    assert "measurement_scope_mismatch" in _finding_types(result)
    assert result["overall_state"] == "healthy_with_explainable_gaps"
    assert not any(finding["severity"] == "critical" for finding in result["findings"])


def test_large_cloudflare_spike_is_suspicion_not_bot_claim() -> None:
    result = _reconcile("large_crawler_spike")
    finding = next(item for item in result["findings"] if item["finding_type"] == "automated_or_network_traffic_suspicion")
    assert finding["severity"] == "warning"
    assert "bots" not in finding["title"].lower()
    assert "without labeling it as bots" in finding["explanation"]


def test_ga4_outage_produces_source_availability_diagnosis() -> None:
    result = _reconcile("ga4_outage")
    finding = next(item for item in result["findings"] if item["rule_id"] == "source.missing_snapshot" and item["source_evidence"][0]["source"] == "google_analytics")
    assert finding["confidence"] == "high"
    assert finding["severity"] == "warning"


def test_gsc_only_spike_is_search_specific() -> None:
    result = _reconcile("gsc_only_spike")
    finding = next(item for item in result["findings"] if item["rule_id"] == "search.gsc_only_spike")
    assert finding["finding_type"] == "search_to_analytics_mismatch"
    assert finding["confidence"] == "medium"


def test_partial_path_fixture_does_not_invent_ga4_undertracking() -> None:
    result = _reconcile("partial_path_tracking")
    finding = next(item for item in result["findings"] if item["rule_id"] == "coverage.path_evidence_incomplete")
    assert finding["finding_type"] == "ga4_coverage_suspicion"
    assert "cannot claim" in finding["explanation"]


def test_missing_cloudflare_is_explicit() -> None:
    result = _reconcile("missing_cloudflare_data")
    assert any(
        item["rule_id"] == "source.missing_snapshot" and item["source_evidence"][0]["source"] == "cloudflare"
        for item in result["findings"]
    )


def test_timezone_mismatch_becomes_evidence_backed_caveat() -> None:
    result = _reconcile("timezone_mismatch")
    finding = next(item for item in result["findings"] if item["rule_id"] == "scope.timezone_boundary_mismatch")
    assert finding["confidence"] == "high"
    assert len(finding["source_evidence"]) >= 2
