"use client";

import { useEffect, useState } from "react";

import { api } from "../../lib/api";

type SourceState = {
  label: string;
  availability: string;
  freshness: { state: string; data_lag_days: number | null; delayed: boolean };
  date_alignment: { source_timezone: string; target_timezone: string; mode: string };
};

type DimensionValue = { source: string; metric: string; value: number | string; semantic: string };
type Dimension = { key: string; label: string; comparison_mode: string; note: string; values: DimensionValue[] };

type NormalizationResponse = {
  canonical_hostname: string;
  canonical_timezone: string;
  canonical_window: { start: string; end: string; days: number; requested_days?: number | null; available_days?: number } | null;
  sources: Record<string, SourceState>;
  dimensions: Dimension[];
  warnings: string[];
  normalization_version: string;
};

function freshnessLabel(source: SourceState) {
  if (source.availability !== "available") return "Missing";
  if (source.freshness.state === "historical") return "Historical";
  if (source.freshness.delayed) return `Delayed · ${source.freshness.data_lag_days ?? "?"}d`;
  return `Fresh · ${source.freshness.data_lag_days ?? 0}d lag`;
}

export function NormalizationPanel({ siteId, days = null }: { siteId: string; days?: number | null }) {
  const [data, setData] = useState<NormalizationResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    setBusy(true);
    setError("");
    try {
      const query = days ? `?days=${days}` : "";
      setData(await api<NormalizationResponse>(`/sites/${siteId}/normalization${query}`));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to normalize source evidence");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, [siteId, days]);

  return (
    <section className="normalization-panel">
      <div className="normalization-heading">
        <div>
          <span className="eyebrow">Normalized evidence</span>
          <h3>Comparable source context</h3>
          {data?.canonical_window ? (
            <p className="muted small">
              {data.canonical_window.start} → {data.canonical_window.end} · {data.canonical_window.days} days · {data.canonical_timezone}
            </p>
          ) : (
            <p className="muted small">Waiting for an overlapping source window.</p>
          )}
        </div>
        <button className="button compact ghost" type="button" disabled={busy} onClick={() => void refresh()}>
          {busy ? "Normalizing…" : "Refresh evidence"}
        </button>
      </div>

      {data ? (
        <>
          <div className="freshness-strip">
            {Object.entries(data.sources).map(([key, source]) => (
              <div key={key}>
                <strong>{source.label}</strong>
                <span className="muted small">{freshnessLabel(source)}</span>
                <span className="muted tiny">
                  {source.date_alignment.mode === "date_label_only"
                    ? `${source.date_alignment.source_timezone} → ${source.date_alignment.target_timezone}`
                    : source.date_alignment.target_timezone}
                </span>
              </div>
            ))}
          </div>

          <div className="dimension-list">
            {data.dimensions.map((dimension) => (
              <div className="dimension-row" key={dimension.key}>
                <div>
                  <strong>{dimension.label}</strong>
                  <p className="muted tiny">{dimension.note}</p>
                </div>
                <div className="dimension-values">
                  {dimension.values.map((value) => (
                    <span className="status" key={`${value.source}-${value.metric}`}>
                      {value.source === "google_analytics" ? "GA4" : value.source === "google_search_console" ? "GSC" : "CF"}: {String(value.value)} {value.metric}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {data.warnings.length ? (
            <details className="normalization-warnings">
              <summary>{data.warnings.length} normalization note{data.warnings.length === 1 ? "" : "s"}</summary>
              <ul>{data.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
            </details>
          ) : null}
        </>
      ) : null}

      {error ? <p className="provider-error normalization-error">{error}</p> : null}
    </section>
  );
}
