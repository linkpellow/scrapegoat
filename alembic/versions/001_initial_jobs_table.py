"""Initial jobs table

Revision ID: 001
Revises: 
Create Date: 2026-01-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('target_url', sa.String(), nullable=False),
        sa.Column('fields', sa.String(), nullable=False),
        sa.Column('requires_auth', sa.Boolean(), nullable=False, default=False),
        sa.Column('frequency', sa.String(), nullable=False),
        sa.Column('strategy', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
    )
    
    # Create indexes for common queries
    op.create_index('ix_jobs_status', 'jobs', ['status'])
    op.create_index('ix_jobs_target_url', 'jobs', ['target_url'])


def downgrade() -> None:
    op.drop_index('ix_jobs_target_url', 'jobs')
    op.drop_index('ix_jobs_status', 'jobs')
    op.drop_table('jobs')
