"""Add Google Analytics connection state and normalized metric snapshots.

Revision ID: 0003_ga4_foundation
Revises: 0002_add_password_hash
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_ga4_foundation"
down_revision = "0002_add_password_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("connections", sa.Column("provider_display_name", sa.String(length=255), nullable=True))
    op.add_column("connections", sa.Column("provider_account_id", sa.String(length=255), nullable=True))
    op.add_column("connections", sa.Column("encrypted_access_token", sa.Text(), nullable=True))
    op.add_column("connections", sa.Column("encrypted_refresh_token", sa.Text(), nullable=True))
    op.add_column("connections", sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("connections", sa.Column("granted_scopes", sa.Text(), nullable=True))
    op.add_column("connections", sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("connections", sa.Column("last_error", sa.Text(), nullable=True))

    op.create_table(
        "metric_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("breakdowns", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metric_snapshots_site_id", "metric_snapshots", ["site_id"], unique=False)
    op.create_index("ix_metric_snapshots_source", "metric_snapshots", ["source"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_metric_snapshots_source", table_name="metric_snapshots")
    op.drop_index("ix_metric_snapshots_site_id", table_name="metric_snapshots")
    op.drop_table("metric_snapshots")

    op.drop_column("connections", "last_error")
    op.drop_column("connections", "last_synced_at")
    op.drop_column("connections", "granted_scopes")
    op.drop_column("connections", "token_expires_at")
    op.drop_column("connections", "encrypted_refresh_token")
    op.drop_column("connections", "encrypted_access_token")
    op.drop_column("connections", "provider_account_id")
    op.drop_column("connections", "provider_display_name")
