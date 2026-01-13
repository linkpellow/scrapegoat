"""add_api_key_usage_tracking

Revision ID: f1a2b3c4d5e6
Revises: c98fac10e668
Create Date: 2026-01-12 16:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'c98fac10e668'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create api_key_usage table
    op.create_table(
        'api_key_usage',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('total_credits', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('used_credits', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('remaining_credits', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on provider for faster lookups
    op.create_index(op.f('ix_api_key_usage_provider'), 'api_key_usage', ['provider'])
    op.create_index(op.f('ix_api_key_usage_is_active'), 'api_key_usage', ['is_active'])


def downgrade() -> None:
    op.drop_index('ix_api_key_usage_is_active', table_name='api_key_usage')
    op.drop_index('ix_api_key_usage_provider', table_name='api_key_usage')
    op.drop_table('api_key_usage')
