"""agent-service 新增 agent_playbooks 表（剧本资源，多租户隔离）。

Revision ID: 0004_playbook
Revises: 0003_tenant
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_playbook"
down_revision: Union[str, None] = "0003_tenant"
branch_labels = None
depends_on = None

# JSON：PostgreSQL 落 JSONB，其余方言用通用 JSON
JSONType = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "agent_playbooks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=True, index=True),
        sa.Column("project_id", sa.String(length=36), nullable=True, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("defaults", JSONType, nullable=True),
        sa.Column("scenario_flow", JSONType, nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("agent_playbooks")
