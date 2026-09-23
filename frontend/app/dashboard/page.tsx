"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "../../lib/api";
import { SiteExperience } from "./site-experience";

type User = { id: string; email: string; display_name: string | null };
type Workspace = { id: string; name: string; slug: string };
type Site = { id: string; workspace_id: string; name: string; domain: string; timezone: string };

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState("");
  const [sites, setSites] = useState<Site[]>([]);
  const [siteName, setSiteName] = useState("");
  const [siteDomain, setSiteDomain] = useState("");
  const [siteTimezone, setSiteTimezone] = useState("UTC");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [accountError, setAccountError] = useState("");
  const [accountBusy, setAccountBusy] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteConfirmation, setDeleteConfirmation] = useState("");

  async function loadSites(workspaceId: string) {
    const nextSites = await api<Site[]>(`/workspaces/${workspaceId}/sites`);
    setSites(nextSites);
  }

  useEffect(() => {
    async function boot() {
      try {
        const currentUser = await api<User>("/auth/me");
        const nextWorkspaces = await api<Workspace[]>("/workspaces");
        setUser(currentUser);
        setWorkspaces(nextWorkspaces);
        if (nextWorkspaces.length > 0) {
          setSelectedWorkspaceId(nextWorkspaces[0].id);
          await loadSites(nextWorkspaces[0].id);
        }
      } catch {
        router.replace("/login");
      } finally {
        setLoading(false);
      }
    }

    void boot();
  }, [router]);

  async function createWorkspace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const form = event.currentTarget;
    const data = new FormData(form);

    try {
      const workspace = await api<Workspace>("/workspaces", {
        method: "POST",
        body: JSON.stringify({ name: data.get("name") }),
      });
      setWorkspaces((current) => [...current, workspace]);
      setSelectedWorkspaceId(workspace.id);
      setSites([]);
      form.reset();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to create workspace");
    }
  }

  async function createSite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedWorkspaceId) return;
    setError("");

    try {
      const site = await api<Site>(`/workspaces/${selectedWorkspaceId}/sites`, {
        method: "POST",
        body: JSON.stringify({
          name: siteName,
          domain: siteDomain,
          timezone: siteTimezone || "UTC",
        }),
      });
      setSites((current) => [...current, site]);
      setSiteName("");
      setSiteDomain("");
      setSiteTimezone("UTC");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to add site");
    }
  }

  async function changeWorkspace(workspaceId: string) {
    setSelectedWorkspaceId(workspaceId);
    setError("");
    try {
      await loadSites(workspaceId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load sites");
    }
  }

  async function logout() {
    await api<void>("/auth/logout", { method: "POST" });
    router.replace("/login");
  }

  async function downloadAccountData() {
    setAccountBusy(true);
    setAccountError("");
    try {
      const data = await api<Record<string, unknown>>("/auth/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `trafficverdict-data-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setAccountError(caught instanceof Error ? caught.message : "Unable to export account data");
    } finally {
      setAccountBusy(false);
    }
  }

  async function deleteAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (deleteConfirmation !== "DELETE") return;
    if (!window.confirm("Permanently delete your TrafficVerdict account and owned site data? This cannot be undone.")) {
      return;
    }

    setAccountBusy(true);
    setAccountError("");
    try {
      await api<void>("/auth/account", {
        method: "DELETE",
        body: JSON.stringify({
          current_password: deletePassword,
          confirmation: deleteConfirmation,
        }),
      });
      router.replace("/");
    } catch (caught) {
      setAccountError(caught instanceof Error ? caught.message : "Unable to delete account");
    } finally {
      setAccountBusy(false);
    }
  }

  if (loading) {
    return (
      <main className="shell dashboard">
        <div className="dashboard-loading" role="status">
          <span className="eyebrow">TrafficVerdict</span>
          <h2>Loading your workspace…</h2>
          <p className="muted">Restoring your sites and the latest evidence-backed verdicts.</p>
        </div>
      </main>
    );
  }

  const selectedWorkspace = workspaces.find((workspace) => workspace.id === selectedWorkspaceId);

  return (
    <main className="shell dashboard">
      <header className="dashboard-nav">
        <div>
          <div className="brand">TrafficVerdict</div>
          <p className="muted small">{user?.display_name || user?.email}</p>
        </div>
        <div className="dashboard-nav-actions">
          <Link className="button ghost" href="/guide">Guide</Link>
          <button className="button ghost" type="button" onClick={logout}>Sign out</button>
        </div>
      </header>

      <section className="dashboard-header experience-dashboard-header">
        <div>
          <span className="eyebrow">Workspace</span>
          <h1 className="dashboard-title">{selectedWorkspace?.name ?? "Create your first workspace"}</h1>
          {selectedWorkspace ? <p className="muted experience-subtitle">Start with the verdict. Drill into sources only when you need the evidence.</p> : null}
        </div>
        {workspaces.length > 1 ? (
          <select className="input workspace-select" value={selectedWorkspaceId} onChange={(event) => void changeWorkspace(event.target.value)}>
            {workspaces.map((workspace) => <option key={workspace.id} value={workspace.id}>{workspace.name}</option>)}
          </select>
        ) : null}
      </section>

      {error ? <p className="form-error dashboard-error">{error}</p> : null}

      {workspaces.length === 0 ? (
        <section className="panel onboarding-panel">
          <span className="eyebrow">Step 1 of 2</span>
          <h2>Create a workspace</h2>
          <p className="muted">A workspace groups the sites and analytics connections you manage.</p>
          <form className="inline-form" onSubmit={createWorkspace}>
            <input className="input" name="name" placeholder="My workspace" maxLength={120} required />
            <button className="button" type="submit">Create workspace</button>
          </form>
        </section>
      ) : (
        <>
          <section className="section-block experience-sites-section">
            <div className="section-heading">
              <div>
                <span className="eyebrow">Traffic today</span>
                <h2>{sites.length ? "Your sites" : "No sites yet"}</h2>
              </div>
            </div>

            <div className="site-list">
              {sites.map((site) => <SiteExperience site={site} key={site.id} />)}
            </div>
          </section>

          <details className="panel site-setup-disclosure" open={sites.length === 0}>
            <summary>{sites.length === 0 ? "Add your first site" : "Add another site"}</summary>
            <div className="site-setup-body">
              <span className="eyebrow">Site setup</span>
              <h2>{sites.length === 0 ? "Add your first site" : "Add another site"}</h2>
              <form className="site-form" onSubmit={createSite} autoComplete="off">
                <input
                  className="input"
                  name="name"
                  placeholder="Neural Critic"
                  value={siteName}
                  onChange={(event) => setSiteName(event.target.value)}
                  maxLength={120}
                  autoComplete="off"
                  required
                />
                <input
                  className="input"
                  name="domain"
                  placeholder="example.com"
                  value={siteDomain}
                  onChange={(event) => setSiteDomain(event.target.value)}
                  maxLength={255}
                  autoComplete="off"
                  required
                />
                <input
                  className="input"
                  name="timezone"
                  placeholder="UTC"
                  value={siteTimezone}
                  onChange={(event) => setSiteTimezone(event.target.value)}
                  maxLength={64}
                  autoComplete="off"
                  required
                />
                <button className="button" type="submit">Add site</button>
              </form>
            </div>
          </details>
        </>
      )}

      <details className="panel account-data-disclosure">
        <summary>Account & data</summary>
        <div className="account-data-body">
          <div className="account-data-section">
            <div>
              <span className="eyebrow">Your data</span>
              <h2>Export your TrafficVerdict data</h2>
              <p className="muted small">
                Download the account, site, connection metadata, synced metrics, and job history currently stored for your accessible workspaces. Provider credentials are never included.
              </p>
            </div>
            <button className="button ghost" type="button" disabled={accountBusy} onClick={() => void downloadAccountData()}>
              {accountBusy ? "Working…" : "Download data"}
            </button>
          </div>

          <div className="account-danger-zone">
            <span className="eyebrow">Danger zone</span>
            <h2>Delete account</h2>
            <p className="muted small">
              This permanently deletes your account and workspaces you solely own, including their sites, connections, snapshots, and sync history.
            </p>
            <form className="account-delete-form" onSubmit={deleteAccount}>
              <input
                className="input"
                type="password"
                placeholder="Current password"
                value={deletePassword}
                onChange={(event) => setDeletePassword(event.target.value)}
                minLength={8}
                maxLength={128}
                autoComplete="current-password"
                required
              />
              <input
                className="input"
                type="text"
                placeholder='Type DELETE'
                value={deleteConfirmation}
                onChange={(event) => setDeleteConfirmation(event.target.value)}
                pattern="DELETE"
                autoComplete="off"
                required
              />
              <button className="button danger-button" type="submit" disabled={accountBusy || deleteConfirmation !== "DELETE"}>
                Permanently delete account
              </button>
            </form>
          </div>

          {accountError ? <p className="form-error">{accountError}</p> : null}
        </div>
      </details>

      <nav className="dashboard-legal-links" aria-label="TrafficVerdict policies">
        <Link href="/guide">Guide</Link>
        <Link href="/privacy">Privacy</Link>
        <Link href="/terms">Terms</Link>
      </nav>
    </main>
  );
}
