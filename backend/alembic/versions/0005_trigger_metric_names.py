"""Align incident trigger metrics with the collected measurements.

Nothing collects GPU readings, so GPU rules could never be evaluated; they are
cleared. The "storage" rule watched disk_percent and is renamed to "disk".
"""

from alembic import op

revision = "0005_trigger_metric_names"
down_revision = "0004_incident_triggers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE incidents SET trigger = NULL WHERE trigger->>'metric' = 'gpu'")
    op.execute(
        "UPDATE incidents "
        "SET trigger = jsonb_set(trigger::jsonb, '{metric}', '\"disk\"')::json "
        "WHERE trigger->>'metric' = 'storage'"
    )


def downgrade() -> None:
    # Cleared GPU rules cannot be restored; only the rename is reversible.
    op.execute(
        "UPDATE incidents "
        "SET trigger = jsonb_set(trigger::jsonb, '{metric}', '\"storage\"')::json "
        "WHERE trigger->>'metric' = 'disk'"
    )
