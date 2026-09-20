import Link from "next/link";

export function PublicFooter() {
  return (
    <footer className="public-footer">
      <div>
        <Link className="brand" href="/">TrafficVerdict</Link>
        <p className="muted small">Clear answers when your analytics disagree.</p>
      </div>
      <nav className="public-footer-links" aria-label="Helpful links">
        <Link href="/guide">Guide</Link>
        <Link href="/privacy">Privacy</Link>
        <Link href="/terms">Terms</Link>
      </nav>
    </footer>
  );
}
