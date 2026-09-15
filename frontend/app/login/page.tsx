"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "../../lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    const form = new FormData(event.currentTarget);

    try {
      await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: form.get("email"),
          password: form.get("password"),
        }),
      });
      router.replace("/dashboard");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to sign in");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-shell shell">
      <Link className="brand" href="/">TrafficVerdict</Link>
      <section className="panel auth-panel">
        <span className="eyebrow">Welcome back</span>
        <h1 className="auth-title">Sign in</h1>
        <p className="muted">Continue to your analytics reconciliation workspace.</p>

        <form className="stack" onSubmit={handleSubmit}>
          <label className="field">
            <span>Email</span>
            <input className="input" name="email" type="email" autoComplete="email" required />
          </label>
          <label className="field">
            <span>Password</span>
            <input className="input" name="password" type="password" autoComplete="current-password" minLength={8} required />
          </label>
          {error ? <p className="form-error">{error}</p> : null}
          <button className="button" type="submit" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="muted small">New to TrafficVerdict? <Link className="text-link" href="/register">Create an account</Link>.</p>
      </section>
    </main>
  );
}
