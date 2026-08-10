"""auth-service 多租户：users / projects 增加 tenant_id 隔离键。

Revision ID: 0003_tenant
Revises: 0002_lockout
"""

from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_tenant"
down_revision: Union[str, None] = "0002_lockout"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("tenant_id", sa.String(length=36), nullable=True, index=True),
    )
    op.add_column(
        "projects",
        sa.Column("tenant_id", sa.String(length=36), nullable=True, index=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "tenant_id")
    op.drop_column("users", "tenant_id")
