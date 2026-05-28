"""Add NotebookLM tables

Revision ID: 20260130_notebooklm
Revises: 
Create Date: 2026-01-30

Tables:
- notebook: Store user's NotebookLM notebook references
- agent_notebook: Many-to-many agent-notebook mapping
- user_google_auth: Google OAuth tokens (Phase B)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY


# revision identifiers
revision = '20260130_notebooklm'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create notebook table
    op.create_table(
        'notebook',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('notebook_url', sa.String(500), nullable=False),
        sa.Column('notebook_external_id', sa.String(100), nullable=True, index=True),
        sa.Column('topics', ARRAY(sa.String()), nullable=True),
        sa.Column('tags', ARRAY(sa.String()), nullable=True),
        sa.Column('source_count', sa.Integer(), default=0),
        sa.Column('last_synced', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    
    # Create agent_notebook table (many-to-many)
    op.create_table(
        'agent_notebook',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agent_id', sa.String(36), sa.ForeignKey('agent.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('notebook_id', sa.String(36), sa.ForeignKey('notebook.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('is_primary', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('agent_id', 'notebook_id', name='uq_agent_notebook'),
    )
    
    # Create user_google_auth table (Phase B)
    op.create_table(
        'user_google_auth',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
        sa.Column('google_email', sa.String(255), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expiry', sa.DateTime(timezone=True), nullable=True),
        sa.Column('session_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('user_google_auth')
    op.drop_table('agent_notebook')
    op.drop_table('notebook')
