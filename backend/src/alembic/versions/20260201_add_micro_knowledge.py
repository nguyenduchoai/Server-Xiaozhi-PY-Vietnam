"""Add micro_knowledge table for AI Tutor

Revision ID: 20260201_add_micro_knowledge
Revises: 20260127_add_themes
Create Date: 2026-02-01 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260201_add_micro_knowledge'
down_revision = '20260127_add_themes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create micro_knowledge table for AI Tutor Micro Knowledge module.
    
    This table stores atomic learning units (15-30 seconds each)
    for adaptive, personalized learning experiences.
    """
    op.create_table(
        'micro_knowledge',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('mk_id', sa.String(100), nullable=False, unique=True),
        sa.Column('subject', sa.String(50), nullable=False),
        sa.Column('topic', sa.String(100), nullable=False),
        sa.Column('difficulty', sa.Integer, default=1),
        sa.Column('target_age', sa.String(20), default='all'),
        sa.Column('content', sa.JSON, nullable=False),
        sa.Column('interaction', sa.JSON, nullable=False),
        sa.Column('tags', sa.JSON, nullable=True),
        sa.Column('source_vocabulary_id', sa.String(36), nullable=True),
        sa.Column('source_type', sa.String(20), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create indexes for common query patterns
    op.create_index('ix_micro_knowledge_mk_id', 'micro_knowledge', ['mk_id'], unique=True)
    op.create_index('ix_micro_knowledge_subject', 'micro_knowledge', ['subject'])
    op.create_index('ix_micro_knowledge_topic', 'micro_knowledge', ['topic'])
    op.create_index('ix_micro_knowledge_difficulty', 'micro_knowledge', ['difficulty'])
    op.create_index('ix_micro_knowledge_is_active', 'micro_knowledge', ['is_active'])
    op.create_index('ix_micro_knowledge_source_vocabulary_id', 'micro_knowledge', ['source_vocabulary_id'])


def downgrade() -> None:
    """Drop micro_knowledge table."""
    op.drop_index('ix_micro_knowledge_source_vocabulary_id', table_name='micro_knowledge')
    op.drop_index('ix_micro_knowledge_is_active', table_name='micro_knowledge')
    op.drop_index('ix_micro_knowledge_difficulty', table_name='micro_knowledge')
    op.drop_index('ix_micro_knowledge_topic', table_name='micro_knowledge')
    op.drop_index('ix_micro_knowledge_subject', table_name='micro_knowledge')
    op.drop_index('ix_micro_knowledge_mk_id', table_name='micro_knowledge')
    op.drop_table('micro_knowledge')
