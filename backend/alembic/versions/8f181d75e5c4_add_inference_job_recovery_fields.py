
"""add inference job recovery fields

Revision ID: 8f181d75e5c4
Revises: 6fd3ce5a106c
Create Date: 2026-10-19 22:05:22.790072

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# Revision identifiers, used by Alembic.
revision: str = '8f181d75e5c4'

down_revision: Union[str, Sequence[str], None] = '6fd3ce5a106c'

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Apply database schema changes.
    """
    with op.batch_alter_table('inference_jobs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('worker_id', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('claim_token', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('heartbeat_at', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'))
        batch_op.create_index('idx_inference_jobs_heartbeat', ['status', 'heartbeat_at'], unique=False)


def downgrade() -> None:
    """
    Reverse database schema changes.
    """
    with op.batch_alter_table('inference_jobs', schema=None) as batch_op:
        batch_op.drop_index('idx_inference_jobs_heartbeat')
        batch_op.drop_column('attempt_count')
        batch_op.drop_column('heartbeat_at')
        batch_op.drop_column('claim_token')
        batch_op.drop_column('worker_id')
