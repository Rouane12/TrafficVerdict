from __future__ import annotations

from uuid import UUID

import app.models  # noqa: F401
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies.auth import get_current_user
from app.db.database import Base, get_db
from app.main import app
from app.models.site import Site
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember


def test_user_cannot_read_another_users_workspace_or_site() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    user_a_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    user_b_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    workspace_a_id = UUID("11111111-1111-1111-1111-111111111111")
    workspace_b_id = UUID("22222222-2222-2222-2222-222222222222")
    site_b_id = UUID("33333333-3333-3333-3333-333333333333")

    with Session() as db:
        db.add_all(
            [
                User(id=user_a_id, email="a@example.test", password_hash="not-used"),
                User(id=user_b_id, email="b@example.test", password_hash="not-used"),
                Workspace(id=workspace_a_id, name="A", slug="a"),
                Workspace(id=workspace_b_id, name="B", slug="b"),
                WorkspaceMember(workspace_id=workspace_a_id, user_id=user_a_id, role="owner"),
                WorkspaceMember(workspace_id=workspace_b_id, user_id=user_b_id, role="owner"),
                Site(
                    id=site_b_id,
                    workspace_id=workspace_b_id,
                    name="Private B",
                    domain="private-b.example",
                    timezone="UTC",
                ),
            ]
        )
        db.commit()

    def override_db():
        with Session() as db:
            yield db

    def override_current_user() -> User:
        return User(id=user_a_id, email="a@example.test", password_hash="not-used")

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_current_user
    client = TestClient(app)

    try:
        workspace_response = client.get(f"/api/workspaces/{workspace_b_id}/sites")
        cloudflare_response = client.get(f"/api/sites/{site_b_id}/integrations/cloudflare/status")
        normalization_response = client.get(f"/api/sites/{site_b_id}/normalization")
        reconciliation_response = client.get(f"/api/sites/{site_b_id}/reconciliation")
        changes_response = client.get(f"/api/sites/{site_b_id}/changes")

        assert workspace_response.status_code == 404
        assert cloudflare_response.status_code == 404
        assert normalization_response.status_code == 404
        assert reconciliation_response.status_code == 404
        assert changes_response.status_code == 404
    finally:
        app.dependency_overrides.clear()
