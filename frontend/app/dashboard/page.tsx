const providers = [
  ["Google Analytics", "GA4 connection will arrive in Milestone 2"],
  ["Search Console", "Search performance connection will arrive in Milestone 3"],
  ["Cloudflare", "Network analytics connection will arrive in Milestone 4"],
] as const;

export default function DashboardPage() {
  return (
    <main className="shell dashboard">
      <section className="dashboard-header">
        <div>
          <span className="eyebrow">Workspace</span>
          <h1 style={{ fontSize: "clamp(2rem, 5vw, 3.5rem)", marginTop: 8 }}>
            TrafficVerdict
          </h1>
        </div>
        <p>Foundation shell — authentication and site creation are next.</p>
      </section>

      <div className="grid">
        {providers.map(([name, description]) => (
          <article className="card" key={name}>
            <h2>{name}</h2>
            <p>{description}</p>
            <span className="status">Not connected</span>
          </article>
        ))}
      </div>
    </main>
  );
}
