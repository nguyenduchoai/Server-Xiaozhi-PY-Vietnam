"""add course price and purchase

Revision ID: 20260506_course
Revises: 20250131_education_lms
Create Date: 2026-05-06 16:03:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260506_course'
down_revision: Union[str, None] = '20250131_education_lms'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add price columns to edu_course
    op.add_column('edu_course', sa.Column('price', sa.BigInteger(), server_default='0', nullable=False))
    op.add_column('edu_course', sa.Column('original_price', sa.BigInteger(), server_default='0', nullable=False))

    # Create edu_course_purchase table
    op.create_table(
        'edu_course_purchase',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('course_id', sa.String(36), sa.ForeignKey('edu_course.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('transaction_id', sa.String(100), nullable=True),
        sa.Column('amount', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('edu_course_purchase')
    op.drop_column('edu_course', 'original_price')
    op.drop_column('edu_course', 'price')
