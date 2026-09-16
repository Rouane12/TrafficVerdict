"use client";

import { useEffect, useState } from "react";

import { api, apiUrl } from "../../lib/api";

type GoogleProperty = {
  property_id: string;
  property_name: string;
  account_id: string;
  account_name: string;
};

type GoogleSnapshot = {
  period_start: string;
  period_end: string;
  metrics: {
    active_users?: number;
    sessions?: number;
    views?: number;
    engaged_sessions?: number;
  };
  breakdowns: Record<string, unknown>;
  created_at: string;
};

type GoogleStatus = {
  configured: boolean;
  status: string;
  property_id: string | null;
  property_name: string | null;
  account_id: string | null;
  last_synced_at: string | null;
  last_error: string | null;
  latest_snapshot: GoogleSnapshot | null;
};

export function GoogleAnalyticsPanel({ siteId }: { siteId: string }) {
  const [connection, setConnection] = useState<GoogleStatus | null>(null);
  const [properties, setProperties] = useState<GoogleProperty[]>([]);
  const [selectedProperty, setSelectedProperty] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function loadProperties() {
    const nextProperties = await api<GoogleProperty[]>(`/sites/${siteId}/integrations/google/properties`);
    setProperties(nextProperties);
    if (nextProperties.length > 0) {
      setSelectedProperty((current) => current || nextProperties[0].property_id);
    }
  }

  async function refresh() {
    const next = await api<GoogleStatus>(`/sites/${siteId}/integrations/google/status`);
    setConnection(next);
    if (next.status === "property_required") {
      await loadProperties();
    }
  }

  useEffect(() => {
    setError("");
    void refresh().catch((caught) => {
      setError(caught instanceof Error ? caught.message : "Unable to load Google Analytics status");
    });
  }, [siteId]);

  function connect() {
    window.location.assign(apiUrl(`/sites/${siteId}/integrations/google/start`));
  }

  async function chooseProperty() {
    if (!selectedProperty) return;
    setBusy(true);
    setError("");
    try {
      const next = await api<GoogleStatus>(`/sites/${siteId}/integrations/google/property`, {
        method: "POST",
        body: JSON.stringify({ property_id: selectedProperty }),
      });
      setConnection(next);
      setProperties([]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to select GA4 property");
    } finally {
      setBusy(false);
    }
  }

  async function sync() {
    setBusy(true);
    setError("");
    try {
      const next = await api<GoogleStatus>(`/sites/${siteId}/integrations/google/sync`, {
        method: "POST",
      });
      setConnection(next);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to sync Google Analytics");
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true);
    setError("");
    try {
      await api<void>(`/sites/${siteId}/integrations/google`, { method: "DELETE" });
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to disconnect Google Analytics");
    } finally {
      setBusy(false);
    }
  }

  if (!connection) {
    return (
      <div className="provider-block">
        <div className="provider-row"><span>Google Analytics</span><span className="muted">Loading…</span></div>
        {error ? <p className="provider-error">{error}</p> : null}
      </div>
    );
  }

  const snapshot = connection.latest_snapshot;

  return (
    <div className="provider-block">
      <div className="provider-row provider-row-rich">
        <div>
          <strong>Google Analytics</strong>
          {connection.property_name ? <p className="muted small">{connection.property_name}</p> : null}
        </div>

        {!connection.configured ? (
          <span className="status">OAuth setup required</span>
        ) : connection.status === "disconnected" ? (
          <button className="button compact" type="button" onClick={connect}>Connect</button>
        ) : connection.status === "property_required" ? (
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

      {connection.status === "property_required" ? (
        <div className="provider-setup">
          {properties.length > 0 ? (
            <>
              <select
                className="input"
                value={selectedProperty}
                onChange={(event) => setSelectedProperty(event.target.value)}
              >
                {properties.map((property) => (
                  <option key={property.property_id} value={property.property_id}>
                    {property.property_name} — {property.account_name}
                  </option>
                ))}
              </select>
              <button className="button compact" type="button" disabled={busy} onClick={() => void chooseProperty()}>
                Use property
              </button>
            </>
          ) : (
            <p className="muted small">No accessible GA4 properties were found for this Google account.</p>
          )}
        </div>
      ) : null}

      {snapshot ? (
        <div className="metric-strip">
          <div><span className="metric-value">{snapshot.metrics.active_users ?? 0}</span><span className="metric-label">Active users</span></div>
          <div><span className="metric-value">{snapshot.metrics.sessions ?? 0}</span><span className="metric-label">Sessions</span></div>
          <div><span className="metric-value">{snapshot.metrics.views ?? 0}</span><span className="metric-label">Views</span></div>
          <div><span className="metric-value">{snapshot.metrics.engaged_sessions ?? 0}</span><span className="metric-label">Engaged sessions</span></div>
        </div>
      ) : null}

      {connection.last_error ? <p className="provider-error">{connection.last_error}</p> : null}
      {error ? <p className="provider-error">{error}</p> : null}
    </div>
  );
}
