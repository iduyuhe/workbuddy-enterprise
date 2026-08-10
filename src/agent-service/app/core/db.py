"""agent-runtime 数据库：sqlite 默认，可通过 AGENT_DATABASE_URL 切 PostgreSQL。"""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("AGENT_DATABASE_URL", "sqlite:///./agent-service_ctl.db")
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import app.models.run  # noqa: F401  ensure tables registered

    Base.metadata.create_all(bind=engine)


# 启动时打印 dialect/url（脱敏密码）
import re as _re
_safe = _re.sub(r"://[^@]+@", "://***@", DATABASE_URL)
print(f"[agent-db] dialect={engine.dialect.name} url={_safe}", flush=True)
