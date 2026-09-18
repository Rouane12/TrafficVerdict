from __future__ import annotations

from app.services.change_detection import build_change_detection
from app.services.normalization import normalize_site_evidence
from tests.normalization_fixtures import AS_OF, cases


def _normalized(case_name: str) -> dict:
    case = cases()[case_name]
    states = {source: "connected" for source in ("google_analytics", "google_search_console", "cloudflare")}
    return normalize_site_evidence(
        site_id="11111111-1111-1111-1111-111111111111",
        site_domain="neuralcritic.net",
        site_timezone=case["timezone"],
        snapshots=case["snapshots"],
        connection_states=states,
        last_synced_at={},
        as_of_date=AS_OF,
        requested_days=14,
    )


def test_normal_history_produces_stable_weekly_comparison() -> None:
    result = build_change_detection(_normalized("normal_site"))

    assert result["state"] == "stable"
    assert len(result["weekly_comparisons"]) == 3
    assert result["anomalies"] == []
    assert all(item["change_percent"] == 0.0 for item in result["weekly_comparisons"])


def test_network_request_spike_is_not_misreported_as_visitor_growth() -> None:
    result = build_change_detection(_normalized("large_crawler_spike"))

    anomaly = next(item for item in result["anomalies"] if item["anomaly_type"] == "network_activity_divergence")
    assert anomaly["severity"] == "warning"
    assert "visitor growth" in anomaly["explanation"]
    assert anomaly["confidence"] == "medium"


def test_search_only_spike_is_recorded_as_source_change() -> None:
    result = build_change_detection(_normalized("gsc_only_spike"))

    anomaly = next(
        item
        for item in result["anomalies"]
        if item["anomaly_type"] == "large_source_change"
        and item["source_evidence"][0]["source"] == "google_search_console"
    )
    assert anomaly["severity"] == "info"
    assert anomaly["source_evidence"][0]["change_percent"] > 60
