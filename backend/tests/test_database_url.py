from app.db.database import _sqlalchemy_database_url


def test_plain_postgresql_url_uses_psycopg_driver() -> None:
    value = "postgresql://user:pass@example.neon.tech/neondb?sslmode=require"
    assert _sqlalchemy_database_url(value) == "postgresql+psycopg://user:pass@example.neon.tech/neondb?sslmode=require"


def test_legacy_postgres_url_uses_psycopg_driver() -> None:
    value = "postgres://user:pass@example.test/db"
    assert _sqlalchemy_database_url(value) == "postgresql+psycopg://user:pass@example.test/db"


def test_existing_sqlalchemy_driver_url_is_unchanged() -> None:
    value = "postgresql+psycopg://user:pass@example.test/db"
    assert _sqlalchemy_database_url(value) == value
