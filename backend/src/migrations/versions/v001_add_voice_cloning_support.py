"""Add voice cloning support

Revision ID: v001_voice_cloning
Revises: f8a123456789
Create Date: 2024-12-29 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'v001_voice_cloning'
down_revision: Union[str, None] = 'f8a123456789'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create voices table
    op.create_table(
        'voices',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('audio_file_path', sa.String(500), nullable=False, comment='Path to original audio sample'),
        sa.Column('audio_duration', sa.Float(), nullable=False, comment='Duration in seconds'),
        sa.Column('audio_size', sa.Integer(), nullable=False, comment='File size in bytes'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sample_rate', sa.Integer(), nullable=False, server_default='24000', comment='Audio sample rate (Hz)'),
        sa.Column('embeddings', postgresql.BYTEA(), nullable=True, comment='Serialized voice embeddings'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false', comment="User's default voice"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
    )
    
    # Create indexes
    op.create_index(
        'idx_voices_user_id',
        'voices',
        ['user_id'],
        unique=False,
        postgresql_where=sa.text("is_deleted = false")
    )
    
    op.create_index(
        'idx_voices_is_default',
        'voices',
        ['user_id', 'is_default'],
        unique=False,
        postgresql_where=sa.text("is_deleted = false")
    )
    
    op.create_index(
        'idx_voices_is_deleted',
        'voices',
        ['is_deleted']
    )
    
    # Create partial unique index for voice name per user (only active voices)
    op.execute("""
        CREATE UNIQUE INDEX unique_voice_name_per_user 
        ON voices (user_id, name) 
        WHERE is_deleted = false
    """)
    
    # Add voice_id foreign key to agent table
    op.add_column(
        'agent',
        sa.Column('voice_id', sa.String(36), sa.ForeignKey('voices.id', ondelete='SET NULL'), nullable=True)
    )
    
    op.create_index('idx_agent_voice_id', 'agent', ['voice_id'])


def downgrade() -> None:
    # Drop agent.voice_id column and index
    op.drop_index('idx_agent_voice_id', table_name='agent')
    op.drop_column('agent', 'voice_id')
    
    # Drop voices table (indexes will be dropped automatically)
    op.drop_table('voices')
