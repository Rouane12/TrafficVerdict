"use client";

import { useEffect, useState } from "react";

import { api } from "../../lib/api";

type Finding = {
  finding_type: string;
  severity: string;
  title: string;
  explanation: string;
  source_evidence: Record<string, unknown>[];
  confidence: string;
  suggested_next_check: string;
  generated_at: string;
  rule_version: string;
  rule_id: string;
};

type ReconciliationResponse = {
  site_id: string;
  canonical_window: { start?: string; end?: string; days?: number } | null;
  normalization_version: string;
  engine_version: string;
  overall_state: string;
  finding_count: number;
  findings: Finding[];
  generated_at: string;
};

type ReconciliationPanelProps = {
  siteId: string;
  days?: number | null;
  variant?: "full" | "summary";
  onViewDetails?: () => void;
};

function headline(state: string) {
  if (state === "attention_required") return "Attention required";
  if (state === "explainable_gaps_with_warnings") return "Explainable gaps — with warnings";
  return "Your analytics are explainable";
}

function sourceLabel(source: unknown) {
  if (source === "google_analytics") return "GA4";
  if (source === "google_search_console") return "GSC";
  if (source === "cloudflare") return "Cloudflare";
  return String(source ?? "Evidence");
}

function evidenceSummary(item: Record<string, unknown>) {
  const parts = Object.entries(item)
    .filter(([key]) => key !== "source")
    .map(([key, value]) => `${key.replaceAll("_", " ")}: ${Array.isArray(value) ? value.join(", ") : String(value)}`);
  return parts.join(" · ");
}

