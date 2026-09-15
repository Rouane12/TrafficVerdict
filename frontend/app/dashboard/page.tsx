"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "../../lib/api";

type User = { id: string; email: string; display_name: string | null };
type Workspace = { id: string; name: string; slug: string };
type Site = { id: string; workspace_id: string; name: string; domain: string; timezone: string };

const providers = ["Google Analytics", "Search Console", "Cloudflare"] as const;

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState("");
  const [sites, setSites] = useState<Site[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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
    const form = event.currentTarget;
    const data = new FormData(form);

    try {
      const site = await api<Site>(`/workspaces/${selectedWorkspaceId}/sites`, {
        method: "POST",
        body: JSON.stringify({
          name: data.get("name"),
          domain: data.get("domain"),
          timezone: data.get("timezone") || "UTC",
        }),
      });
      setSites((current) => [...current, site]);
      form.reset();
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

  if (loading) {
    return <main className="shell dashboard"><p className="muted">Loading your workspace…</p></main>;
  }

  const selectedWorkspace = workspaces.find((workspace) => workspace.id === selectedWorkspaceId);

  return (
    <main className="shell dashboard">
      <header className="dashboard-nav">
        <div>
          <div className="brand">TrafficVerdict</div>
          <p className="muted small">{user?.display_name || user?.email}</p>
        </div>
        <button className="button ghost" type="button" onClick={logout}>Sign out</button>
      </header>

      <section className="dashboard-header">
        <div>
          <span className="eyebrow">Workspace</span>
          <h1 className="dashboard-title">{selectedWorkspace?.name ?? "Create your first workspace"}</h1>
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
          <section className="panel onboarding-panel">
            <span className="eyebrow">Site setup</span>
            <h2>{sites.length === 0 ? "Add your first site" : "Add another site"}</h2>
            <form className="site-form" onSubmit={createSite}>
              <input className="input" name="name" placeholder="Neural Critic" maxLength={120} required />
              <input className="input" name="domain" placeholder="example.com" maxLength={255} required />
              <input className="input" name="timezone" placeholder="UTC" defaultValue="UTC" maxLength={64} required />
              <button className="button" type="submit">Add site</button>
            </form>
          </section>

          <section className="section-block">
            <div className="section-heading">
              <div>
                <span className="eyebrow">Sites</span>
                <h2>{sites.length ? "Your analytics workspaces" : "No sites yet"}</h2>
              </div>
            </div>

            <div className="site-list">
              {sites.map((site) => (
                <article className="site-card" key={site.id}>
                  <div className="site-card-heading">
                    <div>
                      <h2>{site.name}</h2>
                      <p className="muted">{site.domain} · {site.timezone}</p>
                    </div>
                    <span className="status">Foundation ready</span>
                  </div>
                  <div className="provider-grid">
                    {providers.map((provider) => (
                      <div className="provider-row" key={provider}>
                        <span>{provider}</span>
                        <span className="muted">Not connected</span>
                      </div>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  );
}
