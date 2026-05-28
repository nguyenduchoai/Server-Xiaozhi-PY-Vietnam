"""add_provider_access_to_subscription_plan

Revision ID: 720e6cbc0faa
Revises: 8ea1de3885be
Create Date: 2025-12-17 19:25:51.761621

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '720e6cbc0faa'
down_revision: Union[str, None] = '8ea1de3885be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add provider access columns to subscription_plan
    op.add_column('subscription_plan', sa.Column('allowed_provider_types', sa.JSON(), nullable=True))
    op.add_column('subscription_plan', sa.Column('allow_custom_providers', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('subscription_plan', sa.Column('allowed_provider_categories', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('subscription_plan', 'allowed_provider_categories')
    op.drop_column('subscription_plan', 'allow_custom_providers')
    op.drop_column('subscription_plan', 'allowed_provider_types')
