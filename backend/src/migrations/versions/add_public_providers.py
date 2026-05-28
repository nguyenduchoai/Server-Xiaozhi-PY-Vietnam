"""add_public_providers

Revision ID: add_public_providers
Revises: v004_add_pay2s_integration
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_public_providers'
down_revision = 'v004_add_pay2s_integration'
branch_labels = None
depends_on = None


def upgrade():
    # Add is_public column to provider table
    op.add_column('provider', sa.Column('is_public', sa.Boolean(), nullable=True, default=False))
    
    # Make user_id nullable for public providers
    op.alter_column('provider', 'user_id',
        existing_type=sa.String(36),
        nullable=True
    )
    
    # Set default value for existing rows
    op.execute("UPDATE provider SET is_public = false WHERE is_public IS NULL")
    
    # Create index for is_public
    op.create_index('idx_provider_is_public', 'provider', ['is_public'], unique=False)
    
    # NOTE:
    # Không seed public providers mặc định.
    # User sẽ tự tạo provider cần dùng qua BYO config.


def downgrade():
    # Remove public providers
    op.execute("DELETE FROM provider WHERE is_public = true AND user_id IS NULL")
    
    # Drop index
    op.drop_index('idx_provider_is_public', 'provider')
    
    # Remove is_public column
    op.drop_column('provider', 'is_public')
