from __future__ import annotations

from uuid import UUID

import app.models  # noqa: F401
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.routes.auth as auth_routes
from app.core.security import hash_password, verify_password
from app.db.database import Base, get_db
from app.main import app
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User


def _context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    user_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    with Session() as db:
        db.add(
            User(
                id=user_id,
                email="owner@example.com",
                display_name="Owner",
                password_hash=hash_password("old-password"),
            )
        )
        db.commit()

    def override_db():
        with Session() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    return Session, user_id, TestClient(app)


def test_forgot_password_is_generic_and_stores_only_hash(monkeypatch) -> None:
    Session, user_id, client = _context()
    delivered: dict[str, str] = {}

    async def fake_send(email: str, token: str) -> None:
        delivered["email"] = email
        delivered["token"] = token

    monkeypatch.setattr(auth_routes, "send_password_reset_email", fake_send)
    monkeypatch.setattr(auth_routes, "password_reset_email_configured", lambda: True)

    try:
        response = client.post("/api/auth/forgot-password", json={"email": "owner@example.com"})
        assert response.status_code == 202
        assert "If an account exists" in response.json()["message"]
        assert delivered["email"] == "owner@example.com"

        with Session() as db:
            stored = db.scalar(select(PasswordResetToken).where(PasswordResetToken.user_id == user_id))
            assert stored is not None
            assert delivered["token"] not in stored.token_hash
            assert len(stored.token_hash) == 64

        missing = client.post("/api/auth/forgot-password", json={"email": "missing@example.com"})
        assert missing.status_code == 202
        assert missing.json()["message"] == response.json()["message"]
    finally:
        app.dependency_overrides.clear()


def test_reset_password_is_one_time(monkeypatch) -> None:
    Session, user_id, client = _context()
    delivered: dict[str, str] = {}

    async def fake_send(_email: str, token: str) -> None:
        delivered["token"] = token

    monkeypatch.setattr(auth_routes, "send_password_reset_email", fake_send)
    monkeypatch.setattr(auth_routes, "password_reset_email_configured", lambda: True)

    try:
        forgot = client.post("/api/auth/forgot-password", json={"email": "owner@example.com"})
        assert forgot.status_code == 202

        reset = client.post(
            "/api/auth/reset-password",
            json={"token": delivered["token"], "password": "new-password"},
        )
        assert reset.status_code == 200

        with Session() as db:
            user = db.get(User, user_id)
            assert user is not None
            assert verify_password("new-password", user.password_hash)
            assert not verify_password("old-password", user.password_hash)
            stored = db.scalar(select(PasswordResetToken).where(PasswordResetToken.user_id == user_id))
            assert stored is not None
            assert stored.used_at is not None

        reused = client.post(
            "/api/auth/reset-password",
            json={"token": delivered["token"], "password": "another-password"},
        )
        assert reused.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_login_does_not_depend_on_password_reset_email(monkeypatch) -> None:
    _Session, _user_id, client = _context()
    monkeypatch.setattr(auth_routes, "password_reset_email_configured", lambda: False)

    try:
        response = client.post(
            "/api/auth/login",
            json={"email": "owner@example.com", "password": "old-password"},
        )
        assert response.status_code == 200
        assert response.json()["email"] == "owner@example.com"
    finally:
        app.dependency_overrides.clear()


def test_forgot_password_reports_unavailable_when_email_delivery_is_not_configured(monkeypatch) -> None:
    _Session, _user_id, client = _context()
    monkeypatch.setattr(auth_routes, "password_reset_email_configured", lambda: False)

    try:
        response = client.post("/api/auth/forgot-password", json={"email": "owner@example.com"})
        assert response.status_code == 503
        assert response.json()["detail"] == "Password reset email is temporarily unavailable"
    finally:
        app.dependency_overrides.clear()
