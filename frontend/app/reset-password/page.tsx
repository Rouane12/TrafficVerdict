"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { PublicFooter } from "../../components/public-footer";
import { api } from "../../lib/api";

type MessageResponse = { message: string };

export default function ResetPasswordPage() {
  const [token, setToken] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setToken(new URLSearchParams(window.location.search).get("token") ?? "");
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (!token) {
      setError("This reset link is missing its token. Request a new password reset email.");
      return;
    }

    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") ?? "");
    const confirmation = String(form.get("confirmation") ?? "");
    if (password !== confirmation) {
      setError("The passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      const result = await api<MessageResponse>("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, password }),
      });
      setMessage(result.message);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to reset your password");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-shell shell">
      <Link className="brand" href="/">TrafficVerdict</Link>
      <section className="panel auth-panel">
        <span className="eyebrow">Choose a new password</span>
        <h1 className="auth-title">Almost there</h1>
        <p className="muted">Use at least 8 characters. This reset link can only be used once.</p>

        {message ? (
          <div className="stack">
            <p className="form-success">{message}</p>
            <Link className="button" href="/login">Sign in</Link>
          </div>
        ) : (
          <form className="stack" onSubmit={handleSubmit}>
            <label className="field">
              <span>New password</span>
              <input className="input" name="password" type="password" autoComplete="new-password" minLength={8} maxLength={128} required />
            </label>
            <label className="field">
              <span>Repeat new password</span>
              <input className="input" name="confirmation" type="password" autoComplete="new-password" minLength={8} maxLength={128} required />
            </label>
            {error ? <p className="form-error">{error}</p> : null}
            <button className="button" type="submit" disabled={submitting || !token}>
              {submitting ? "Updating…" : "Update password"}
            </button>
          </form>
        )}
      </section>
      <PublicFooter />
    </main>
  );
}
