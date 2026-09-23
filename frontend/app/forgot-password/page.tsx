"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { PublicFooter } from "../../components/public-footer";
import { api } from "../../lib/api";

type MessageResponse = { message: string };

export default function ForgotPasswordPage() {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setSubmitting(true);
    const form = new FormData(event.currentTarget);

    try {
      const result = await api<MessageResponse>("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email: form.get("email") }),
      });
      setMessage(result.message);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to request a password reset");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-shell shell">
      <Link className="brand" href="/">TrafficVerdict</Link>
      <section className="panel auth-panel">
        <span className="eyebrow">Account recovery</span>
        <h1 className="auth-title">Reset your password</h1>
        <p className="muted">Enter your account email. If it matches an account, we will send a one-time reset link.</p>

        <form className="stack" onSubmit={handleSubmit}>
          <label className="field">
            <span>Email</span>
            <input className="input" name="email" type="email" autoComplete="email" required />
          </label>
          {message ? <p className="form-success">{message}</p> : null}
          {error ? <p className="form-error">{error}</p> : null}
          <button className="button" type="submit" disabled={submitting}>
            {submitting ? "Sending…" : "Send reset link"}
          </button>
        </form>

        <p className="muted small">Remembered it? <Link className="text-link" href="/login">Back to sign in</Link>.</p>
      </section>
      <PublicFooter />
    </main>
  );
}
