import pytest

from app.core.config import Settings
from app.core.runtime_safety import validate_runtime_settings


def _production_settings(**overrides) -> Settings:
    values = {
        "environment": "production",
        "frontend_origin": "https://trafficverdict.example",
        "auth_secret": "a" * 48,
        "credential_encryption_secret": "b" * 48,
        "sync_trigger_secret": "c" * 48,
        "cookie_secure": True,
        "google_client_id": "production-client-id",
        "google_client_secret": "production-client-secret",
        "google_redirect_uri": "https://api.trafficverdict.example/api/integrations/google/callback",
        "google_search_console_redirect_uri": "https://api.trafficverdict.example/api/integrations/search-console/callback",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_safe_production_settings_pass() -> None:
    validate_runtime_settings(_production_settings())


def test_production_can_boot_before_google_oauth_is_configured() -> None:
    validate_runtime_settings(
        _production_settings(
            google_client_id="",
            google_client_secret="",
            google_redirect_uri="http://localhost:8000/api/integrations/google/callback",
            google_search_console_redirect_uri="http://localhost:8000/api/integrations/search-console/callback",
        )
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("auth_secret", "trafficverdict-local-dev-secret-change-before-production", "AUTH_SECRET"),
        ("credential_encryption_secret", "replace-this-with-a-different-long-random-secret", "CREDENTIAL_ENCRYPTION_SECRET"),
        ("sync_trigger_secret", "short", "SYNC_TRIGGER_SECRET"),
        ("cookie_secure", False, "COOKIE_SECURE"),
        ("frontend_origin", "http://trafficverdict.example", "FRONTEND_ORIGIN"),
        ("google_redirect_uri", "http://api.example/callback", "GOOGLE_REDIRECT_URI"),
        (
            "google_search_console_redirect_uri",
            "http://api.example/search-console/callback",
            "GOOGLE_SEARCH_CONSOLE_REDIRECT_URI",
        ),
    ],
)
def test_unsafe_production_settings_fail(field: str, value: object, message: str) -> None:
    with pytest.raises(RuntimeError, match=message):
        validate_runtime_settings(_production_settings(**{field: value}))


def test_production_secrets_must_be_distinct() -> None:
    secret = "c" * 48
    with pytest.raises(RuntimeError, match="must be different"):
        validate_runtime_settings(
            _production_settings(
                auth_secret=secret,
                credential_encryption_secret=secret,
            )
        )
