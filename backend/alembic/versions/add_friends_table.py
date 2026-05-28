"""Add friends table for cross-account intercom

Revision ID: add_friends_table
Revises: v003_add_emoji_pack
Create Date: 2026-02-03 21:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_friends_table'
down_revision = 'v003_add_emoji_pack'
branch_labels = None
depends_on = None


def upgrade():
    # Friends table - stores relationships between users
    op.create_table(
        'friends',
        sa.Column('id', sa.String(36), nullable=False),
        
        # Requester (who sent the friend request)
        sa.Column('user_id', sa.String(36), nullable=False),
        
        # Recipient (who received the friend request)
        sa.Column('friend_id', sa.String(36), nullable=False),
        
        # Relationship status: pending, accepted, rejected, blocked
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        
        # Can this friend call me via Intercom?
        sa.Column('intercom_enabled', sa.Boolean(), nullable=False, server_default='true'),
        
        # Custom display name for this friend
        sa.Column('nickname', sa.String(100), nullable=True),
        
        # Private notes about this friend
        sa.Column('notes', sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['friend_id'], ['user.id'], ondelete='CASCADE'),
        
        # Each user can only have one relationship with another user
        sa.UniqueConstraint('user_id', 'friend_id', name='friends_unique'),
        
        # Cannot friend yourself
        sa.CheckConstraint('user_id != friend_id', name='friends_not_self'),
        
        # Status must be valid
        sa.CheckConstraint("status IN ('pending', 'accepted', 'rejected', 'blocked')", name='friends_status_check'),
    )
    
    # Indexes for common queries
    op.create_index('idx_friends_user_id', 'friends', ['user_id'])
    op.create_index('idx_friends_friend_id', 'friends', ['friend_id'])
    op.create_index('idx_friends_status', 'friends', ['status'])
    
    # Composite index for efficient friendship lookups
    op.create_index('idx_friends_lookup', 'friends', ['user_id', 'friend_id', 'status'])


def downgrade():
    op.drop_table('friends')
