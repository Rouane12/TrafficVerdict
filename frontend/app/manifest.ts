import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "TrafficVerdict",
    short_name: "TrafficVerdict",
    description:
      "Understand why Google Analytics, Search Console, and Cloudflare traffic numbers disagree.",
    start_url: "/",
    display: "standalone",
    background_color: "#080d12",
    theme_color: "#080d12",
    icons: [
      {
        src: "/icon.svg",
        sizes: "any",
        type: "image/svg+xml",
      },
    ],
  };
}
