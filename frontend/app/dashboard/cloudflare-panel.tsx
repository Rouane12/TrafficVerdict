"use client";

import { useEffect, useState } from "react";

import { api } from "../../lib/api";

type CloudflareZone = {
  zone_id: string;
  name: string;
  status: string;
  account_name: string | null;
};

type CloudflareSnapshot = {
  period_start: string;
  period_end: string;
  metrics: {
    requests?: number;
    visits?: number;
    data_transfer_bytes?: number;
    sample_interval?: number;
  };
  breakdowns: Record<string, unknown>;
  created_at: string;
};

type CloudflareStatus = {
  configured: boolean;
  status: string;
  zone_id: string | null;
  zone_name: string | null;
  account_name: string | null;
  last_synced_at: string | null;
  last_error: string | null;
  latest_snapshot: CloudflareSnapshot | null;
};

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  if (value < 1024 * 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  return `${(value / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export function CloudflarePanel({ siteId }: { siteId: string }) {
  const [connection, setConnection] = useState<CloudflareStatus | null>(null);
  const [zones, setZones] = useState<CloudflareZone[]>([]);
  const [selectedZone, setSelectedZone] = useState("");
  const [apiToken, setApiToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function loadZones() {
    const nextZones = await api<CloudflareZone[]>(`/sites/${siteId}/integrations/cloudflare/zones`);
    setZones(nextZones);
    if (nextZones.length > 0) {
      setSelectedZone((current) => current || nextZones[0].zone_id);
    }
  }

  async function refresh() {
    const next = await api<CloudflareStatus>(`/sites/${siteId}/integrations/cloudflare/status`);
    setConnection(next);
    if (next.status === "zone_required") {
      await loadZones();
    }
  }

  useEffect(() => {
    setError("");
    void refresh().catch((caught) => {
      setError(caught instanceof Error ? caught.message : "Unable to load Cloudflare status");
    });
  }, [siteId]);

  async function connect() {
    if (!apiToken.trim()) return;
    setBusy(true);
    setError("");
    try {
      const next = await api<CloudflareStatus>(`/sites/${siteId}/integrations/cloudflare/connect`, {
        method: "POST",
        body: JSON.stringify({ api_token: apiToken.trim() }),
      });
      setConnection(next);
      setApiToken("");
      await loadZones();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to connect Cloudflare");
    } finally {
      setBusy(false);
    }
  }

  async function chooseZone() {
    if (!selectedZone) return;
    setBusy(true);
    setError("");
    try {
      const next = await api<CloudflareStatus>(`/sites/${siteId}/integrations/cloudflare/zone`, {
        method: "POST",
        body: JSON.stringify({ zone_id: selectedZone }),
      });
      setConnection(next);
      setZones([]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to select Cloudflare zone");
    } finally {
      setBusy(false);
    }
  }

  async function sync() {
    setBusy(true);
    setError("");
    try {
      const next = await api<CloudflareStatus>(`/sites/${siteId}/integrations/cloudflare/sync`, {
        method: "POST",
      });
      setConnection(next);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to sync Cloudflare");
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true);
    setError("");
    try {
      await api<void>(`/sites/${siteId}/integrations/cloudflare`, { method: "DELETE" });
      setZones([]);
      setSelectedZone("");
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to disconnect Cloudflare");
    } finally {
      setBusy(false);
    }
  }

  if (!connection) {
    return (
      <div className="provider-block">
        <div className="provider-row"><span>Cloudflare</span><span className="muted">Loading…</span></div>
        {error ? <p className="provider-error">{error}</p> : null}
      </div>
    );
  }

  const snapshot = connection.latest_snapshot;
  const sampleInterval = snapshot?.metrics.sample_interval ?? 1;

  return (
    <div className="provider-block">
      <div className="provider-row provider-row-rich">
        <div>
          <strong>Cloudflare</strong>
          {connection.zone_name ? <p className="muted small">{connection.zone_name}</p> : null}
        </div>

        {connection.status === "connected" ? (
          <div className="actions">
            <button className="button compact" type="button" disabled={busy} onClick={() => void sync()}>
              {busy ? "Syncing…" : "Sync now"}
            </button>
            <button className="button compact ghost" type="button" disabled={busy} onClick={() => void disconnect()}>
              Disconnect
            </button>
          </div>
        ) : connection.status === "zone_required" ? (
          <span className="status">Choose zone</span>
        ) : connection.status === "error" ? (
          <button className="button compact" type="button" disabled={busy} onClick={() => void disconnect()}>
            Reset connection
          </button>
        ) : null}
      </div>

      {connection.status === "disconnected" ? (
        <div className="provider-setup">
          <input
            className="input"
            type="password"
            value={apiToken}
            onChange={(event) => setApiToken(event.target.value)}
            placeholder="Cloudflare API token"
            autoComplete="off"
          />
          <button className="button compact" type="button" disabled={busy || !apiToken.trim()} onClick={() => void connect()}>
            {busy ? "Connecting…" : "Connect"}
          </button>
          <p className="muted small">Use a token with Zone Read and Analytics Read. The token is encrypted before storage.</p>
        </div>
      ) : null}

      {connection.status === "zone_required" ? (
        <div className="provider-setup">
          {zones.length > 0 ? (
            <>
              <select className="input" value={selectedZone} onChange={(event) => setSelectedZone(event.target.value)}>
                {zones.map((zone) => (
                  <option key={zone.zone_id} value={zone.zone_id}>
                    {zone.name}{zone.account_name ? ` — ${zone.account_name}` : ""}
                  </option>
                ))}
              </select>
              <button className="button compact" type="button" disabled={busy} onClick={() => void chooseZone()}>
                Use zone
              </button>
            </>
          ) : (
            <p className="muted small">No Cloudflare zones were found for this API token.</p>
          )}
        </div>
      ) : null}

      {snapshot ? (
        <div className="metric-strip">
          <div><span className="metric-value">{snapshot.metrics.requests ?? 0}</span><span className="metric-label">Requests</span></div>
          <div><span className="metric-value">{snapshot.metrics.visits ?? 0}</span><span className="metric-label">Visits</span></div>
          <div><span className="metric-value">{formatBytes(snapshot.metrics.data_transfer_bytes ?? 0)}</span><span className="metric-label">Data transfer</span></div>
          <div><span className="metric-value">{sampleInterval <= 1.01 ? "No" : `1:${sampleInterval.toFixed(1)}`}</span><span className="metric-label">Sampling</span></div>
        </div>
      ) : null}

      {connection.last_error ? <p className="provider-error">{connection.last_error}</p> : null}
      {error ? <p className="provider-error">{error}</p> : null}
    </div>
  );
}
