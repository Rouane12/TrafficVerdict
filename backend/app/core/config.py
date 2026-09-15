from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TrafficVerdict API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://trafficverdict:trafficverdict_dev@localhost:55432/trafficverdict"
    frontend_origin: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
