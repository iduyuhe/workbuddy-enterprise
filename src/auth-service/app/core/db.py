"""SQLAlchemy engine / session / base for auth-service."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # import models so they register on Base.metadata
    from app.models import rbac, org  # noqa: F401

    import os
    try:
        from alembic import command
        from alembic.config import Config

        # alembic.ini / migrations live at the service root (3 levels up from app/core/db.py)
        _here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cfg = Config(os.path.join(_here, "alembic.ini"))
        cfg.set_main_option("script_location", os.path.join(_here, "migrations"))
        cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
        command.upgrade(cfg, "head")
        print("[auth-db] alembic upgrade head OK", flush=True)
    except Exception as e:
        print(f"[auth-db] alembic unavailable ({e!r}); fallback create_all", flush=True)
        Base.metadata.create_all(bind=engine)
