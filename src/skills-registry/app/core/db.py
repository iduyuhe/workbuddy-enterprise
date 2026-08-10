"""SQLAlchemy 引擎 / session / Base。URL 来自 env DATABASE_URL（默认 sqlite）。"""
import os
from sqlalchemy import create_engine

from shared.db.connect import normalize_database_url
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL", "sqlite:///./skills.db"))

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args, future=True)
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
    # 导入模型以注册到 Base.metadata
    from app.models import skills  # noqa: F401

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
        print("[skills-db] alembic upgrade head OK", flush=True)
    except Exception as e:
        print(f"[skills-db] alembic unavailable ({e!r}); fallback create_all", flush=True)
        Base.metadata.create_all(bind=engine)
