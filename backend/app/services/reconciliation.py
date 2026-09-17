from __future__ import annotations

from datetime import datetime, timezone
from statistics import median
from typing import Any

ENGINE_VERSION = "1.0.0"
RULE_VERSION = "1.0.0"
MIN_BASELINE_DAYS = 5
SPIKE_RATIO = 5.0
MILD_SPIKE_RATIO = 2.0


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _daily(source: dict[str, Any]) -> list[dict[str, Any]]:
    breakdowns = source.get("normalized_breakdowns") if isinstance(source, dict) else {}
    rows = breakdowns.get("daily") if isinstance(breakdowns, dict) else []
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _spike_evidence(rows: list[dict[str, Any]], metric: str) -> dict[str, Any] | None:
    if len(rows) < MIN_BASELINE_DAYS + 1:
        return None
    recent = _number(rows[-1].get(metric))
    baseline_values = [_number(row.get(metric)) for row in rows[-(MIN_BASELINE_DAYS + 1):-1]]
    baseline_values = [value for value in baseline_values if value >= 0]
    if not baseline_values:
        return None
    baseline = median(baseline_values)
    ratio = recent / baseline if baseline > 0 else (float("inf") if recent > 0 else 1.0)
    return {
        "date": rows[-1].get("date"),
        "metric": metric,
        "recent": recent,
        "baseline_median": baseline,
        "ratio": ratio,
        "baseline_days": len(baseline_values),
    }


def _finding(
    *,
    finding_type: str,
    severity: str,
    title: str,
    explanation: str,
    evidence: list[dict[str, Any]],
    confidence: str,
    suggested_next_check: str,
    generated_at: str,
    rule_id: str,
) -> dict[str, Any]:
    return {
        "finding_type": finding_type,
        "severity": severity,
        "title": title,
        "explanation": explanation,
        "source_evidence": evidence,
        "confidence": confidence,
        "suggested_next_check": suggested_next_check,
        "generated_at": generated_at,
        "rule_version": RULE_VERSION,
        "rule_id": rule_id,
    }


