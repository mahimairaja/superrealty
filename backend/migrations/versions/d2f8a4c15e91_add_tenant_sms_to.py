"""add tenant sms_to

Revision ID: d2f8a4c15e91
Revises: c4e1a7b93f20
Create Date: 2026-07-01 20:40:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel  # SQLModel column types (e.g. AutoString) appear in migrations
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd2f8a4c15e91'
down_revision: Union[str, Sequence[str], None] = 'c4e1a7b93f20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'tenants',
        sa.Column('sms_to', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tenants', 'sms_to')
