"""Add persistent incident records without changing existing metrics.

Revision ID: 0002_incidents
Revises: 0001_metrics
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_incidents"
down_revision = "0001_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("server_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.String(5000), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("char_length(title) BETWEEN 1 AND 200"),
        sa.CheckConstraint("char_length(description) BETWEEN 1 AND 5000"),
        sa.CheckConstraint("severity IN ('info', 'warning', 'critical')"),
        sa.CheckConstraint("status IN ('open', 'investigating', 'resolved')"),
        sa.CheckConstraint(
            "(status = 'resolved' AND resolved_at IS NOT NULL) OR "
            "(status != 'resolved' AND resolved_at IS NULL)"
        ),
    )
    op.create_index(
        "ix_incidents_server_created", "incidents", ["server_id", "created_at", "id"]
    )


def downgrade() -> None:
    # Destructive: use only with disposable data or explicit approval.
    op.drop_index("ix_incidents_server_created", table_name="incidents")
    op.drop_table("incidents")
