import type { Metadata } from "next";
import Link from "next/link";

import { PublicFooter } from "../../components/public-footer";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "How TrafficVerdict handles account, analytics, connection, and synced metric data.",
  alternates: { canonical: "/privacy/" },
  openGraph: {
    title: "Privacy Policy · TrafficVerdict",
    description: "How TrafficVerdict handles account, analytics, connection, and synced metric data.",
    url: "/privacy/",
  },
};

export default function PrivacyPage() {
  return (
    <main className="shell public-document">
      <header className="topbar">
        <Link className="brand" href="/">TrafficVerdict</Link>
        <nav className="topbar-actions"><Link href="/guide">Guide</Link><Link href="/login">Sign in</Link></nav>
      </header>

      <article className="document-body legal-document">
        <span className="eyebrow">Privacy</span>
        <h1>Privacy Policy</h1>
        <p className="document-lede">Effective September 20, 2026. This policy explains the data TrafficVerdict needs to reconcile your analytics and how that data is handled.</p>

        <section>
          <h2>Information we handle</h2>
          <p>TrafficVerdict stores account information such as your email address and optional display name; workspace and site information you enter; connection metadata for analytics providers; synced analytics metrics and diagnostic history; and operational records such as sync status and errors.</p>
          <p>Passwords are stored as one-way password hashes. Provider access or refresh credentials are stored in encrypted form when a connection requires them.</p>
        </section>

        <section>
          <h2>Why we use it</h2>
          <p>We use this information to authenticate your account, connect the analytics services you authorize, sync measurements, normalize them, produce evidence-backed reconciliation findings, maintain account and security features, and operate the service.</p>
        </section>

        <section>
          <h2>Connected providers</h2>
          <p>When you connect Google Analytics, Google Search Console, or Cloudflare, TrafficVerdict requests only the access needed for the features you choose. TrafficVerdict is designed for read-only analytics access and does not use those connections to change your website or analytics configuration.</p>
        </section>

        <section>
          <h2>Service providers</h2>
          <p>TrafficVerdict relies on infrastructure and API providers to operate. These may include Render for application hosting, Neon for PostgreSQL hosting, Google for authorized analytics APIs, Cloudflare for authorized analytics APIs, and an email delivery provider such as Resend for account recovery messages. Those providers process data under their own terms and privacy practices.</p>
        </section>

        <section>
          <h2>Cookies and sessions</h2>
          <p>TrafficVerdict uses an essential secure session cookie to keep you signed in. The core application does not require advertising cookies to reconcile your analytics.</p>
        </section>

        <section>
          <h2>Sharing and selling</h2>
          <p>TrafficVerdict does not currently sell your personal information or connected analytics data, and does not use your connected analytics data for third-party advertising targeting. Data may be disclosed when required by law or when necessary to protect the service, users, or others.</p>
        </section>

        <section>
          <h2>Retention and your controls</h2>
          <p>You can export the account, site, connection metadata, synced metrics, and job history stored for your accessible workspaces from Account &amp; data. You can also delete your account from the dashboard. Deletion removes workspaces you solely own and their stored sites, connections, snapshots, and sync history, subject to limited records that may need to be retained for security or legal reasons.</p>
        </section>

        <section>
          <h2>Security</h2>
          <p>TrafficVerdict uses measures including HTTPS, secure cookies, one-way password hashing, encrypted provider credentials, origin checks for state-changing requests, and least-privilege provider scopes. No internet service can guarantee absolute security.</p>
        </section>

        <section>
          <h2>International use and eligibility</h2>
          <p>TrafficVerdict may process data in countries where its infrastructure providers operate. You should only connect analytics accounts and sites that you are authorized to manage. If the law where you live requires permission from a parent, guardian, organization, or account owner to use the service, you must have that permission.</p>
        </section>

        <section>
          <h2>Changes to this policy</h2>
          <p>We may update this policy as TrafficVerdict changes. The effective date at the top will be updated when material changes are published.</p>
        </section>

        <section>
          <h2>Questions or privacy requests</h2>
          <p>Use the account export and deletion controls for self-service requests. For other privacy questions, contact <a className="text-link" href="mailto:support@trafficverdict.app">support@trafficverdict.app</a>.</p>
        </section>
      </article>

      <PublicFooter />
    </main>
  );
}
