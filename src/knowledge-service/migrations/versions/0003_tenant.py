"""knowledge-service 多租户：knowledge_bases 增加 tenant_id 隔离键。

Revision ID: 0003_tenant
Revises: dea77e011907
"""

from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_tenant"
down_revision: Union[str, None] = "dea77e011907"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "knowledge_bases",
        sa.Column("tenant_id", sa.String(length=36), nullable=True, index=True),
    )


def downgrade() -> None:
    op.drop_column("knowledge_bases", "tenant_id")
