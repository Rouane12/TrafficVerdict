import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Sign in",
  robots: { index: false, follow: false, nocache: true },
};

export default function LoginLayout({ children }: Readonly<{ children: ReactNode }>) {
  return children;
}