export function ReconciliationPanel({ siteId, days = null, variant = "full", onViewDetails }: ReconciliationPanelProps) {
  const [data, setData] = useState<ReconciliationResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);

  async function refresh() {
    setBusy(true);
    setError("");
    try {
      const query = days ? `?days=${days}` : "";
      setData(await api<ReconciliationResponse>(`/sites/${siteId}/reconciliation${query}`));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to reconcile analytics evidence");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, [siteId, days]);

  useEffect(() => {
    if (!selectedFinding) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setSelectedFinding(null);
    }

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [selectedFinding]);

  if (variant === "summary") {
    return (
      <section className="reconciliation-panel reconciliation-summary-panel">
        <div className="reconciliation-heading">
          <div>
            <span className="eyebrow">TrafficVerdict</span>
            <h3>{data ? headline(data.overall_state) : "Building your verdict…"}</h3>
            <p className="muted small">
              {data?.canonical_window?.start && data?.canonical_window?.end
                ? `${data.canonical_window.start} → ${data.canonical_window.end}`
                : "Deterministic reconciliation from normalized evidence."}
            </p>
          </div>
          <button className="button compact" type="button" disabled={busy} onClick={() => void refresh()}>
            {busy ? "Reconciling…" : "Run verdict"}
          </button>
        </div>

        {!data && !error ? (
          <div className="state-card state-loading" role="status" aria-live="polite">
            <span className="state-pulse" aria-hidden="true" />
            <div>
              <strong>Analyzing synced evidence…</strong>
              <p className="muted small">TrafficVerdict is normalizing the selected window and running deterministic rules.</p>
            </div>
          </div>
        ) : null}

        {data ? (
          <div className="verdict-summary">
            <div className="verdict-summary-count">
              <strong>{data.finding_count}</strong>
              <span className="muted small">current finding{data.finding_count === 1 ? "" : "s"}</span>
            </div>
            <div className="verdict-summary-list">
              {data.findings.slice(0, 3).map((finding) => (
                <div className="verdict-summary-item" key={`${finding.rule_id}-${finding.title}`}>
                  <span className={`finding-dot severity-${finding.severity}`} aria-hidden="true" />
                  <div>
                    <strong>{finding.title}</strong>
                    <span className="muted tiny">{finding.confidence} confidence</span>
                  </div>
                </div>
              ))}
            </div>
            {onViewDetails ? (
              <button className="button ghost compact" type="button" onClick={onViewDetails}>
                See reconciliation
              </button>
            ) : null}
          </div>
        ) : null}

        {error ? (
          <div className="state-card state-error reconciliation-summary-error" role="alert">
            <div>
              <strong>We couldn’t build this verdict.</strong>
              <p className="muted small">{error}</p>
            </div>
            <button className="button ghost compact" type="button" onClick={() => void refresh()}>Try again</button>
          </div>
        ) : null}
      </section>
    );
  }

  return (
    <>
      <section className="reconciliation-panel">
        <div className="reconciliation-heading">
          <div>
            <span className="eyebrow">TrafficVerdict</span>
            <h3>{data ? headline(data.overall_state) : "Building your verdict…"}</h3>
            <p className="muted small">
              {data?.canonical_window?.start && data?.canonical_window?.end
                ? `${data.canonical_window.start} → ${data.canonical_window.end} · ${data.finding_count} finding${data.finding_count === 1 ? "" : "s"}`
                : "Deterministic reconciliation from normalized evidence."}
            </p>
          </div>
          <button className="button compact" type="button" disabled={busy} onClick={() => void refresh()}>
            {busy ? "Reconciling…" : "Run verdict"}
          </button>
        </div>

        {!data && !error ? (
          <div className="state-card state-loading" role="status" aria-live="polite">
            <span className="state-pulse" aria-hidden="true" />
            <div>
              <strong>Reconciling your sources…</strong>
              <p className="muted small">This should only take a moment.</p>
            </div>
          </div>
        ) : null}

        {data ? (
          data.finding_count === 0 ? (
            <div className="state-card state-empty">
              <div>
                <strong>No findings for this window.</strong>
                <p className="muted small">The available evidence did not trigger any reconciliation rule. This is not a guarantee that tracking is perfect.</p>
              </div>
            </div>
          ) : (
          <div className="finding-list">
            {data.findings.map((finding) => (
              <article className={`finding-card severity-${finding.severity}`} key={`${finding.rule_id}-${finding.title}`}>
                <div className="finding-title-row">
                  <div>
                    <span className="finding-severity">{finding.severity}</span>
                    <h4>{finding.title}</h4>
                  </div>
                  <span className="status">{finding.confidence} confidence</span>
                </div>
                <p className="muted finding-explanation">{finding.explanation}</p>
                <div className="finding-next">
                  <strong>Next check</strong>
                  <span className="muted small">{finding.suggested_next_check}</span>
                </div>
                <button className="finding-evidence-button" type="button" onClick={() => setSelectedFinding(finding)}>
                  View evidence
                  <span aria-hidden="true">→</span>
                </button>
              </article>
            ))}
          </div>
          )
        ) : null}

        {error ? (
          <div className="state-card state-error" role="alert">
            <div>
              <strong>Reconciliation couldn’t load.</strong>
              <p className="muted small">{error}</p>
            </div>
            <button className="button ghost compact" type="button" onClick={() => void refresh()}>Try again</button>
          </div>
        ) : null}
      </section>

      {selectedFinding ? (
        <div className="evidence-overlay" role="presentation" onMouseDown={() => setSelectedFinding(null)}>
          <aside
            className="evidence-drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="evidence-drawer-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="evidence-drawer-header">
              <div>
                <span className="eyebrow">Evidence</span>
                <h3 id="evidence-drawer-title">{selectedFinding.title}</h3>
              </div>
              <button className="evidence-close" type="button" aria-label="Close evidence" autoFocus onClick={() => setSelectedFinding(null)}>
                ×
              </button>
            </div>

            <div className="evidence-meta">
              <span className="status">{selectedFinding.confidence} confidence</span>
              <span className="status">{selectedFinding.severity}</span>
              {data?.canonical_window?.start && data?.canonical_window?.end ? (
                <span className="status">
                  {data.canonical_window.start} → {data.canonical_window.end}
                </span>
              ) : null}
            </div>

            <section className="evidence-drawer-section">
              <span className="evidence-label">Why this finding exists</span>
              <p className="muted">{selectedFinding.explanation}</p>
            </section>

            <section className="evidence-drawer-section">
              <span className="evidence-label">Source evidence</span>
              <div className="finding-evidence-list drawer-evidence-list">
                {selectedFinding.source_evidence.map((item, index) => (
                  <div key={`${selectedFinding.rule_id}-${index}`}>
                    <strong>{sourceLabel(item.source)}</strong>
                    <span className="muted tiny">{evidenceSummary(item)}</span>
                  </div>
                ))}
              </div>
            </section>

            <section className="evidence-drawer-section">
              <span className="evidence-label">Next check</span>
              <p className="muted">{selectedFinding.suggested_next_check}</p>
            </section>

            <section className="evidence-drawer-section evidence-rule-meta">
              <div>
                <span className="evidence-label">Rule</span>
                <code>{selectedFinding.rule_id}</code>
              </div>
              <div>
                <span className="evidence-label">Rule version</span>
                <span>{selectedFinding.rule_version}</span>
              </div>
              {data?.canonical_window?.start && data?.canonical_window?.end ? (
                <div>
                  <span className="evidence-label">Analysis window</span>
                  <span>
                    {data.canonical_window.start} → {data.canonical_window.end}
                    {data.canonical_window.days ? ` · ${data.canonical_window.days} days` : ""}
                  </span>
                </div>
              ) : null}
              <div>
                <span className="evidence-label">Generated</span>
                <span>{new Date(selectedFinding.generated_at).toLocaleString()}</span>
              </div>
            </section>
          </aside>
        </div>
      ) : null}
    </>
  );
}
