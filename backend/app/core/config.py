from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TrafficVerdict API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://trafficverdict:trafficverdict_dev@localhost:55432/trafficverdict"
    frontend_origin: str = "http://localhost:3000"
    auth_secret: str = "trafficverdict-local-dev-secret-change-before-production"
    session_cookie_name: str = "trafficverdict_session"
    session_ttl_seconds: int = 60 * 60 * 24 * 7
    cookie_secure: bool = False

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/integrations/google/callback"
    google_analytics_scope: str = "https://www.googleapis.com/auth/analytics.readonly"
    google_search_console_redirect_uri: str = "http://localhost:8000/api/integrations/search-console/callback"
    google_search_console_scope: str = "https://www.googleapis.com/auth/webmasters.readonly"
    credential_encryption_secret: str = "trafficverdict-local-credential-key-change-before-production"

    scheduled_sync_interval_hours: int = 24
    sync_worker_poll_seconds: int = 60
    sync_worker_batch_size: int = 10
    sync_job_max_attempts: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
