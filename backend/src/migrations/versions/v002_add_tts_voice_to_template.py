"""Add tts_voice column to template table

Revision ID: v002_template_tts_voice
Revises: v001_voice_cloning
Create Date: 2024-12-29 10:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'v002_template_tts_voice'
down_revision: Union[str, None] = 'v001_voice_cloning'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if column exists first to be safe
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('template')]
    
    if 'tts_voice' not in columns:
        op.add_column('template', sa.Column('tts_voice', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('template', 'tts_voice')
