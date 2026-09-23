"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { PublicFooter } from "../../components/public-footer";
import { api } from "../../lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    const form = new FormData(event.currentTarget);

    try {
      await api("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          display_name: form.get("displayName"),
          email: form.get("email"),
          password: form.get("password"),
        }),
      });
      router.replace("/dashboard");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to create account");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-shell shell">
      <Link className="brand" href="/">TrafficVerdict</Link>
      <section className="panel auth-panel">
        <span className="eyebrow">Start reconciling</span>
        <h1 className="auth-title">Create your account</h1>
        <p className="muted">Set up the account first. Your workspace and site come next.</p>

        <form className="stack" onSubmit={handleSubmit}>
          <label className="field">
            <span>Name</span>
            <input className="input" name="displayName" type="text" autoComplete="name" maxLength={120} />
          </label>
          <label className="field">
            <span>Email</span>
            <input className="input" name="email" type="email" autoComplete="email" required />
          </label>
          <label className="field">
            <span>Password</span>
            <input className="input" name="password" type="password" autoComplete="new-password" minLength={8} maxLength={128} required />
          </label>
          {error ? <p className="form-error">{error}</p> : null}
          <button className="button" type="submit" disabled={submitting}>
            {submitting ? "Creating account…" : "Create account"}
          </button>
          <p className="muted tiny legal-note">
            By creating an account, you agree to the <Link className="text-link" href="/terms">Terms</Link> and acknowledge the <Link className="text-link" href="/privacy">Privacy Policy</Link>.
          </p>
        </form>

        <p className="muted small">Already have an account? <Link className="text-link" href="/login">Sign in</Link>.</p>
      </section>
      <PublicFooter />
    </main>
  );
}
