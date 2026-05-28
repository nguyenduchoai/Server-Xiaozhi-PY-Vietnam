"""Add knowledge_base tables and knowledge_base_id column

Revision ID: 20260128_knowledge_base
Revises: 20260127_add_themes
Create Date: 2026-01-28 08:50:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260128_knowledge_base'
down_revision = 'add_public_providers'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create knowledge_base table
    op.create_table(
        'knowledge_base',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('ragflow_dataset_id', sa.String(100), nullable=True),
        sa.Column('embedding_model', sa.String(100), nullable=False, server_default='text-embedding-3-small'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false', index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create agent_knowledge_base junction table
    op.create_table(
        'agent_knowledge_base',
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agent.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('knowledge_base_id', sa.String(36), sa.ForeignKey('knowledge_base.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    
    # Create indexes for junction table
    op.create_index('ix_akb_agent_id', 'agent_knowledge_base', ['agent_id'])
    op.create_index('ix_akb_kb_id', 'agent_knowledge_base', ['knowledge_base_id'])
    
    # Add knowledge_base_id column to knowledge_embeddings
    op.add_column(
        'knowledge_embeddings',
        sa.Column('knowledge_base_id', sa.String(36), nullable=True, index=True)
    )
    
    # Create index for knowledge_base_id + created_at
    op.create_index(
        'ix_knowledge_kb_created',
        'knowledge_embeddings',
        ['knowledge_base_id', 'created_at']
    )
    
    # Make agent_id nullable (for transition period)
    op.alter_column(
        'knowledge_embeddings',
        'agent_id',
        existing_type=sa.String(50),
        nullable=True
    )


def downgrade() -> None:
    # Remove knowledge_base_id column from knowledge_embeddings
    op.drop_index('ix_knowledge_kb_created', table_name='knowledge_embeddings')
    op.drop_column('knowledge_embeddings', 'knowledge_base_id')
    
    # Make agent_id non-nullable again
    op.alter_column(
        'knowledge_embeddings',
        'agent_id',
        existing_type=sa.String(50),
        nullable=False
    )
    
    # Drop junction table indexes
    op.drop_index('ix_akb_kb_id', table_name='agent_knowledge_base')
    op.drop_index('ix_akb_agent_id', table_name='agent_knowledge_base')
    
    # Drop tables
    op.drop_table('agent_knowledge_base')
    op.drop_table('knowledge_base')
