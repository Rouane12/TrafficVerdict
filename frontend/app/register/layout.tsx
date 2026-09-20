import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Create account",
  robots: { index: false, follow: false, nocache: true },
};

export default function RegisterLayout({ children }: Readonly<{ children: ReactNode }>) {
  return children;
}
