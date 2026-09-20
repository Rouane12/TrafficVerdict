import type { MetadataRoute } from "next";

const baseUrl = "https://trafficverdict.app";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: `${baseUrl}/`,
      lastModified: "2026-09-20",
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: `${baseUrl}/guide/`,
      lastModified: "2026-09-20",
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      url: `${baseUrl}/privacy/`,
      lastModified: "2026-09-20",
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: `${baseUrl}/terms/`,
      lastModified: "2026-09-20",
      changeFrequency: "yearly",
      priority: 0.3,
    },
  ];
}
