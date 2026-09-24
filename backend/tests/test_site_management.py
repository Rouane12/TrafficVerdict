from __future__ import annotations

from uuid import UUID

import app.models  # noqa: F401
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies.auth import get_current_user
from app.db.database import Base, get_db
from app.main import app
from app.models.site import Site
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember


def _context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    user_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    workspace_id = UUID("11111111-1111-1111-1111-111111111111")
    site_id = UUID("22222222-2222-2222-2222-222222222222")

    with Session() as db:
        db.add_all(
            [
                User(id=user_id, email="owner@example.test", password_hash="not-used"),
                Workspace(id=workspace_id, name="Workspace", slug="workspace"),
                WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role="owner"),
                Site(
                    id=site_id,
                    workspace_id=workspace_id,
                    name="Old name",
                    domain="old.example",
                    timezone="UTC",
                ),
            ]
        )
        db.commit()

    def override_db():
        with Session() as db:
            yield db

    def override_current_user() -> User:
        return User(id=user_id, email="owner@example.test", password_hash="not-used")

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_current_user
    return Session, TestClient(app), workspace_id, site_id


def test_site_can_be_edited_and_deleted() -> None:
    Session, client, workspace_id, site_id = _context()

    try:
        updated = client.patch(
            f"/api/workspaces/{workspace_id}/sites/{site_id}",
            json={
                "name": "Neural Critic",
                "domain": "https://www.NeuralCritic.net/articles",
                "timezone": "Africa/Casablanca",
            },
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Neural Critic"
        assert updated.json()["domain"] == "www.neuralcritic.net"
        assert updated.json()["timezone"] == "Africa/Casablanca"

        with Session() as db:
            site = db.get(Site, site_id)
            assert site is not None
            assert site.name == "Neural Critic"
            assert site.domain == "www.neuralcritic.net"

        deleted = client.delete(f"/api/workspaces/{workspace_id}/sites/{site_id}")
        assert deleted.status_code == 204

        with Session() as db:
            assert db.scalar(select(Site).where(Site.id == site_id)) is None
    finally:
        app.dependency_overrides.clear()


def test_site_management_is_tenant_scoped() -> None:
    _Session, client, _workspace_id, site_id = _context()
    other_workspace_id = UUID("33333333-3333-3333-3333-333333333333")

    try:
        update = client.patch(
            f"/api/workspaces/{other_workspace_id}/sites/{site_id}",
            json={"name": "Should not work"},
        )
        delete = client.delete(f"/api/workspaces/{other_workspace_id}/sites/{site_id}")

        assert update.status_code == 404
        assert delete.status_code == 404
    finally:
        app.dependency_overrides.clear()
