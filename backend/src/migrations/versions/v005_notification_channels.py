"""Add notification_channels to agent table

Revision ID: v005_notification_channels
Create Date: 2026-02-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


revision = "v005_notification_channels"
down_revision = None  # standalone migration
branch_labels = None
depends_on = None


def upgrade():
    """Add notification_channels JSON column to agent table."""
    op.add_column(
        "agent",
        sa.Column(
            "notification_channels",
            JSON,
            nullable=True,
            server_default=None,
            comment="Multi-channel notification config: Telegram, Zalo, escalation, daily report",
        ),
    )


def downgrade():
    """Remove notification_channels column from agent table."""
    op.drop_column("agent", "notification_channels")
