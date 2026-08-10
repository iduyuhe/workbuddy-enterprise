"""agent-service 多租户：agent_runs 增加 tenant_id 隔离键。

Revision ID: 0003_tenant
Revises: 0001_initial
"""

from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_tenant"
down_revision: Union[str, None] = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_runs",
        sa.Column("tenant_id", sa.String(length=36), nullable=True, index=True),
    )


def downgrade() -> None:
    op.drop_column("agent_runs", "tenant_id")
