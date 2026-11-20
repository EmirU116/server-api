"""Allow incidents to be planned before they occur."""

from alembic import op

revision = "0003_planned_incidents"
down_revision = "0002_incidents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("incidents_status_check", "incidents", type_="check")
    op.alter_column("incidents", "occurred_at", nullable=True)
    op.create_check_constraint(
        "incidents_status_check",
        "incidents",
        "status IN ('planned', 'open', 'investigating', 'resolved')",
    )
    op.create_check_constraint(
        "incidents_occurrence_check",
        "incidents",
        "(status = 'planned') = (occurred_at IS NULL)",
    )


def downgrade() -> None:
    # PostgreSQL rejects the downgrade if any planned records still exist.
    op.drop_constraint("incidents_occurrence_check", "incidents", type_="check")
    op.alter_column("incidents", "occurred_at", nullable=False)
    op.drop_constraint("incidents_status_check", "incidents", type_="check")
    op.create_check_constraint(
        "incidents_status_check",
        "incidents",
        "status IN ('open', 'investigating', 'resolved')",
    )
