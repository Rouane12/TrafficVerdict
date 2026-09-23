import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Reset password",
  robots: { index: false, follow: false, nocache: true },
};

export default function ResetPasswordLayout({ children }: Readonly<{ children: ReactNode }>) {
  return children;
}
