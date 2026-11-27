from collections.abc import Generator
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from backend.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
db_url = settings.effective_database_url

connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _migrate_sessions_table() -> None:
    """Safely adds post-session polish columns to pre-existing SQLite or PostgreSQL databases."""
    inspector = inspect(engine)
    if not inspector.has_table("sessions"):
        return
    existing_cols = {col["name"] for col in inspector.get_columns("sessions")}
    migrations = [
        ("polished_transcript_md", "TEXT"),
        ("polish_status", "VARCHAR(24) DEFAULT 'idle'"),
        ("polish_provider", "VARCHAR(64)"),
    ]
    with engine.begin() as conn:
        for col_name, col_ddl in migrations:
            if col_name not in existing_cols:
                conn.execute(text(f"ALTER TABLE sessions ADD COLUMN {col_name} {col_ddl}"))


def init_db() -> None:
    # Ensure all ORM models are registered before create_all
    import backend.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_sessions_table()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
