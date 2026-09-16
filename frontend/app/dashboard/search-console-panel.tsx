"use client";

import { useEffect, useState } from "react";

import { api, apiUrl } from "../../lib/api";

type SearchConsoleSite = {
  site_url: string;
  display_name: string;
  permission_level: string;
};

type SearchConsoleSnapshot = {
  period_start: string;
  period_end: string;
  metrics: {
    clicks?: number;
    impressions?: number;
    ctr?: number;
    average_position?: number;
  };
  breakdowns: Record<string, unknown>;
  created_at: string;
};

type SearchConsoleStatus = {
  configured: boolean;
  status: string;
  site_url: string | null;
  site_name: string | null;
  permission_level: string | null;
  last_synced_at: string | null;
  last_error: string | null;
  latest_snapshot: SearchConsoleSnapshot | null;
};

export function SearchConsolePanel({ siteId }: { siteId: string }) {
  const [connection, setConnection] = useState<SearchConsoleStatus | null>(null);
  const [sites, setSites] = useState<SearchConsoleSite[]>([]);
  const [selectedSite, setSelectedSite] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function loadSites() {
    const nextSites = await api<SearchConsoleSite[]>(`/sites/${siteId}/integrations/search-console/sites`);
    setSites(nextSites);
    if (nextSites.length > 0) {
      setSelectedSite((current) => current || nextSites[0].site_url);
    }
  }

  async function refresh() {
    const next = await api<SearchConsoleStatus>(`/sites/${siteId}/integrations/search-console/status`);
    setConnection(next);
    if (next.status === "site_required") {
      await loadSites();
    }
  }

  useEffect(() => {
    setError("");
    void refresh().catch((caught) => {
      setError(caught instanceof Error ? caught.message : "Unable to load Search Console status");
    });
  }, [siteId]);

  function connect() {
    window.location.assign(apiUrl(`/sites/${siteId}/integrations/search-console/start`));
  }

  async function chooseSite() {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      const next = await api<SearchConsoleStatus>(`/sites/${siteId}/integrations/search-console/site`, {
        method: "POST",
        body: JSON.stringify({ site_url: selectedSite }),
      });
      setConnection(next);
      setSites([]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to select Search Console property");
    } finally {
      setBusy(false);
    }
  }

  async function sync() {
    setBusy(true);
    setError("");
    try {
      const next = await api<SearchConsoleStatus>(`/sites/${siteId}/integrations/search-console/sync`, {
        method: "POST",
      });
      setConnection(next);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to sync Search Console");
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true);
    setError("");
    try {
      await api<void>(`/sites/${siteId}/integrations/search-console`, { method: "DELETE" });
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to disconnect Search Console");
    } finally {
      setBusy(false);
    }
  }

  if (!connection) {
    return (
      <div className="provider-block">
        <div className="provider-row"><span>Search Console</span><span className="muted">Loading…</span></div>
        {error ? <p className="provider-error">{error}</p> : null}
      </div>
    );
  }

  const snapshot = connection.latest_snapshot;
  const ctr = ((snapshot?.metrics.ctr ?? 0) * 100).toFixed(1);
  const position = (snapshot?.metrics.average_position ?? 0).toFixed(1);

  return (
    <div className="provider-block">
      <div className="provider-row provider-row-rich">
        <div>
          <strong>Search Console</strong>
          {connection.site_name ? <p className="muted small">{connection.site_name}</p> : null}
        </div>

        {!connection.configured ? (
          <span className="status">OAuth setup required</span>
        ) : connection.status === "disconnected" ? (
          <button className="button compact" type="button" onClick={connect}>Connect</button>
        ) : connection.status === "site_required" ? (
          <span className="status">Choose property</span>
        ) : connection.status === "connected" ? (
          <div className="actions">
            <button className="button compact" type="button" disabled={busy} onClick={() => void sync()}>
              {busy ? "Syncing…" : "Sync now"}
            </button>
            <button className="button compact ghost" type="button" disabled={busy} onClick={() => void disconnect()}>
              Disconnect
            </button>
          </div>
        ) : (
          <button className="button compact" type="button" onClick={connect}>Reconnect</button>
        )}
      </div>

      {connection.status === "site_required" ? (
        <div className="provider-setup">
          {sites.length > 0 ? (
            <>
              <select
                className="input"
                value={selectedSite}
                onChange={(event) => setSelectedSite(event.target.value)}
              >
                {sites.map((site) => (
                  <option key={site.site_url} value={site.site_url}>
                    {site.display_name} — {site.permission_level}
                  </option>
                ))}
              </select>
              <button className="button compact" type="button" disabled={busy} onClick={() => void chooseSite()}>
                Use property
              </button>
            </>
          ) : (
            <p className="muted small">No verified Search Console properties were found for this Google account.</p>
          )}
        </div>
      ) : null}

      {snapshot ? (
        <div className="metric-strip">
          <div><span className="metric-value">{snapshot.metrics.clicks ?? 0}</span><span className="metric-label">Clicks</span></div>
          <div><span className="metric-value">{snapshot.metrics.impressions ?? 0}</span><span className="metric-label">Impressions</span></div>
          <div><span className="metric-value">{ctr}%</span><span className="metric-label">CTR</span></div>
          <div><span className="metric-value">{position}</span><span className="metric-label">Avg position</span></div>
        </div>
      ) : null}

      {connection.last_error ? <p className="provider-error">{connection.last_error}</p> : null}
      {error ? <p className="provider-error">{error}</p> : null}
    </div>
  );
}
