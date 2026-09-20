"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "../lib/api";

type AuthState = "checking" | "signed-in" | "signed-out";

export function GuideAuthActions() {
  const [authState, setAuthState] = useState<AuthState>("checking");

  useEffect(() => {
    let active = true;

    api("/auth/me")
      .then(() => {
        if (active) setAuthState("signed-in");
      })
      .catch(() => {
        if (active) setAuthState("signed-out");
      });

    return () => {
      active = false;
    };
  }, []);

  if (authState === "checking") {
    return <nav className="topbar-actions" aria-label="Account navigation" />;
  }

  if (authState === "signed-in") {
    return (
      <nav className="topbar-actions" aria-label="Account navigation">
        <Link className="button compact" href="/dashboard">Back to dashboard</Link>
      </nav>
    );
  }

  return (
    <nav className="topbar-actions" aria-label="Account navigation">
      <Link href="/login">Sign in</Link>
      <Link className="button compact" href="/register">Create account</Link>
    </nav>
  );
}
