"""Add Pay2s payment gateway

Revision ID: add_pay2s_integration
Revises: 
Create Date: 2026-01-15 09:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'v004_add_pay2s_integration'
down_revision: Union[str, None] = 'v003_add_emoji_pack'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add Pay2s config columns to site_settings
    op.add_column('site_settings', sa.Column('pay2s_enabled', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('site_settings', sa.Column('pay2s_sandbox_mode', sa.Boolean(), nullable=True, server_default='true'))
    op.add_column('site_settings', sa.Column('pay2s_partner_code', sa.String(50), nullable=True, server_default=''))
    op.add_column('site_settings', sa.Column('pay2s_access_key', sa.String(100), nullable=True, server_default=''))
    op.add_column('site_settings', sa.Column('pay2s_secret_key', sa.Text(), nullable=True, server_default=''))
    op.add_column('site_settings', sa.Column('pay2s_payment_timeout_minutes', sa.Integer(), nullable=True, server_default='15'))
    op.add_column('site_settings', sa.Column('pay2s_bank_account_number', sa.String(50), nullable=True, server_default=''))
    op.add_column('site_settings', sa.Column('pay2s_bank_id', sa.String(20), nullable=True, server_default=''))
    
    # Create pay2s_transaction table
    op.create_table(
        'pay2s_transaction',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('order_id', sa.String(64), unique=True, nullable=False, index=True),
        sa.Column('request_id', sa.String(64), nullable=False),
        sa.Column('order_info', sa.String(100), nullable=False),
        
        sa.Column('user_id', sa.String(50), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('plan_id', sa.Integer(), sa.ForeignKey('subscription_plan.id'), nullable=False),
        sa.Column('user_subscription_id', sa.String(50), sa.ForeignKey('user_subscription.id'), nullable=True),
        
        sa.Column('amount', sa.BigInteger(), nullable=False),
        sa.Column('billing_cycle', sa.String(20), nullable=False, server_default='monthly'),
        
        sa.Column('payment_url', sa.Text(), nullable=True),
        sa.Column('trans_id', sa.BigInteger(), nullable=True),
        sa.Column('result_code', sa.Integer(), nullable=True),
        sa.Column('pay_type', sa.String(20), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        
        sa.Column('status', sa.String(20), nullable=False, server_default='pending', index=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column('payment_url_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.Column('ipn_received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ipn_raw_payload', sa.JSON(), nullable=True),
        sa.Column('webhook_received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('webhook_raw_payload', sa.JSON(), nullable=True),
        
        sa.Column('signature_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('verification_attempts', sa.Integer(), nullable=False, server_default='0'),
        
        sa.Column('email_sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('email_sent_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    # Drop pay2s_transaction table
    op.drop_table('pay2s_transaction')
    
    # Remove Pay2s config columns from site_settings
    op.drop_column('site_settings', 'pay2s_enabled')
    op.drop_column('site_settings', 'pay2s_sandbox_mode')
    op.drop_column('site_settings', 'pay2s_partner_code')
    op.drop_column('site_settings', 'pay2s_access_key')
    op.drop_column('site_settings', 'pay2s_secret_key')
    op.drop_column('site_settings', 'pay2s_payment_timeout_minutes')
    op.drop_column('site_settings', 'pay2s_bank_account_number')
    op.drop_column('site_settings', 'pay2s_bank_id')
