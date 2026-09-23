"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "../lib/api";

type AuthState = "checking" | "signed-in" | "signed-out";

export function PublicAuthActions() {
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
        <Link href="/guide">How it works</Link>
        <Link className="button compact" href="/dashboard">Dashboard</Link>
      </nav>
    );
  }

  return (
    <nav className="topbar-actions" aria-label="Account navigation">
      <Link href="/guide">How it works</Link>
      <Link href="/login">Sign in</Link>
      <Link className="button compact" href="/register">Create account</Link>
    </nav>
  );
}
