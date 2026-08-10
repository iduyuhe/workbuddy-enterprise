"""auth-service 等保三级：用户登录失败计数与锁定时间。

Revision ID: 0002_lockout
Revises: 674e6ff4e08c
"""

from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_lockout"
down_revision: Union[str, None] = "674e6ff4e08c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("failed_login_count", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("locked_until", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_count")
