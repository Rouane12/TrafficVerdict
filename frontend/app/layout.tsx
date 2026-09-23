import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

const siteUrl = "https://trafficverdict.app";
const defaultTitle = "TrafficVerdict — Why Your Website Analytics Disagree";
const defaultDescription =
  "TrafficVerdict reconciles Google Analytics, Search Console, and Cloudflare so you can understand why traffic numbers disagree and whether anything needs attention.";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  applicationName: "TrafficVerdict",
  title: {
    default: defaultTitle,
    template: "%s · TrafficVerdict",
  },
  description: defaultDescription,
  keywords: [
    "website analytics",
    "Google Analytics",
    "GA4",
    "Google Search Console",
    "Cloudflare analytics",
    "analytics reconciliation",
    "website traffic",
    "traffic discrepancy",
  ],
  category: "analytics",
  creator: "TrafficVerdict",
  publisher: "TrafficVerdict",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
  openGraph: {
    type: "website",
    siteName: "TrafficVerdict",
    url: siteUrl,
    title: defaultTitle,
    description: defaultDescription,
  },
  twitter: {
    card: "summary_large_image",
    title: defaultTitle,
    description: defaultDescription,
  },
  icons: {
    icon: [{ url: "/icon.svg", type: "image/svg+xml" }],
  },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
