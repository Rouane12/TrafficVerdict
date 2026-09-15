import Link from "next/link";

export default function HomePage() {
  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">TrafficVerdict</div>
        <nav className="topbar-actions">
          <Link href="/login">Sign in</Link>
          <Link className="button compact" href="/register">Create account</Link>
        </nav>
      </header>

      <section className="hero">
        <span className="eyebrow">Analytics reconciliation</span>
        <h1>Your analytics disagree. Find out why.</h1>
        <p>
          TrafficVerdict compares the signals you already have, explains meaningful gaps,
          and shows the evidence behind each conclusion without pretending unlike metrics
          should match.
        </p>
        <div className="actions">
          <Link className="button" href="/register">Start with your site</Link>
          <Link className="button ghost" href="/login">Sign in</Link>
        </div>
      </section>
    </main>
  );
}