def reconcile_normalized_evidence(normalized: dict[str, Any], *, generated_at: str | None = None) -> dict[str, Any]:
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    sources = normalized.get("sources") if isinstance(normalized.get("sources"), dict) else {}
    findings: list[dict[str, Any]] = []

    ga = sources.get("google_analytics", {})
    gsc = sources.get("google_search_console", {})
    cf = sources.get("cloudflare", {})

    # Source outage / stale sync family.
    for key, source in sources.items():
        label = source.get("label") or key
        availability = source.get("availability")
        freshness = source.get("freshness") if isinstance(source.get("freshness"), dict) else {}
        missing_dates = source.get("missing_dates") if isinstance(source.get("missing_dates"), list) else []
        if availability != "available":
            findings.append(
                _finding(
                    finding_type="source_outage_or_missing",
                    severity="warning",
                    title=f"{label} has no usable snapshot",
                    explanation="TrafficVerdict cannot reconcile this source until a usable snapshot exists. This is a source-availability problem, not evidence that site traffic disappeared.",
                    evidence=[{"source": key, "availability": availability, "connection_state": source.get("connection_state")}],
                    confidence="high",
                    suggested_next_check=f"Reconnect or sync {label}, then rerun reconciliation.",
                    generated_at=generated_at,
                    rule_id="source.missing_snapshot",
                )
            )
            continue
        if freshness.get("delayed"):
            findings.append(
                _finding(
                    finding_type="source_outage_or_stale_sync",
                    severity="warning",
                    title=f"{label} is delayed",
                    explanation="This source is older than its expected reporting lag, so comparisons that depend on the newest dates should be treated cautiously.",
                    evidence=[{
                        "source": key,
                        "data_lag_days": freshness.get("data_lag_days"),
                        "expected_lag_days": freshness.get("expected_lag_days"),
                    }],
                    confidence="high",
                    suggested_next_check=f"Sync {label} again and confirm the newest available date.",
                    generated_at=generated_at,
                    rule_id="source.delayed",
                )
            )
        if missing_dates:
            findings.append(
                _finding(
                    finding_type="source_outage_or_stale_sync",
                    severity="warning",
                    title=f"{label} has missing daily data",
                    explanation="One or more dates are absent inside this source's own reporting window. TrafficVerdict will not silently replace those dates with zeros.",
                    evidence=[{"source": key, "missing_dates": missing_dates[:10], "missing_count": len(missing_dates)}],
                    confidence="high",
                    suggested_next_check=f"Inspect {label} for reporting gaps or rerun the source sync.",
                    generated_at=generated_at,
                    rule_id="source.missing_days",
                )
            )

    # Measurement-scope mismatch family. This is explanatory, not an error.
    ga_metrics = ga.get("canonical_metrics") if isinstance(ga.get("canonical_metrics"), dict) else {}
    gsc_metrics = gsc.get("canonical_metrics") if isinstance(gsc.get("canonical_metrics"), dict) else {}
    cf_metrics = cf.get("canonical_metrics") if isinstance(cf.get("canonical_metrics"), dict) else {}
    scope_evidence: list[dict[str, Any]] = []
    if ga.get("availability") == "available":
        scope_evidence.append({"source": "google_analytics", "sessions": ga_metrics.get("sessions"), "views": ga_metrics.get("views")})
    if cf.get("availability") == "available":
        scope_evidence.append({"source": "cloudflare", "visits": cf_metrics.get("visits"), "requests": cf_metrics.get("requests")})
    if gsc.get("availability") == "available":
        scope_evidence.append({"source": "google_search_console", "clicks": gsc_metrics.get("clicks"), "impressions": gsc_metrics.get("impressions")})
    if len(scope_evidence) >= 2:
        findings.append(
            _finding(
                finding_type="measurement_scope_mismatch",
                severity="info",
                title="The connected sources measure different things",
                explanation="Cloudflare network traffic, GA4 browser analytics, and Search Console search activity are not expected to match. Their differences are meaningful context, not automatically a tracking failure.",
                evidence=scope_evidence,
                confidence="high",
                suggested_next_check="Use the source whose metric matches the question you are asking; investigate only unusual changes in the relationship between sources.",
                generated_at=generated_at,
                rule_id="scope.distinct_measurement_entities",
            )
        )

    # Timezone/day-boundary caveat.
    timezone_evidence = []
    for key, source in sources.items():
        alignment = source.get("date_alignment") if isinstance(source.get("date_alignment"), dict) else {}
        if alignment.get("mode") == "date_label_only":
            timezone_evidence.append({"source": key, **alignment})
    if timezone_evidence:
        findings.append(
            _finding(
                finding_type="measurement_scope_mismatch",
                severity="info",
                title="Source day boundaries do not fully align",
                explanation="At least one provider defines a reporting day in a different timezone. TrafficVerdict normalizes date labels without inventing rebinned counts, so small day-edge differences may remain.",
                evidence=timezone_evidence,
                confidence="high",
                suggested_next_check="Use multi-day trends for reconciliation and treat single-day edge differences cautiously.",
                generated_at=generated_at,
                rule_id="scope.timezone_boundary_mismatch",
            )
        )

    # Automated/network traffic suspicion. We identify a network spike, but never call it bots automatically.
    cf_spike = _spike_evidence(_daily(cf), "requests") if cf.get("availability") == "available" else None
    ga_spike = _spike_evidence(_daily(ga), "sessions") if ga.get("availability") == "available" else None
    gsc_spike = _spike_evidence(_daily(gsc), "clicks") if gsc.get("availability") == "available" else None
    if cf_spike and cf_spike["ratio"] >= SPIKE_RATIO:
        browser_support = ga_spike is not None and ga_spike["ratio"] >= MILD_SPIKE_RATIO
        search_support = gsc_spike is not None and gsc_spike["ratio"] >= MILD_SPIKE_RATIO
        confidence = "high" if ga_spike is not None and gsc_spike is not None and not browser_support and not search_support else "medium"
        findings.append(
            _finding(
                finding_type="automated_or_network_traffic_suspicion",
                severity="warning",
                title="Cloudflare recorded an unusual request spike",
                explanation="Cloudflare requests jumped far above their recent baseline. The available browser/search signals do not establish that these requests were human visits, so TrafficVerdict flags network traffic for investigation without labeling it as bots.",
                evidence=[
                    {"source": "cloudflare", **cf_spike},
                    {"source": "google_analytics", **ga_spike} if ga_spike else {"source": "google_analytics", "comparison": "unavailable"},
                    {"source": "google_search_console", **gsc_spike} if gsc_spike else {"source": "google_search_console", "comparison": "unavailable"},
                ],
                confidence=confidence,
                suggested_next_check="Inspect Cloudflare bot/security, request path, status, and cache dimensions around the spike before deciding what caused it.",
                generated_at=generated_at,
                rule_id="network.cloudflare_request_spike",
            )
        )

    # Search-only spike family.
    if gsc_spike and gsc_spike["ratio"] >= SPIKE_RATIO:
        ga_support = ga_spike is not None and ga_spike["ratio"] >= MILD_SPIKE_RATIO
        cf_support = cf_spike is not None and cf_spike["ratio"] >= MILD_SPIKE_RATIO
        if not ga_support and not cf_support:
            findings.append(
                _finding(
                    finding_type="search_to_analytics_mismatch",
                    severity="info",
                    title="Search Console spiked without the same pattern in site-wide traffic",
                    explanation="Google Search activity rose sharply in Search Console, while the available GA4 and Cloudflare signals did not show a similar spike. Search Console is search-specific, so this can be a genuine search-discovery event rather than a site-wide traffic event.",
                    evidence=[
                        {"source": "google_search_console", **gsc_spike},
                        {"source": "google_analytics", **ga_spike} if ga_spike else {"source": "google_analytics", "comparison": "unavailable"},
                        {"source": "cloudflare", **cf_spike} if cf_spike else {"source": "cloudflare", "comparison": "unavailable"},
                    ],
                    confidence="medium",
                    suggested_next_check="Inspect the affected Search Console queries and landing pages before treating the spike as total-site growth.",
                    generated_at=generated_at,
                    rule_id="search.gsc_only_spike",
                )
            )

    # GA4 coverage suspicion can only be asserted when page-level search evidence exists and GA4 lacks comparable path evidence.
    gsc_breakdowns = gsc.get("normalized_breakdowns") if isinstance(gsc.get("normalized_breakdowns"), dict) else {}
    ga_breakdowns = ga.get("normalized_breakdowns") if isinstance(ga.get("normalized_breakdowns"), dict) else {}
    gsc_pages = gsc_breakdowns.get("top_pages") if isinstance(gsc_breakdowns.get("top_pages"), list) else []
    ga_pages = ga_breakdowns.get("landing_pages") if isinstance(ga_breakdowns.get("landing_pages"), list) else []
    if len(gsc_pages) >= 2 and not ga_pages and ga.get("availability") == "available":
        findings.append(
            _finding(
                finding_type="ga4_coverage_suspicion",
                severity="info",
                title="Path-level GA4 coverage cannot yet be verified",
                explanation="Search Console has page-level evidence for multiple URLs, but the current GA4 snapshot does not include a landing-page breakdown. TrafficVerdict therefore cannot claim that any section is under-tracked yet.",
                evidence=[{"source": "google_search_console", "page_evidence_count": len(gsc_pages)}, {"source": "google_analytics", "landing_page_breakdown": "not_collected"}],
                confidence="high",
                suggested_next_check="Collect GA4 landing-page breakdowns before diagnosing section-level tracking coverage.",
                generated_at=generated_at,
                rule_id="coverage.path_evidence_incomplete",
            )
        )

    # Site-change anomaly family is intentionally dormant until historical relationship baselines exist.
    # Keeping it explicit prevents a one-window comparison from masquerading as change detection.

    severity_rank = {"critical": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda item: (severity_rank.get(item["severity"], 9), item["rule_id"], item["title"]))

    warnings = [item for item in findings if item["severity"] in {"warning", "critical"}]
    if any(item["severity"] == "critical" for item in findings):
        overall_state = "attention_required"
    elif warnings:
        overall_state = "explainable_gaps_with_warnings"
    else:
        overall_state = "healthy_with_explainable_gaps"

    return {
        "site_id": normalized.get("site_id"),
        "canonical_window": normalized.get("canonical_window"),
        "normalization_version": normalized.get("normalization_version"),
        "engine_version": ENGINE_VERSION,
        "overall_state": overall_state,
        "finding_count": len(findings),
        "findings": findings,
        "generated_at": generated_at,
    }
