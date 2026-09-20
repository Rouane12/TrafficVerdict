import type { Metadata } from "next";
import Link from "next/link";

import { PublicFooter } from "../../components/public-footer";

export const metadata: Metadata = {
  title: "How TrafficVerdict Works",
  description: "A beginner-friendly guide to connecting analytics sources and reading your traffic verdict.",
};

export default function GuidePage() {
  return (
    <main className="shell public-document">
      <header className="topbar">
        <Link className="brand" href="/">TrafficVerdict</Link>
        <nav className="topbar-actions">
          <Link href="/login">Sign in</Link>
          <Link className="button compact" href="/register">Create account</Link>
        </nav>
      </header>

      <article className="document-body">
        <span className="eyebrow">Beginner guide</span>
        <h1>Understand your traffic without learning three analytics platforms.</h1>
        <p className="document-lede">
          TrafficVerdict compares the analytics sources you already use and explains what their differences mean,
          whether anything appears wrong, and what—if anything—you should check next.
        </p>

        <section>
          <h2>The four-step workflow</h2>
          <div className="guide-grid">
            <div><strong>1. Add your site</strong><p>Name the site, enter its domain, and choose the timezone you normally use.</p></div>
            <div><strong>2. Connect sources</strong><p>Connect Google Analytics, Search Console, and Cloudflare from Tracking health.</p></div>
            <div><strong>3. Sync the evidence</strong><p>TrafficVerdict pulls a recent usable window from each connected source.</p></div>
            <div><strong>4. Read the verdict</strong><p>Overview gives the conclusion first. Reconciliation shows the evidence only when you want it.</p></div>
          </div>
        </section>

        <section>
          <h2>What the three sources actually measure</h2>
          <div className="guide-source-list">
            <div><strong>Google Analytics (GA4)</strong><p>Browser and app activity such as active users, sessions, page views, and engagement.</p></div>
            <div><strong>Google Search Console</strong><p>What happened in Google Search: impressions, clicks, click-through rate, and search position.</p></div>
            <div><strong>Cloudflare</strong><p>Traffic reaching Cloudflare's network, including visits, HTTP requests, and transferred data.</p></div>
          </div>
          <p className="callout">
            These systems do not count the same thing. A Cloudflare visit is not the same metric as a GA4 active user,
            and a Search Console click only describes traffic from Google Search. TrafficVerdict does not force those totals to match.
          </p>
        </section>

        <section>
          <h2>How to read a verdict</h2>
          <p><strong>Start with the headline.</strong> It tells you whether the differences are explainable or whether TrafficVerdict found something that deserves attention.</p>
          <p><strong>Read “What should I do?” next.</strong> If no action is needed, the product should say so. If something needs checking, it gives the next practical step.</p>
          <p><strong>Open evidence only when you want detail.</strong> Rule IDs and raw metadata are supporting material, not homework.</p>
        </section>

        <section>
          <h2>What TrafficVerdict can and cannot tell you</h2>
          <p>
            TrafficVerdict can tell you how to interpret the connected measurements, whether their relationship looks reasonable,
            whether data is stale or incomplete, and where the evidence suggests a tracking problem.
          </p>
          <p>
            It cannot promise one exact universal count of “real humans.” The connected platforms use different collection methods,
            definitions, privacy rules, filtering, time boundaries, and processing delays.
          </p>
        </section>

        <section className="document-cta">
          <h2>Ready to check your site?</h2>
          <p className="muted">Connect your sources and let the verdict be the first thing you read.</p>
          <Link className="button" href="/register">Create account</Link>
        </section>
      </article>

      <PublicFooter />
    </main>
  );
}
