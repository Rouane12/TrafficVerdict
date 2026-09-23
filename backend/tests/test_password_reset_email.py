from __future__ import annotations

import asyncio

from app.services import password_reset_email as email_service


class _Response:
    is_success = True
    status_code = 201


class _Client:
    def __init__(self, capture: dict, *args, **kwargs):
        self.capture = capture

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, *, headers, json):
        self.capture["url"] = url
        self.capture["headers"] = headers
        self.capture["json"] = json
        return _Response()


def test_password_reset_email_configured_requires_brevo_and_sender(monkeypatch) -> None:
    monkeypatch.setattr(email_service.settings, "brevo_api_key", "")
    monkeypatch.setattr(email_service.settings, "password_reset_from_email", "")
    assert email_service.password_reset_email_configured() is False

    monkeypatch.setattr(email_service.settings, "brevo_api_key", "test-key")
    monkeypatch.setattr(email_service.settings, "password_reset_from_email", "no-reply@example.com")
    assert email_service.password_reset_email_configured() is True


def test_send_password_reset_email_uses_brevo_transactional_api(monkeypatch) -> None:
    capture: dict = {}

    monkeypatch.setattr(email_service.settings, "brevo_api_key", "test-key")
    monkeypatch.setattr(email_service.settings, "password_reset_from_email", "no-reply@example.com")
    monkeypatch.setattr(email_service.settings, "password_reset_from_name", "TrafficVerdict")
    monkeypatch.setattr(email_service.settings, "frontend_origin", "https://trafficverdict.app")
    monkeypatch.setattr(email_service.settings, "password_reset_ttl_minutes", 30)
    monkeypatch.setattr(
        email_service.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _Client(capture, *args, **kwargs),
    )

    asyncio.run(email_service.send_password_reset_email("user@example.com", "reset-token"))

    assert capture["url"] == "https://api.brevo.com/v3/smtp/email"
    assert capture["headers"]["api-key"] == "test-key"
    assert capture["json"]["sender"] == {
        "name": "TrafficVerdict",
        "email": "no-reply@example.com",
    }
    assert capture["json"]["to"] == [{"email": "user@example.com"}]
    assert capture["json"]["subject"] == "Reset your TrafficVerdict password"
    assert "reset-password?token=reset-token" in capture["json"]["htmlContent"]
