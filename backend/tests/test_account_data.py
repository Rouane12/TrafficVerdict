from __future__ import annotations

from uuid import UUID

import app.models  # noqa: F401
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies.auth import get_current_user
from app.core.security import hash_password
from app.db.database import Base, get_db
from app.main import app
from app.models.connection import Connection
from app.models.site import Site
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember


def _test_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    user_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    workspace_id = UUID("11111111-1111-1111-1111-111111111111")
    site_id = UUID("22222222-2222-2222-2222-222222222222")

    with Session() as db:
        user = User(
            id=user_id,
            email="owner@example.test",
            display_name="Owner",
            password_hash=hash_password("correct-password"),
        )
        workspace = Workspace(id=workspace_id, name="Owner workspace", slug="owner-workspace")
        db.add_all([user, workspace])
        db.flush()
        db.add(WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role="owner"))
        db.add(
            Site(
                id=site_id,
                workspace_id=workspace_id,
                name="Example",
                domain="example.test",
                timezone="UTC",
            )
        )
        db.flush()
        db.add(
            Connection(
                site_id=site_id,
                provider="cloudflare",
                status="connected",
                external_resource_id="zone-123",
                provider_display_name="example.test",
                encrypted_access_token="must-never-be-exported",
            )
        )
        db.commit()
        db.refresh(user)

    def override_db():
        with Session() as db:
            yield db

    def override_current_user() -> User:
        with Session() as db:
            user = db.get(User, user_id)
            assert user is not None
            db.expunge(user)
            return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_current_user
    return Session, user_id, workspace_id, site_id, TestClient(app)


def test_account_export_contains_user_data_but_not_credentials() -> None:
    Session, _user_id, _workspace_id, _site_id, client = _test_context()
    try:
        response = client.get("/api/auth/export")
        assert response.status_code == 200

        payload = response.json()
        assert payload["account"]["email"] == "owner@example.test"
        assert payload["workspaces"][0]["sites"][0]["connections"][0]["provider"] == "cloudflare"

        raw = response.text
        assert "must-never-be-exported" not in raw
        assert "password_hash" not in raw
        assert "encrypted_access_token" not in raw
        assert "encrypted_refresh_token" not in raw
    finally:
        app.dependency_overrides.clear()


def test_account_deletion_requires_password_and_cascades_owned_workspace() -> None:
    Session, user_id, workspace_id, site_id, client = _test_context()
    try:
        wrong = client.request(
            "DELETE",
            "/api/auth/account",
            json={"current_password": "wrong-password", "confirmation": "DELETE"},
        )
        assert wrong.status_code == 401

        deleted = client.request(
            "DELETE",
            "/api/auth/account",
            json={"current_password": "correct-password", "confirmation": "DELETE"},
        )
        assert deleted.status_code == 204

        with Session() as db:
            assert db.get(User, user_id) is None
            assert db.get(Workspace, workspace_id) is None
            assert db.get(Site, site_id) is None
            assert db.scalar(select(Connection).where(Connection.site_id == site_id)) is None
    finally:
        app.dependency_overrides.clear()
