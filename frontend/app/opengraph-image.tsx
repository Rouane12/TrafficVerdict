import { ImageResponse } from "next/og";

export const alt = "TrafficVerdict — Understand why your website analytics disagree";
export const size = {
  width: 1200,
  height: 630,
};
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px",
          background: "#080d12",
          color: "#f5f7fb",
          fontFamily: "Arial, sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "18px", fontSize: 30, fontWeight: 700 }}>
          <div
            style={{
              width: 54,
              height: 54,
              borderRadius: 14,
              border: "2px solid #8ee7be",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#8ee7be",
              fontSize: 28,
              fontWeight: 800,
            }}
          >
            ✓
          </div>
          TrafficVerdict
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "24px", maxWidth: 960 }}>
          <div style={{ color: "#8ee7be", fontSize: 24, fontWeight: 700, textTransform: "uppercase", letterSpacing: 2 }}>
            Analytics reconciliation
          </div>
          <div style={{ fontSize: 72, lineHeight: 1.04, fontWeight: 800, letterSpacing: -3 }}>
            Your analytics disagree. Find out why.
          </div>
          <div style={{ fontSize: 30, lineHeight: 1.35, color: "#aebdca" }}>
            GA4 + Search Console + Cloudflare, explained in one verdict.
          </div>
        </div>

        <div style={{ fontSize: 22, color: "#7f91a0" }}>trafficverdict.app</div>
      </div>
    ),
    size,
  );
}
