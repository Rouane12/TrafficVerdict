"use client";

import { useEffect, useMemo, useState } from "react";

import { api } from "../../lib/api";

type Freshness = {
  state: string;
  data_lag_days: number | null;
  expected_lag_days: number;
  delayed: boolean;
};

type NormalizedSource = {
  label: string;
  connection_state: string;
  availability: string;
  freshness: Freshness;
  last_synced_at: string | null;
};

type NormalizationResponse = {
  sources: Record<string, NormalizedSource>;
  warnings: string[];
};

type ProviderStatus = {
  status: string;
  last_synced_at: string | null;
  last_error: string | null;
  property_name?: string | null;
  site_name?: string | null;
  zone_name?: string | null;
};

type Finding = {
  finding_type: string;
  severity: string;
  title: string;
  explanation: string;
  confidence: string;
  rule_id: string;
};

type ReconciliationResponse = {
  findings: Finding[];
};

type SourceKey = "google_analytics" | "google_search_console" | "cloudflare";

const SOURCE_ORDER: SourceKey[] = ["google_analytics", "google_search_console", "cloudflare"];

const SOURCE_SHORT: Record<SourceKey, string> = {
  google_analytics: "GA4",
  google_search_console: "Search Console",
  cloudflare: "Cloudflare",
};

function resourceLabel(key: SourceKey, status: ProviderStatus | undefined) {
  if (!status) return "Loading source details…";
  if (key === "google_analytics") return status.property_name || "No GA4 property selected";
  if (key === "google_search_console") return status.site_name || "No Search Console property selected";
  return status.zone_name || "No Cloudflare zone selected";
}

function sourceHealth(source: NormalizedSource | undefined, status: ProviderStatus | undefined) {
  if (!source || !status) return { state: "Loading", tone: "neutral", detail: "Checking source status" };
  if (status.last_error) return { state: "Needs attention", tone: "danger", detail: "The last source operation reported an error" };
  if (source.connection_state !== "connected") return { state: "Needs setup", tone: "warning", detail: "Connection is not fully active" };
  if (source.availability !== "available") return { state: "Waiting for data", tone: "warning", detail: "Connected, but no usable snapshot is available yet" };
  if (source.freshness.delayed) {
    return {
      state: "Delayed",
      tone: "warning",
      detail: `Data is ${source.freshness.data_lag_days ?? "?"} days behind`,
    };
  }
  return {
    state: "Healthy",
    tone: "healthy",
    detail: `Fresh · ${source.freshness.data_lag_days ?? 0}d lag`,
  };
}

function formatSync(value: string | null | undefined) {
  if (!value) return "Never synced";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

export function TrackingHealthSummary({ siteId }: { siteId: string }) {
  const [normalization, setNormalization] = useState<NormalizationResponse | null>(null);
  const [statuses, setStatuses] = useState<Partial<Record<SourceKey, ProviderStatus>>>({});
  const [findings, setFindings] = useState<Finding[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    setBusy(true);
    setError("");
    try {
      const [normalized, ga, gsc, cf, reconciliation] = await Promise.all([
        api<NormalizationResponse>(`/sites/${siteId}/normalization`),
        api<ProviderStatus>(`/sites/${siteId}/integrations/google/status`),
        api<ProviderStatus>(`/sites/${siteId}/integrations/search-console/status`),
        api<ProviderStatus>(`/sites/${siteId}/integrations/cloudflare/status`),
        api<ReconciliationResponse>(`/sites/${siteId}/reconciliation`),
      ]);

      setNormalization(normalized);
      setStatuses({
        google_analytics: ga,
        google_search_console: gsc,
        cloudflare: cf,
      });
      setFindings(
        reconciliation.findings.filter(
          (finding) =>
            finding.rule_id.startsWith("source.") ||
            finding.rule_id.startsWith("coverage.") ||
            finding.severity === "critical" ||
            finding.severity === "warning",
        ),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load tracking health");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, [siteId]);

  const sourceCards = useMemo(
    () =>
      SOURCE_ORDER.map((key) => {
        const source = normalization?.sources[key];
        const status = statuses[key];
        return { key, source, status, health: sourceHealth(source, status) };
      }),
    [normalization, statuses],
  );

  const healthyCount = sourceCards.filter((item) => item.health.state === "Healthy").length;
  const hasAttention = sourceCards.some((item) => item.health.tone === "danger" || item.health.tone === "warning");

  return (
    <section className="tracking-health-summary">
      <div className="tracking-health-heading">
        <div>
          <span className="eyebrow">Source health</span>
          <h4>{hasAttention ? "Some sources need attention" : "All connected sources look healthy"}</h4>
          <p className="muted small">
            {healthyCount} of {SOURCE_ORDER.length} sources are connected, usable, and within their expected reporting lag.
          </p>
        </div>
        <button className="button compact ghost" type="button" disabled={busy} onClick={() => void refresh()}>
          {busy ? "Checking…" : "Check health"}
        </button>
      </div>

      <div className="tracking-health-grid">
        {sourceCards.map(({ key, source, status, health }) => (
          <article className="tracking-health-card" key={key}>
            <div className="tracking-health-card-top">
              <div>
                <strong>{SOURCE_SHORT[key]}</strong>
                <p className="muted tiny">{resourceLabel(key, status)}</p>
              </div>
              <span className={`health-pill health-${health.tone}`}>{health.state}</span>
            </div>

            <div className="tracking-health-facts">
              <div>
                <span className="evidence-label">Status</span>
                <span>{source?.connection_state ?? status?.status ?? "Loading"}</span>
              </div>
              <div>
                <span className="evidence-label">Freshness</span>
                <span>{health.detail}</span>
              </div>
              <div>
                <span className="evidence-label">Last successful sync</span>
                <span>{formatSync(source?.last_synced_at ?? status?.last_synced_at)}</span>
              </div>
            </div>

            {status?.last_error ? <p className="provider-error tracking-health-error">{status.last_error}</p> : null}
          </article>
        ))}
      </div>

      {findings.length > 0 ? (
        <div className="health-notes">
          <span className="evidence-label">Coverage and measurement notes</span>
          {findings.map((finding) => (
            <div className="health-note" key={finding.rule_id}>
              <span className={`finding-dot severity-${finding.severity}`} aria-hidden="true" />
              <div>
                <strong>{finding.title}</strong>
                <p className="muted tiny">{finding.explanation}</p>
              </div>
              <span className="status">{finding.confidence} confidence</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="health-clear-state">
          <strong>No connection or freshness warnings detected.</strong>
          <p className="muted small">TrafficVerdict found no stale-sync or missing-source warnings that need action right now.</p>
        </div>
      )}

      {error ? <p className="provider-error tracking-health-load-error">{error}</p> : null}
    </section>
  );
}
