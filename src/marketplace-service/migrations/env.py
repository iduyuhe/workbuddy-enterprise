"""Alembic env for marketplace-service.

Dynamically uses app.core.db engine (honors DATABASE_URL: sqlite / PostgreSQL),
does not hardcode sqlalchemy.url. target_metadata = Base.metadata.

Each service uses its OWN alembic version table (alembic_version_marketplace) so
multiple services can share one PostgreSQL instance without clobbering each
other's migration chain (microservice-grade isolation).
"""
from __future__ import annotations

import os
import sys

# service root on path so `app` is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# repo src on path so `shared` package is importable (db.py imports shared.db.connect)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.db import Base, DATABASE_URL
import app.models.package  # noqa: F401

VERSION_TABLE = "alembic_version_marketplace"

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=VERSION_TABLE,
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
            version_table=VERSION_TABLE,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
