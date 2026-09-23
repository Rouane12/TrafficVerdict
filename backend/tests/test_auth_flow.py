from __future__ import annotations

import app.models  # noqa: F401
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import security
from app.core.config import settings
from app.db.database import Base, get_db
from app.main import app
from app.models.user import User


def _context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    def override_db():
        with Session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    return Session, TestClient(app)


def test_register_session_logout_and_sign_back_in(monkeypatch) -> None:
    Session, client = _context()
    monkeypatch.setattr(settings, "cookie_secure", False)
    monkeypatch.setattr(settings, "auth_secret", "test-auth-secret-that-is-long-enough-for-session-signing")
    monkeypatch.setattr(security.settings, "auth_secret", "test-auth-secret-that-is-long-enough-for-session-signing")

    try:
        registered = client.post(
            "/api/auth/register",
            json={
                "email": "  Owner@Example.com ",
                "password": "correct-password",
                "display_name": "Owner",
            },
        )
        assert registered.status_code == 201
        assert registered.json()["email"] == "owner@example.com"
        assert settings.session_cookie_name in client.cookies

        with Session() as db:
            user = db.scalar(select(User).where(User.email == "owner@example.com"))
            assert user is not None
            assert user.password_hash is not None
            assert user.password_hash != "correct-password"
            assert security.verify_password("correct-password", user.password_hash)

        me = client.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == "owner@example.com"

        duplicate = client.post(
            "/api/auth/register",
            json={"email": "OWNER@example.com", "password": "another-password"},
        )
        assert duplicate.status_code == 409

        logged_out = client.post("/api/auth/logout")
        assert logged_out.status_code == 204
        assert settings.session_cookie_name not in client.cookies

        after_logout = client.get("/api/auth/me")
        assert after_logout.status_code == 401

        wrong_password = client.post(
            "/api/auth/login",
            json={"email": "owner@example.com", "password": "wrong-password"},
        )
        assert wrong_password.status_code == 401
        assert settings.session_cookie_name not in client.cookies

        signed_in = client.post(
            "/api/auth/login",
            json={"email": "OWNER@example.com", "password": "correct-password"},
        )
        assert signed_in.status_code == 200
        assert signed_in.json()["email"] == "owner@example.com"
        assert settings.session_cookie_name in client.cookies

        restored = client.get("/api/auth/me")
        assert restored.status_code == 200
        assert restored.json()["display_name"] == "Owner"
    finally:
        app.dependency_overrides.clear()


def test_invalid_or_missing_session_cannot_access_account(monkeypatch) -> None:
    _Session, client = _context()
    monkeypatch.setattr(settings, "cookie_secure", False)
    monkeypatch.setattr(settings, "auth_secret", "test-auth-secret-that-is-long-enough-for-session-signing")
    monkeypatch.setattr(security.settings, "auth_secret", "test-auth-secret-that-is-long-enough-for-session-signing")

    try:
        missing = client.get("/api/auth/me")
        assert missing.status_code == 401

        client.cookies.set(settings.session_cookie_name, "not-a-valid-jwt")
        invalid = client.get("/api/auth/me")
        assert invalid.status_code == 401
    finally:
        app.dependency_overrides.clear()
