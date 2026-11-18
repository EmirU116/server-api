"""Create immutable server metric samples.

Revision ID: 0001_metrics
Revises: None
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_metrics"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("server_id", sa.String(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cpu_percent", sa.Float(), nullable=False),
        sa.Column("memory_percent", sa.Float(), nullable=False),
        sa.Column("disk_percent", sa.Float(), nullable=False),
        sa.Column("uptime_seconds", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("server_id", "collected_at", name="uq_metrics_server_time"),
        sa.CheckConstraint("cpu_percent >= 0 AND cpu_percent <= 100"),
        sa.CheckConstraint("memory_percent >= 0 AND memory_percent <= 100"),
        sa.CheckConstraint("disk_percent >= 0 AND disk_percent <= 100"),
        sa.CheckConstraint("uptime_seconds >= 0"),
    )


def downgrade() -> None:
    # Destructive: only run against disposable test data or with explicit approval.
    op.drop_table("metrics")
