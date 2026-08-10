"""audit-service 等保三级：明细加密标记 + 完整性哈希。

Revision ID: 0002_audit_sec
Revises: ae71f3282012
"""

from __future__ import annotations

from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_audit_sec"
down_revision: Union[str, None] = "ae71f3282012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audit_logs",
        sa.Column("enc_ver", sa.Integer(), nullable=True, server_default="1"),
    )
    op.add_column(
        "audit_logs",
        sa.Column("integrity_hash", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("audit_logs", "integrity_hash")
    op.drop_column("audit_logs", "enc_ver")
