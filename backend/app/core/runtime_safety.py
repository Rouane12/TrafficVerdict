from __future__ import annotations

from urllib.parse import urlparse

from app.core.config import Settings

_INSECURE_MARKERS = (
    "change-before-production",
    "replace-this",
    "local-dev-secret",
    "local-credential-key",
)


def _looks_insecure_secret(value: str) -> bool:
    lowered = value.lower()
    return len(value) < 32 or any(marker in lowered for marker in _INSECURE_MARKERS)


def validate_runtime_settings(config: Settings) -> None:
    environment = config.environment.strip().lower()
    if environment not in {"production", "prod"}:
        return

    errors: list[str] = []

    if _looks_insecure_secret(config.auth_secret):
        errors.append("AUTH_SECRET must be a strong production secret")
    if _looks_insecure_secret(config.credential_encryption_secret):
        errors.append("CREDENTIAL_ENCRYPTION_SECRET must be a strong production secret")
    if config.auth_secret == config.credential_encryption_secret:
        errors.append("AUTH_SECRET and CREDENTIAL_ENCRYPTION_SECRET must be different")
    if not config.cookie_secure:
        errors.append("COOKIE_SECURE must be true in production")

    frontend = urlparse(config.frontend_origin)
    if frontend.scheme != "https":
        errors.append("FRONTEND_ORIGIN must use https in production")

    for label, uri in (
        ("GOOGLE_REDIRECT_URI", config.google_redirect_uri),
        ("GOOGLE_SEARCH_CONSOLE_REDIRECT_URI", config.google_search_console_redirect_uri),
    ):
        if uri and urlparse(uri).scheme != "https":
            errors.append(f"{label} must use https in production")

    if errors:
        joined = "; ".join(errors)
        raise RuntimeError(f"Unsafe production configuration: {joined}")
