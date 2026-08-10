"""initial migration: create agent_runs table (audit / observability).

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=True),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("thread_id", sa.String(36), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        # PG 上落 JSONB；sqlite 下 alembic 不跑（init_db 回退 create_all 用 TEXT 亲和）
        sa.Column("steps_json", JSONB(), nullable=True),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("status", sa.String(16), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_agent_runs_project_id", "agent_runs", ["project_id"])
    op.create_index("ix_agent_runs_user_id", "agent_runs", ["user_id"])
    op.create_index("ix_agent_runs_thread_id", "agent_runs", ["thread_id"])


def downgrade() -> None:
    op.drop_table("agent_runs")
