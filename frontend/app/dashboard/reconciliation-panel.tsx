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
    .slice(0, 4)
    .map(([key, value]) => `${key.replaceAll("_", " ")}: ${Array.isArray(value) ? value.join(", ") : String(value)}`);
  return parts.join(" · ");
}

export function ReconciliationPanel({ siteId }: { siteId: string }) {
  const [data, setData] = useState<ReconciliationResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    setBusy(true);
    setError("");
    try {
      setData(await api<ReconciliationResponse>(`/sites/${siteId}/reconciliation`));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to reconcile analytics evidence");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, [siteId]);

  return (
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

      {data ? (
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
              <details className="finding-evidence">
                <summary>Evidence · {finding.rule_id}</summary>
                <div className="finding-evidence-list">
                  {finding.source_evidence.map((item, index) => (
                    <div key={`${finding.rule_id}-${index}`}>
                      <strong>{sourceLabel(item.source)}</strong>
                      <span className="muted tiny">{evidenceSummary(item)}</span>
                    </div>
                  ))}
                </div>
              </details>
            </article>
          ))}
        </div>
      ) : null}

      {error ? <p className="provider-error">{error}</p> : null}
    </section>
  );
}
