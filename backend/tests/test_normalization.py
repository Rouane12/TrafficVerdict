from __future__ import annotations

from app.services.normalization import normalize_hostname, normalize_path, normalize_site_evidence, normalize_url
from tests.normalization_fixtures import AS_OF, cases


def _normalize(case: dict) -> dict:
    snapshots = case["snapshots"]
    states = {source: "connected" for source in ("google_analytics", "google_search_console", "cloudflare")}
    return normalize_site_evidence(
        site_id="11111111-1111-1111-1111-111111111111",
        site_domain="https://WWW.NeuralCritic.net/",
        site_timezone=case["timezone"],
        snapshots=snapshots,
        connection_states=states,
        last_synced_at={},
        as_of_date=AS_OF,
    )


def test_normalization_is_deterministic_for_all_required_fixtures() -> None:
    for case in cases().values():
        assert _normalize(case) == _normalize(case)


def test_hostname_path_and_url_rules_are_canonical() -> None:
    assert normalize_hostname("HTTPS://WWW.Example.COM.:443/a") == "example.com"
    assert normalize_path("/News//Nintendo/?utm_source=x#top") == "/News/Nintendo"
    normalized = normalize_url("https://www.NeuralCritic.net/reviews/?utm_source=x#top")
    assert normalized["hostname"] == "neuralcritic.net"
    assert normalized["path"] == "/reviews"
    assert normalized["canonical_url"] == "https://neuralcritic.net/reviews"


def test_normal_site_builds_overlap_and_comparable_dimensions() -> None:
    result = _normalize(cases()["normal_site"])
    assert result["canonical_window"]["start"] == "2026-08-20"
    assert result["canonical_window"]["end"] == "2026-09-14"
    assert result["canonical_window"]["days"] == 26
    visit_dimension = next(item for item in result["dimensions"] if item["key"] == "visit_like_activity")
    assert visit_dimension["comparison_mode"] == "contextual_not_equivalent"
    assert {item["source"] for item in visit_dimension["values"]} == {"google_analytics", "cloudflare"}


def test_missing_sources_are_explicit_not_zero_filled() -> None:
    ga4 = _normalize(cases()["ga4_outage"])["sources"]["google_analytics"]
    cloudflare = _normalize(cases()["missing_cloudflare_data"])["sources"]["cloudflare"]
    assert ga4["freshness"]["state"] == "missing"
    assert ga4["canonical_metrics"] == {}
    assert cloudflare["freshness"]["state"] == "missing"
    assert cloudflare["metrics"] == {}


def test_crawler_spike_is_preserved_without_diagnosing_it() -> None:
    result = _normalize(cases()["large_crawler_spike"])
    assert result["sources"]["cloudflare"]["metrics"]["requests"] == 900000
    assert not any("crawler" in warning.lower() for warning in result["warnings"])


def test_gsc_spike_remains_source_specific() -> None:
    result = _normalize(cases()["gsc_only_spike"])
    search = next(item for item in result["dimensions"] if item["key"] == "search_discovery")
    assert search["comparison_mode"] == "source_specific"
    assert all(value["source"] == "google_search_console" for value in search["values"])


def test_gsc_pages_receive_hostname_and_path_normalization() -> None:
    result = _normalize(cases()["partial_path_tracking"])
    pages = result["sources"]["google_search_console"]["normalized_breakdowns"]["top_pages"]
    assert pages[0]["canonical_url"] == "https://neuralcritic.net/reviews"
    assert pages[1]["canonical_path"] == "/news/nintendo" or pages[1]["canonical_path"] == "/news/nintendo"
    assert all(page["matches_site_hostname"] is True for page in pages)


def test_timezone_mismatch_is_marked_without_rebinning_counts() -> None:
    result = _normalize(cases()["timezone_mismatch"])
    gsc = result["sources"]["google_search_console"]
    cloudflare = result["sources"]["cloudflare"]
    assert gsc["date_alignment"]["mode"] == "date_label_only"
    assert cloudflare["date_alignment"]["mode"] == "date_label_only"
    assert any("day boundaries" in warning for warning in result["warnings"])
