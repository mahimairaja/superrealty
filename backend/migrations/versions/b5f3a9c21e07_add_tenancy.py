"""add tenancy: tenants table + tenant_id on bookings and call_logs

Revision ID: b5f3a9c21e07
Revises: 824b2e9643aa
Create Date: 2026-07-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'b5f3a9c21e07'
down_revision: Union[str, Sequence[str], None] = '824b2e9643aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'tenants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('clerk_org_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('plan', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_tenants_clerk_org_id'), 'tenants', ['clerk_org_id'], unique=True)
    op.create_index(op.f('ix_tenants_uuid'), 'tenants', ['uuid'], unique=True)

    op.add_column('bookings', sa.Column('tenant_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.create_index(op.f('ix_bookings_tenant_id'), 'bookings', ['tenant_id'], unique=False)

    op.add_column('call_logs', sa.Column('tenant_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.create_index(op.f('ix_call_logs_tenant_id'), 'call_logs', ['tenant_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_call_logs_tenant_id'), table_name='call_logs')
    op.drop_column('call_logs', 'tenant_id')
    op.drop_index(op.f('ix_bookings_tenant_id'), table_name='bookings')
    op.drop_column('bookings', 'tenant_id')
    op.drop_index(op.f('ix_tenants_uuid'), table_name='tenants')
    op.drop_index(op.f('ix_tenants_clerk_org_id'), table_name='tenants')
    op.drop_table('tenants')
