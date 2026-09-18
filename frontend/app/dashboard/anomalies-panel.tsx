"use client";

import { useEffect, useState } from "react";

import { api } from "../../lib/api";

type ChangeComparison = {
  source: string;
  label: string;
  metric: string;
  previous: number;
  current: number;
  change_percent: number | null;
  direction: string;
  previous_start?: string | null;
  previous_end?: string | null;
  current_start?: string | null;
  current_end?: string | null;
  previous_date?: string | null;
  current_date?: string | null;
};

type ChangeAnomaly = {
  anomaly_type: string;
  severity: string;
  title: string;
  explanation: string;
  confidence: string;
  source_evidence: Record<string, unknown>[];
};

type ChangeResponse = {
  site_id: string;
  state: string;
  summary: string;
  analysis_window: { start?: string; end?: string; days?: number } | null;
  weekly_comparisons: ChangeComparison[];
  daily_comparisons: ChangeComparison[];
  anomalies: ChangeAnomaly[];
  change_detection_version: string;
};

function formatChange(value: number | null) {
  if (value === null) return "No baseline";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

export function AnomaliesPanel({ siteId }: { siteId: string }) {
  const [data, setData] = useState<ChangeResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    setBusy(true);
    setError("");
    try {
      setData(await api<ChangeResponse>(`/sites/${siteId}/changes`));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to compare synced history");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, [siteId]);

  return (
    <section className="anomaly-panel">
      <div className="anomaly-heading">
        <div>
          <span className="eyebrow">Change detection</span>
          <h4>{data?.summary ?? "Comparing synced history…"}</h4>
          {data?.analysis_window?.start && data?.analysis_window?.end ? (
            <p className="muted small">
              {data.analysis_window.start} → {data.analysis_window.end} · latest 7 days compared with the previous 7
            </p>
          ) : (
            <p className="muted small">TrafficVerdict needs enough daily history before it can compare periods.</p>
          )}
        </div>
        <button className="button compact ghost" type="button" disabled={busy} onClick={() => void refresh()}>
          {busy ? "Checking…" : "Check changes"}
        </button>
      </div>

      {!data && !error ? (
        <div className="state-card state-loading" role="status" aria-live="polite">
          <span className="state-pulse" aria-hidden="true" />
          <div>
            <strong>Building the comparison…</strong>
            <p className="muted small">Using the daily history already stored by your connected sources.</p>
          </div>
        </div>
      ) : null}

      {data?.weekly_comparisons.length ? (
        <div className="change-grid">
          {data.weekly_comparisons.map((item) => (
            <article className="change-card" key={item.source}>
              <div className="change-card-top">
                <div>
                  <strong>{item.label}</strong>
                  <p className="muted tiny">{item.metric}</p>
                </div>
                <span className={`change-pill change-${item.direction}`}>{formatChange(item.change_percent)}</span>
              </div>
              <div className="change-values">
                <div>
                  <span className="evidence-label">Previous 7 days</span>
                  <strong>{item.previous}</strong>
                </div>
                <span aria-hidden="true">→</span>
                <div>
                  <span className="evidence-label">Latest 7 days</span>
                  <strong>{item.current}</strong>
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : null}

      {data ? (
        data.anomalies.length ? (
          <div className="anomaly-list">
            {data.anomalies.map((anomaly) => (
              <article className={`finding-card severity-${anomaly.severity}`} key={`${anomaly.anomaly_type}-${anomaly.title}`}>
                <div className="finding-title-row">
                  <div>
                    <span className="finding-severity">{anomaly.severity}</span>
                    <h4>{anomaly.title}</h4>
                  </div>
                  <span className="status">{anomaly.confidence} confidence</span>
                </div>
                <p className="muted finding-explanation">{anomaly.explanation}</p>
              </article>
            ))}
          </div>
        ) : (
          <div className="state-card state-empty">
            <div>
              <strong>{data.state === "insufficient_history" ? "Not enough history yet." : "No major anomaly detected."}</strong>
              <p className="muted small">
                {data.state === "insufficient_history"
                  ? "Scheduled syncing will build more history automatically."
                  : "The latest week did not trigger the current deterministic change rules."}
              </p>
            </div>
          </div>
        )
      ) : null}

      {error ? (
        <div className="state-card state-error" role="alert">
          <div>
            <strong>Change detection couldn’t load.</strong>
            <p className="muted small">{error}</p>
          </div>
          <button className="button ghost compact" type="button" onClick={() => void refresh()}>Try again</button>
        </div>
      ) : null}
    </section>
  );
}
