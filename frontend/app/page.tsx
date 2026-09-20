import Link from "next/link";

import { PublicFooter } from "../components/public-footer";

export default function HomePage() {
  return (
    <main className="shell">
      <header className="topbar">
        <Link className="brand" href="/">TrafficVerdict</Link>
        <nav className="topbar-actions">
          <Link href="/guide">How it works</Link>
          <Link href="/login">Sign in</Link>
          <Link className="button compact" href="/register">Create account</Link>
        </nav>
      </header>

      <section className="hero">
        <span className="eyebrow">Analytics reconciliation</span>
        <h1>Your analytics disagree. Find out why.</h1>
        <p>
          Connect the analytics you already use. TrafficVerdict explains what the numbers mean,
          why they differ, whether anything looks wrong, and what you should check next.
        </p>
        <div className="actions">
          <Link className="button" href="/register">Start with your site</Link>
          <Link className="button ghost" href="/guide">See how it works</Link>
        </div>
      </section>

      <section className="home-explainer" aria-labelledby="home-explainer-title">
        <span className="eyebrow">The point</span>
        <h2 id="home-explainer-title">You should not need to become an analytics expert.</h2>
        <div className="home-explainer-grid">
          <div><strong>1. Connect</strong><p className="muted">Add your site and connect GA4, Search Console, and Cloudflare.</p></div>
          <div><strong>2. Sync</strong><p className="muted">TrafficVerdict lines up the usable evidence without pretending unlike metrics are equal.</p></div>
          <div><strong>3. Read the verdict</strong><p className="muted">See what your traffic data actually tells you and whether you need to act.</p></div>
        </div>
      </section>

      <PublicFooter />
    </main>
  );
}
