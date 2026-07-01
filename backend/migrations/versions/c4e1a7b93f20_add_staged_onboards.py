"""add staged_onboards

Revision ID: c4e1a7b93f20
Revises: b5f3a9c21e07
Create Date: 2026-07-01 20:10:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel  # SQLModel column types (e.g. AutoString) appear in migrations
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c4e1a7b93f20'
down_revision: Union[str, Sequence[str], None] = 'b5f3a9c21e07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'staged_onboards',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tenant_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('drafts', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('profile', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_staged_onboards_tenant_id'),
        'staged_onboards',
        ['tenant_id'],
        unique=True,
    )
    op.create_index(
        op.f('ix_staged_onboards_uuid'), 'staged_onboards', ['uuid'], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_staged_onboards_uuid'), table_name='staged_onboards')
    op.drop_index(op.f('ix_staged_onboards_tenant_id'), table_name='staged_onboards')
    op.drop_table('staged_onboards')
