"""add_mcp_template_tools_limits

Revision ID: bb1517738d1b
Revises: 720e6cbc0faa
Create Date: 2025-12-17 20:30:16.785383

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'bb1517738d1b'
down_revision: Union[str, None] = '720e6cbc0faa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns with server_default to handle existing rows
    op.add_column('subscription_plan', sa.Column('max_mcps', sa.Integer(), nullable=False, server_default='3'))
    op.add_column('subscription_plan', sa.Column('max_templates', sa.Integer(), nullable=False, server_default='5'))
    op.add_column('subscription_plan', sa.Column('max_tools', sa.Integer(), nullable=False, server_default='10'))


def downgrade() -> None:
    op.drop_column('subscription_plan', 'max_tools')
    op.drop_column('subscription_plan', 'max_templates')
    op.drop_column('subscription_plan', 'max_mcps')
