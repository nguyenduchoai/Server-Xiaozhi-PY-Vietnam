"""Add emoji_pack tables

Revision ID: v003_add_emoji_pack
Revises: v002_template_tts_voice
Create Date: 2026-01-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'v003_add_emoji_pack'
down_revision: Union[str, None] = 'v002_template_tts_voice'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create emoji_pack table
    op.create_table('emoji_pack',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_size', sa.Integer(), nullable=False, server_default='64'),
        sa.Column('base_pack', sa.String(length=50), nullable=False, server_default='twemoji'),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('approval_status', sa.String(length=20), nullable=False, server_default='private'),
        sa.Column('download_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_emoji_pack_public', 'emoji_pack', ['is_public', 'approval_status'], unique=False)
    op.create_index(op.f('ix_emoji_pack_user_id'), 'emoji_pack', ['user_id'], unique=False)

    # Create emoji_pack_asset table
    op.create_table('emoji_pack_asset',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('pack_id', sa.String(), nullable=False),
        sa.Column('emotion_name', sa.String(length=50), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('file_type', sa.String(length=10), nullable=False, server_default='png'),
        sa.Column('file_size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('has_animation', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('frame_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_custom', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['pack_id'], ['emoji_pack.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_emoji_asset_pack_emotion', 'emoji_pack_asset', ['pack_id', 'emotion_name'], unique=True)
    op.create_index(op.f('ix_emoji_pack_asset_pack_id'), 'emoji_pack_asset', ['pack_id'], unique=False)

    # Create flash_job table
    op.create_table('flash_job',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('device_id', sa.String(), nullable=False),
        sa.Column('pack_id', sa.String(), nullable=True),
        sa.Column('asset_type', sa.String(length=50), nullable=False, server_default='emoji_pack'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='queued'),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('binary_size', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['device.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pack_id'], ['emoji_pack.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_flash_job_device_id'), 'flash_job', ['device_id'], unique=False)
    op.create_index(op.f('ix_flash_job_user_id'), 'flash_job', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop flash_job
    op.drop_index(op.f('ix_flash_job_user_id'), table_name='flash_job')
    op.drop_index(op.f('ix_flash_job_device_id'), table_name='flash_job')
    op.drop_table('flash_job')

    # Drop emoji_pack_asset
    op.drop_index(op.f('ix_emoji_pack_asset_pack_id'), table_name='emoji_pack_asset')
    op.drop_index('idx_emoji_asset_pack_emotion', table_name='emoji_pack_asset')
    op.drop_table('emoji_pack_asset')

    # Drop emoji_pack
    op.drop_index(op.f('ix_emoji_pack_user_id'), table_name='emoji_pack')
    op.drop_index('idx_emoji_pack_public', table_name='emoji_pack')
    op.drop_table('emoji_pack')
