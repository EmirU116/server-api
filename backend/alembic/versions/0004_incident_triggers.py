"""Store optional metric rules on incident records."""

import sqlalchemy as sa
from alembic import op

revision = "0004_incident_triggers"
down_revision = "0003_planned_incidents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("incidents", sa.Column("trigger", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("incidents", "trigger")
