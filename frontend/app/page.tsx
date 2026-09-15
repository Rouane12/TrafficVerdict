import Link from "next/link";

export default function HomePage() {
  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">TrafficVerdict</div>
        <Link href="/dashboard">Dashboard</Link>
      </header>

      <section className="hero">
        <span className="eyebrow">Analytics reconciliation</span>
        <h1>Your analytics disagree. Find out why.</h1>
        <p>
          TrafficVerdict compares the signals you already have, explains meaningful gaps,
          and shows the evidence behind each conclusion without pretending unlike metrics
          should match.
        </p>
        <Link className="button" href="/dashboard">
          Open dashboard shell
        </Link>
      </section>
    </main>
  );
}
