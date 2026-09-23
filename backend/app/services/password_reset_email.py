from __future__ import annotations

from urllib.parse import urlencode

import httpx

from app.core.config import settings


class PasswordResetEmailError(RuntimeError):
    pass


def password_reset_email_configured() -> bool:
    return bool(settings.brevo_api_key and settings.password_reset_from_email)


async def send_password_reset_email(email: str, token: str) -> None:
    if not password_reset_email_configured():
        raise PasswordResetEmailError("Password reset email delivery is not configured")

    reset_url = f"{settings.frontend_origin.rstrip('/')}/reset-password?{urlencode({'token': token})}"
    subject = "Reset your TrafficVerdict password"
    html = (
        "<div style=\"font-family:Arial,sans-serif;line-height:1.6;color:#111827\">"
        "<h2>Reset your TrafficVerdict password</h2>"
        "<p>We received a request to reset your password.</p>"
        f"<p><a href=\"{reset_url}\">Choose a new password</a></p>"
        f"<p>This link expires in {settings.password_reset_ttl_minutes} minutes and can be used once.</p>"
        "<p>If you did not request this, you can ignore this email.</p>"
        "</div>"
    )

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": settings.brevo_api_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={
                "sender": {
                    "name": settings.password_reset_from_name,
                    "email": settings.password_reset_from_email,
                },
                "to": [{"email": email}],
                "subject": subject,
                "htmlContent": html,
            },
        )

    if not response.is_success:
        raise PasswordResetEmailError(
            f"Password reset email provider returned status {response.status_code}"
        )
