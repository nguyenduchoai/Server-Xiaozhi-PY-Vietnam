"""Add license and features to firmware and device

Revision ID: v005_license_features
Revises: v004_add_pay2s_integration
Create Date: 2026-02-12
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "v005_license_features"
down_revision = "v004_add_pay2s_integration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add license and feature management columns."""
    
    # Add license_qty and features_config to firmware table
    op.add_column("firmware", sa.Column("license_qty", sa.Integer(), nullable=True))
    op.add_column("firmware", sa.Column("features_config", sa.Text(), nullable=True))
    op.add_column("firmware", sa.Column("display_name", sa.String(255), nullable=True))
    
    # Add features_override and custom_firmware_id to device table
    op.add_column("device", sa.Column("features_override", sa.Text(), nullable=True))
    op.add_column("device", sa.Column("custom_firmware_id", sa.String(36), nullable=True))
    
    # Add index for custom_firmware_id
    op.create_index(
        "ix_device_custom_firmware_id",
        "device",
        ["custom_firmware_id"],
    )


def downgrade() -> None:
    """Remove license and feature management columns."""
    op.drop_index("ix_device_custom_firmware_id", table_name="device")
    op.drop_column("device", "custom_firmware_id")
    op.drop_column("device", "features_override")
    op.drop_column("firmware", "display_name")
    op.drop_column("firmware", "features_config")
    op.drop_column("firmware", "license_qty")
