"""Alembic env for agent-service.

动态使用 app.core.db 的 engine（尊重 AGENT_DATABASE_URL：sqlite / PostgreSQL 通用），
不写死 sqlalchemy.url。target_metadata = Base.metadata（含 AgentRun）。
"""
from __future__ import annotations

import os
import sys

# agent-service 目录加入 path，使 `app` 与 `shared` 可导入
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# repo src on path so `shared` package is importable (db.py imports shared.db.connect)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.db import Base, DATABASE_URL
import app.models.run  # noqa: F401  确保 AgentRun 注册到 metadata

config = context.config
# 用 app.core.db 的 DATABASE_URL 覆盖 ini 占位
config.set_main_option("sqlalchemy.url", DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
