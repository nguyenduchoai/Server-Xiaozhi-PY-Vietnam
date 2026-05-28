"""add firmware and firmware_deployment tables

Revision ID: d5262552b7d1
Revises: bb1517738d1b
Create Date: 2025-12-20 11:17:06.901878

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd5262552b7d1'
down_revision: Union[str, None] = 'bb1517738d1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create firmware table
    op.create_table('firmware',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('board_type', sa.Enum('ESP32', 'ESP32_S3', 'ESP32_C3', 'ALL', name='board_type_enum'), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('release_notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_latest', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('download_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_firmware_board_type'), 'firmware', ['board_type'], unique=False)
    op.create_index(op.f('ix_firmware_version'), 'firmware', ['version'], unique=False)
    
    # Create firmware_deployment table
    op.create_table('firmware_deployment',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('firmware_id', sa.String(length=36), nullable=False),
        sa.Column('target_type', sa.Enum('ALL', 'BOARD', 'USER', 'DEVICE', name='deployment_target_type_enum'), nullable=False),
        sa.Column('target_value', sa.String(length=255), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'ROLLING_OUT', 'COMPLETED', 'PAUSED', 'CANCELLED', 'FAILED', name='deployment_status_enum'), nullable=False),
        sa.Column('rollout_percentage', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('deployed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ),
        sa.ForeignKeyConstraint(['firmware_id'], ['firmware.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_firmware_deployment_firmware_id'), 'firmware_deployment', ['firmware_id'], unique=False)
    op.create_index(op.f('ix_firmware_deployment_status'), 'firmware_deployment', ['status'], unique=False)


def downgrade() -> None:
    # Drop firmware_deployment table
    op.drop_index(op.f('ix_firmware_deployment_status'), table_name='firmware_deployment')
    op.drop_index(op.f('ix_firmware_deployment_firmware_id'), table_name='firmware_deployment')
    op.drop_table('firmware_deployment')
    
    # Drop firmware table
    op.drop_index(op.f('ix_firmware_version'), table_name='firmware')
    op.drop_index(op.f('ix_firmware_board_type'), table_name='firmware')
    op.drop_table('firmware')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS deployment_status_enum')
    op.execute('DROP TYPE IF EXISTS deployment_target_type_enum')
    op.execute('DROP TYPE IF EXISTS board_type_enum')
