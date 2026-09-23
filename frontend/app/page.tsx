import type { Metadata } from "next";
import Link from "next/link";

import { PublicAuthActions } from "../components/public-auth-actions";
import { PublicFooter } from "../components/public-footer";

const pageTitle = "TrafficVerdict — Why Your Website Analytics Disagree";
const pageDescription =
  "Compare GA4, Google Search Console, and Cloudflare in one place. TrafficVerdict explains why the numbers differ, whether anything looks wrong, and what to check next.";

export const metadata: Metadata = {
  title: { absolute: pageTitle },
  description: pageDescription,
  alternates: { canonical: "/" },
  openGraph: {
    title: pageTitle,
    description: pageDescription,
    url: "/",
  },
  twitter: {
    title: pageTitle,
    description: pageDescription,
  },
};

const softwareApplicationSchema = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "TrafficVerdict",
  url: "https://trafficverdict.app",
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  description: pageDescription,
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
  },
  featureList: [
    "Google Analytics reconciliation",
    "Google Search Console reconciliation",
    "Cloudflare analytics reconciliation",
    "Evidence-backed traffic explanations",
    "Tracking health checks",
    "Traffic change detection",
  ],
};

const websiteSchema = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "TrafficVerdict",
  url: "https://trafficverdict.app",
  description: pageDescription,
};

export default function HomePage() {
  return (
    <main className="shell">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(softwareApplicationSchema) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteSchema) }}
      />

      <header className="topbar">
        <Link className="brand" href="/">TrafficVerdict</Link>
        <PublicAuthActions />
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

      <section className="seo-questions" aria-labelledby="common-questions-title">
        <span className="eyebrow">Common questions</span>
        <h2 id="common-questions-title">The confusing traffic questions TrafficVerdict is built to answer.</h2>

        <div className="seo-question-grid">
          <article>
            <h3>Why does Cloudflare show more traffic than Google Analytics?</h3>
            <p>
              Cloudflare measures traffic reaching its network, while GA4 depends on browser-side analytics collection.
              Bots, blocked scripts, consent choices, and different definitions can make Cloudflare totals much larger.
              TrafficVerdict compares the evidence without treating those measurements as identical.
            </p>
          </article>
          <article>
            <h3>Why do Search Console clicks not match GA4 sessions?</h3>
            <p>
              Search Console reports activity from Google Search. GA4 reports browser sessions after a visitor reaches
              your site and its analytics code runs. Time zones, attribution, consent, and collection differences mean
              the two numbers are not expected to match exactly.
            </p>
          </article>
          <article>
            <h3>Which website traffic number is the correct one?</h3>
            <p>
              There is no single universal traffic number across every provider. The useful answer depends on the
              question: search visibility, browser engagement, or network traffic. TrafficVerdict tells you which
              measurement fits the question and whether the differences look explainable.
            </p>
          </article>
        </div>

        <Link className="text-link" href="/guide">Read the beginner guide →</Link>
      </section>

      <PublicFooter />
    </main>
  );
}
