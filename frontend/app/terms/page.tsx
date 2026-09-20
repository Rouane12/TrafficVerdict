import type { Metadata } from "next";
import Link from "next/link";

import { PublicFooter } from "../../components/public-footer";

export const metadata: Metadata = {
  title: "Terms of Service · TrafficVerdict",
  description: "Terms for using TrafficVerdict.",
};

export default function TermsPage() {
  return (
    <main className="shell public-document">
      <header className="topbar">
        <Link className="brand" href="/">TrafficVerdict</Link>
        <nav className="topbar-actions"><Link href="/guide">Guide</Link><Link href="/login">Sign in</Link></nav>
      </header>

      <article className="document-body legal-document">
        <span className="eyebrow">Terms</span>
        <h1>Terms of Service</h1>
        <p className="document-lede">Effective September 20, 2026. These terms apply when you create an account or use TrafficVerdict.</p>

        <section>
          <h2>What TrafficVerdict provides</h2>
          <p>TrafficVerdict is an analytics reconciliation service. It connects to analytics sources you authorize, compares their measurements, and presents explanations, evidence, health information, and suggested next checks.</p>
        </section>

        <section>
          <h2>Analytics are not one universal number</h2>
          <p>Different providers measure different events, users, requests, visits, search activity, time windows, and filtered traffic. TrafficVerdict is designed to explain those differences; it does not guarantee an exact count of unique human visitors or guarantee that different providers will match.</p>
        </section>

        <section>
          <h2>Your account</h2>
          <p>You are responsible for keeping your sign-in information secure and for activity performed through your account. You must provide information you are authorized to use and must not attempt to access another person's workspace, site, credentials, or analytics data.</p>
        </section>

        <section>
          <h2>Authorized connections only</h2>
          <p>You may only connect websites, analytics properties, Cloudflare zones, Google accounts, or other resources that you own or are authorized to manage. You must follow the terms of the third-party services you connect.</p>
        </section>

        <section>
          <h2>Acceptable use</h2>
          <p>Do not use TrafficVerdict to break the law, interfere with the service, probe or bypass security controls, abuse provider APIs, introduce malicious code, or access data without authorization.</p>
        </section>

        <section>
          <h2>Beta availability</h2>
          <p>TrafficVerdict may be offered as a public beta. Features, integrations, limits, and availability may change. Scheduled jobs may be delayed by hosting or provider availability, and third-party APIs may change or become unavailable.</p>
        </section>

        <section>
          <h2>Your data and privacy</h2>
          <p>Your use of TrafficVerdict is also covered by the <Link className="text-link" href="/privacy">Privacy Policy</Link>. You keep ownership of the site and analytics data you are authorized to connect. You grant TrafficVerdict the limited permission needed to process that data to provide the service.</p>
        </section>

        <section>
          <h2>No professional guarantee</h2>
          <p>TrafficVerdict provides analytics interpretation and diagnostic information, not legal, accounting, security-audit, or financial advice. Findings are based on the data and provider semantics available to the service and may be incomplete when sources are missing, delayed, sampled, or differently scoped.</p>
        </section>

        <section>
          <h2>Suspension and termination</h2>
          <p>Access may be limited or suspended when reasonably necessary to protect TrafficVerdict, its users, provider integrations, or legal compliance. You may stop using the service and use the account deletion controls at any time.</p>
        </section>

        <section>
          <h2>Liability and mandatory rights</h2>
          <p>To the extent permitted by applicable law, TrafficVerdict is provided without guarantees of uninterrupted availability or error-free analytics interpretation. Nothing in these terms removes consumer or other rights that cannot legally be waived where you live.</p>
        </section>

        <section>
          <h2>Changes</h2>
          <p>These terms may be updated as the service changes. Material changes will be reflected by updating the effective date and, when appropriate, by providing notice in the product.</p>
        </section>

        <section>
          <h2>Questions</h2>
          <p>For questions about these terms, contact <a className="text-link" href="mailto:support@trafficverdict.app">support@trafficverdict.app</a>.</p>
        </section>
      </article>

      <PublicFooter />
    </main>
  );
}
