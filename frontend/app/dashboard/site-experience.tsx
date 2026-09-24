"use client";

import { FormEvent, useState } from "react";

import { AnomaliesPanel } from "./anomalies-panel";
import { CloudflarePanel } from "./cloudflare-panel";
import { GoogleAnalyticsPanel } from "./google-analytics-panel";
import { NormalizationPanel } from "./normalization-panel";
import { ReconciliationPanel } from "./reconciliation-panel";
import { SearchConsolePanel } from "./search-console-panel";
import { TrackingHealthSummary } from "./tracking-health-summary";
import { api } from "../../lib/api";

type Site = {
  id: string;
  workspace_id: string;
  name: string;
  domain: string;
  timezone: string;
};

type ExperienceTab = "overview" | "reconciliation" | "health" | "anomalies";

const TABS: { key: ExperienceTab; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "reconciliation", label: "Reconciliation" },
  { key: "health", label: "Tracking health" },
  { key: "anomalies", label: "Anomalies" },
];

export function SiteExperience({
  site,
  onUpdated,
  onDeleted,
}: {
  site: Site;
  onUpdated: (site: Site) => void;
  onDeleted: (siteId: string) => void;
}) {
  const [tab, setTab] = useState<ExperienceTab>("overview");
  const [analysisDays, setAnalysisDays] = useState<number | null>(null);
  const [editName, setEditName] = useState(site.name);
  const [editDomain, setEditDomain] = useState(site.domain);
  const [editTimezone, setEditTimezone] = useState(site.timezone);
  const [siteBusy, setSiteBusy] = useState(false);
  const [siteError, setSiteError] = useState("");

  async function saveSite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSiteBusy(true);
    setSiteError("");
    try {
      const updated = await api<Site>(`/workspaces/${site.workspace_id}/sites/${site.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: editName,
          domain: editDomain,
          timezone: editTimezone,
        }),
      });
      setEditName(updated.name);
      setEditDomain(updated.domain);
      setEditTimezone(updated.timezone);
      onUpdated(updated);
    } catch (caught) {
      setSiteError(caught instanceof Error ? caught.message : "Unable to update site");
    } finally {
      setSiteBusy(false);
    }
  }

  async function deleteSite() {
    if (!window.confirm(`Delete ${site.name} and all synced analytics data for this site? This cannot be undone.`)) {
      return;
    }

    setSiteBusy(true);
    setSiteError("");
    try {
      await api<void>(`/workspaces/${site.workspace_id}/sites/${site.id}`, {
        method: "DELETE",
      });
      onDeleted(site.id);
    } catch (caught) {
      setSiteError(caught instanceof Error ? caught.message : "Unable to delete site");
      setSiteBusy(false);
    }
  }

  return (
    <article className="site-card experience-card">
      <div className="site-card-heading experience-site-heading">
        <div>
          <span className="eyebrow">Site</span>
          <h2>{site.name}</h2>
          <p className="muted">{site.domain} · {site.timezone}</p>
        </div>
      </div>

      <nav className="experience-tabs" aria-label={`${site.name} dashboard views`}>
        {TABS.map((item) => (
          <button
            key={item.key}
            type="button"
            className={`experience-tab${tab === item.key ? " active" : ""}`}
            aria-pressed={tab === item.key}
            onClick={() => setTab(item.key)}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {tab === "overview" || tab === "reconciliation" ? (
        <div className="analysis-window-bar">
          <div>
            <span className="evidence-label">Analysis window</span>
            <p className="muted tiny">
              {analysisDays
                ? "Daily evidence is filtered to this window. Page/query diagnostics stay out unless their stored breakdown matches the selected range."
                : "Uses the common overlap across the synced sources and never invents unavailable history."}
            </p>
          </div>
          <label className="analysis-window-control">
            <span className="sr-only">Choose analysis window</span>
            <select
              className="input analysis-window-select"
              value={analysisDays ?? "available"}
              onChange={(event) =>
                setAnalysisDays(event.target.value === "available" ? null : Number(event.target.value))
              }
            >
              <option value="available">Available overlap</option>
              <option value="7">Last 7 days</option>
              <option value="14">Last 14 days</option>
              <option value="28">Last 28 days</option>
            </select>
          </label>
        </div>
      ) : null}

      {tab === "overview" ? (
        <div className="experience-view">
          <section className="experience-intro">
            <span className="eyebrow">Current verdict</span>
            <h3>What should I know about my traffic?</h3>
            <p className="muted">
              Start with the conclusion. Open Reconciliation only when you want the detailed evidence and next checks.
            </p>
          </section>
          <ReconciliationPanel
            siteId={site.id}
            days={analysisDays}
            variant="summary"
            onViewDetails={() => setTab("reconciliation")}
          />
        </div>
      ) : null}

      {tab === "reconciliation" ? (
        <div className="experience-view">
          <section className="experience-intro compact-intro">
            <span className="eyebrow">Reconciliation</span>
            <h3>See how the sources line up.</h3>
            <p className="muted">
              Normalized context first, then the deterministic findings that explain meaningful gaps without pretending unlike metrics should match.
            </p>
          </section>
          <NormalizationPanel siteId={site.id} days={analysisDays} />
          <ReconciliationPanel siteId={site.id} days={analysisDays} />
        </div>
      ) : null}

      {tab === "health" ? (
        <div className="experience-view">
          <section className="experience-intro compact-intro">
            <span className="eyebrow">Tracking health</span>
            <h3>Is my measurement setup healthy?</h3>
            <p className="muted">
              Start with connection, freshness, and coverage health. Use the source controls below only when you need to sync, reconnect, or inspect raw metrics.
            </p>
          </section>
          <TrackingHealthSummary siteId={site.id} />
          <div className="health-controls-heading">
            <div>
              <span className="evidence-label">Source controls</span>
              <p className="muted small">Manual sync and connection management.</p>
            </div>
          </div>
          <div className="provider-grid experience-provider-grid">
            <GoogleAnalyticsPanel siteId={site.id} />
            <SearchConsolePanel siteId={site.id} />
            <CloudflarePanel siteId={site.id} />
          </div>
        </div>
      ) : null}

      {tab === "anomalies" ? (
        <div className="experience-view">
          <section className="experience-intro compact-intro">
            <span className="eyebrow">Anomalies</span>
            <h3>What changed compared with the previous week?</h3>
            <p className="muted">
              TrafficVerdict compares synced daily history and flags large changes or source relationships that moved unusually. It reports the pattern without guessing the cause.
            </p>
          </section>
          <AnomaliesPanel siteId={site.id} />
        </div>
      ) : null}

      <details className="panel site-setup-disclosure">
        <summary>Site settings</summary>
        <div className="site-setup-body">
          <span className="eyebrow">Site settings</span>
          <h3>Edit this site</h3>
          <form className="site-form" onSubmit={saveSite}>
            <input
              className="input"
              value={editName}
              onChange={(event) => setEditName(event.target.value)}
              maxLength={120}
              required
              aria-label="Site name"
            />
            <input
              className="input"
              value={editDomain}
              onChange={(event) => setEditDomain(event.target.value)}
              maxLength={255}
              required
              aria-label="Site domain"
            />
            <input
              className="input"
              value={editTimezone}
              onChange={(event) => setEditTimezone(event.target.value)}
              maxLength={64}
              required
              aria-label="Site timezone"
            />
            <button className="button compact" type="submit" disabled={siteBusy}>
              {siteBusy ? "Saving…" : "Save changes"}
            </button>
          </form>

          <div className="account-danger-zone">
            <span className="eyebrow">Danger zone</span>
            <p className="muted small">
              Deleting a site permanently removes its connections, synced metrics, and sync history.
            </p>
            <button className="button danger-button" type="button" disabled={siteBusy} onClick={() => void deleteSite()}>
              Delete site
            </button>
          </div>

          {siteError ? <p className="form-error">{siteError}</p> : null}
        </div>
      </details>
    </article>
  );
}
