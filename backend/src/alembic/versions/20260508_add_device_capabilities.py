"""Add device capabilities columns (multi-board capability profile from FW hello)

Revision ID: 20260508_add_device_capabilities
Revises: 20260201_add_micro_knowledge
Create Date: 2026-05-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260508_add_device_capabilities"
down_revision = "20260201_add_micro_knowledge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # JSONB on Postgres, JSON elsewhere — matches the existing `features`
    # column on `device`.
    op.add_column(
        "device",
        sa.Column("capabilities", sa.JSON(), nullable=True),
    )
    op.add_column(
        "device",
        sa.Column(
            "capabilities_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Optional: index a few hot booleans for capability-aware queries.
    # We use functional/expression indexes on the JSON since JSON_EXTRACT
    # is portable across MySQL/Postgres for boolean fields.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_device_caps_can_camera "
            "ON device ((capabilities ->> 'can_camera'))"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_device_caps_soc "
            "ON device ((capabilities ->> 'soc'))"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_device_caps_can_camera")
        op.execute("DROP INDEX IF EXISTS ix_device_caps_soc")
    op.drop_column("device", "capabilities_updated_at")
    op.drop_column("device", "capabilities")
