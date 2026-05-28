"""Add advanced AI features: memory, triggers, skills

Revision ID: f8a123456789
Revises: d3a7c924a3c4
Create Date: 2025-12-27 03:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8a123456789'
down_revision: Union[str, None] = 'd3a7c924a3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Conversation Memories table
    op.create_table('conversation_memories',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('device_id', sa.String(50), nullable=False, index=True),
        sa.Column('key', sa.String(100), nullable=False, index=True),
        sa.Column('value', sa.JSON(), nullable=True, default=dict),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=True),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agent.id', ondelete='SET NULL'), nullable=True),
        sa.Column('memory_type', sa.String(20), nullable=False, server_default='long_term'),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('source', sa.String(20), nullable=False, server_default='explicit'),
        sa.Column('source_message_id', sa.String(36), nullable=True),
        sa.Column('access_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_memory_device_key', 'conversation_memories', ['device_id', 'key'])
    op.create_index('idx_memory_user_type', 'conversation_memories', ['user_id', 'memory_type'])
    op.create_index('idx_memory_expires', 'conversation_memories', ['expires_at'])

    # Emotion Logs table
    op.create_table('emotion_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('device_id', sa.String(50), nullable=False, index=True),
        sa.Column('emotion', sa.String(20), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=True),
        sa.Column('message_id', sa.String(36), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('emotion_scores', sa.JSON(), nullable=True),
        sa.Column('source_text', sa.Text(), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_emotion_device_time', 'emotion_logs', ['device_id', 'detected_at'])

    # Proactive Triggers table
    op.create_table('proactive_triggers',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('device_id', sa.String(50), nullable=True, index=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=True),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agent.id', ondelete='SET NULL'), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('trigger_type', sa.String(30), nullable=False, server_default='time_based'),
        sa.Column('condition', sa.JSON(), nullable=True, default=dict),
        sa.Column('action_type', sa.String(30), nullable=False, server_default='speak'),
        sa.Column('action_config', sa.JSON(), nullable=True, default=dict),
        sa.Column('template_vars', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cooldown_minutes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_daily_triggers', sa.Integer(), nullable=True),
        sa.Column('daily_trigger_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_trigger_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_trigger_device_active', 'proactive_triggers', ['device_id', 'is_active'])
    op.create_index('idx_trigger_type', 'proactive_triggers', ['trigger_type'])

    # Skills table
    op.create_table('skills',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('author_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('author_name', sa.String(100), nullable=False),
        sa.Column('config', sa.JSON(), nullable=True, default=dict),
        sa.Column('short_description', sa.String(200), nullable=True),
        sa.Column('skill_type', sa.String(30), nullable=False, server_default='mcp_server'),
        sa.Column('category', sa.String(30), nullable=False, server_default='utilities'),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('author_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('version', sa.String(20), nullable=False, server_default='1.0.0'),
        sa.Column('min_platform_version', sa.String(20), nullable=True),
        sa.Column('changelog', sa.Text(), nullable=True),
        sa.Column('icon_url', sa.String(500), nullable=True),
        sa.Column('banner_url', sa.String(500), nullable=True),
        sa.Column('screenshots', sa.JSON(), nullable=True),
        sa.Column('demo_video_url', sa.String(500), nullable=True),
        sa.Column('readme', sa.Text(), nullable=True),
        sa.Column('documentation_url', sa.String(500), nullable=True),
        sa.Column('support_url', sa.String(500), nullable=True),
        sa.Column('install_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('active_installs', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rating', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('rating_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_premium', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('price', sa.Integer(), nullable=True),
        sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('moderation_status', sa.String(20), nullable=True),
        sa.Column('moderation_note', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_skill_category', 'skills', ['category', 'is_public'])
    op.create_index('idx_skill_featured', 'skills', ['is_featured', 'is_public'])
    op.create_index('idx_skill_rating', 'skills', ['rating', 'install_count'])

    # Skill Installations table
    op.create_table('skill_installations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('skill_id', sa.String(36), sa.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('installed_version', sa.String(20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('custom_config', sa.JSON(), nullable=True),
        sa.Column('installed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('uninstalled_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_installation_user_skill', 'skill_installations', ['user_id', 'skill_id'], unique=True)

    # Skill Reviews table
    op.create_table('skill_reviews',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('skill_id', sa.String(36), sa.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('version_reviewed', sa.String(20), nullable=False),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('is_verified_purchase', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('helpful_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_approved', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_hidden', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_review_skill_rating', 'skill_reviews', ['skill_id', 'rating'])


def downgrade() -> None:
    op.drop_table('skill_reviews')
    op.drop_table('skill_installations')
    op.drop_table('skills')
    op.drop_table('proactive_triggers')
    op.drop_table('emotion_logs')
    op.drop_table('conversation_memories')
