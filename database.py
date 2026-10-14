import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

BASE_DIR = Path(__file__).resolve().parent


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        # Neon/Supabase/Heroku style URLs -> SQLAlchemy + psycopg2
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg2://" + url[len("postgresql://"):]
        return url
    if os.getenv("VERCEL"):
        # Vercel's disk is read-only except /tmp, and /tmp is wiped often.
        # Fine for a quick test, NOT for real data. Set DATABASE_URL instead.
        return "sqlite:////tmp/database.db"
    return f"sqlite:///{BASE_DIR / 'database.db'}"


DATABASE_URL = _database_url()

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # Serverless: open a fresh connection per request instead of keeping a pool.
    engine = create_engine(DATABASE_URL, poolclass=NullPool, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    """FastAPI dependency: one database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema():
    """Create missing tables and add columns that older databases don't have yet."""
    Base.metadata.create_all(bind=engine)
    columns = {c["name"] for c in inspect(engine).get_columns("rants")}
    if "kind" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE rants ADD COLUMN kind VARCHAR(12) NOT NULL DEFAULT 'rant'"))