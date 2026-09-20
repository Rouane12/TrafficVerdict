import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Forgot password",
  robots: { index: false, follow: false, nocache: true },
};

export default function ForgotPasswordLayout({ children }: Readonly<{ children: ReactNode }>) {
  return children;
}
