"""Add durable scheduled sync jobs.

Revision ID: 0004_sync_jobs
Revises: 0003_ga4_foundation
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_sync_jobs"
down_revision = "0003_ga4_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sync_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_sync_jobs_idempotency_key"),
    )
    op.create_index("ix_sync_jobs_site_id", "sync_jobs", ["site_id"], unique=False)
    op.create_index("ix_sync_jobs_provider", "sync_jobs", ["provider"], unique=False)
    op.create_index("ix_sync_jobs_status", "sync_jobs", ["status"], unique=False)
    op.create_index("ix_sync_jobs_scheduled_for", "sync_jobs", ["scheduled_for"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sync_jobs_scheduled_for", table_name="sync_jobs")
    op.drop_index("ix_sync_jobs_status", table_name="sync_jobs")
    op.drop_index("ix_sync_jobs_provider", table_name="sync_jobs")
    op.drop_index("ix_sync_jobs_site_id", table_name="sync_jobs")
    op.drop_table("sync_jobs")
