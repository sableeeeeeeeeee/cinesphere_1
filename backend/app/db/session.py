"""Engine / session setup. SQLite is a dev fallback; PostgreSQL is the target."""
from datetime import datetime, timezone

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


def utcnow() -> datetime:
    """Naive UTC 'now'. All datetimes in the DB are stored as UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_utc_naive(dt: datetime) -> datetime:
    """Accept naive (assumed UTC) or aware datetimes and return naive UTC."""
    return dt if dt.tzinfo is None else dt.astimezone(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 30})

        @event.listens_for(engine, "connect")
        def _on_connect(dbapi_conn, _):
            dbapi_conn.isolation_level = None  # we emit BEGIN ourselves
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
            dbapi_conn.execute("PRAGMA journal_mode=WAL")

        @event.listens_for(engine, "begin")
        def _on_begin(conn):
            # Take the write lock up front so concurrent writers queue instead of deadlocking.
            conn.exec_driver_sql("BEGIN IMMEDIATE")

        return engine
    return create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20)


engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
