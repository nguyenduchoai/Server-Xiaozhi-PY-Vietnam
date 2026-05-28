"""Add device theme tables

Revision ID: 20260127_add_themes
Revises: 
Create Date: 2026-01-27 13:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260127_add_themes'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Device Theme table
    op.create_table(
        'device_theme',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('preview_url', sa.String(500), nullable=True),
        sa.Column('thumbnail_url', sa.String(500), nullable=True),
        sa.Column('theme_data', sa.JSON, nullable=True),
        sa.Column('screen_type', sa.String(50), default='240x240'),
        sa.Column('screen_width', sa.Integer, default=240),
        sa.Column('screen_height', sa.Integer, default=240),
        sa.Column('category', sa.String(50), default='default'),
        sa.Column('tags', sa.JSON, nullable=True),
        sa.Column('is_system', sa.Boolean, default=False),
        sa.Column('created_by', sa.String(36), nullable=True),
        sa.Column('is_public', sa.Boolean, default=True),
        sa.Column('download_count', sa.Integer, default=0),
        sa.Column('rating', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('is_active', sa.Boolean, default=True),
    )
    op.create_index('ix_device_theme_name', 'device_theme', ['name'])
    op.create_index('ix_device_theme_category', 'device_theme', ['category'])
    op.create_index('ix_device_theme_screen_type', 'device_theme', ['screen_type'])
    
    # Device Theme Asset table
    op.create_table(
        'device_theme_asset',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('theme_id', sa.String(36), sa.ForeignKey('device_theme.id'), nullable=False),
        sa.Column('asset_type', sa.String(50), nullable=False),
        sa.Column('file_url', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer, default=0),
        sa.Column('file_format', sa.String(20), default='png'),
        sa.Column('width', sa.Integer, nullable=True),
        sa.Column('height', sa.Integer, nullable=True),
        sa.Column('is_animated', sa.Boolean, default=False),
        sa.Column('frame_count', sa.Integer, default=1),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_device_theme_asset_theme_id', 'device_theme_asset', ['theme_id'])
    
    # Device Theme Installation table
    op.create_table(
        'device_theme_installation',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('device_id', sa.String(36), sa.ForeignKey('device.id'), nullable=False),
        sa.Column('theme_id', sa.String(36), sa.ForeignKey('device_theme.id'), nullable=False),
        sa.Column('installed_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('custom_config', sa.JSON, nullable=True),
        sa.Column('widget_clock_enabled', sa.Boolean, default=True),
        sa.Column('widget_weather_enabled', sa.Boolean, default=True),
        sa.Column('widget_calendar_enabled', sa.Boolean, default=False),
        sa.Column('widget_lunar_enabled', sa.Boolean, default=True),
    )
    op.create_index('ix_device_theme_installation_device_id', 'device_theme_installation', ['device_id'])
    op.create_index('ix_device_theme_installation_theme_id', 'device_theme_installation', ['theme_id'])


def downgrade() -> None:
    op.drop_table('device_theme_installation')
    op.drop_table('device_theme_asset')
    op.drop_table('device_theme')
