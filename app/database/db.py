from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _migrate_db():
    """Apply any necessary schema migrations."""
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE recipes ADD COLUMN external_status TEXT NOT NULL DEFAULT 'unknown'"))
            conn.commit()
        except Exception:
            pass  # Column already exists or other error


def init_db():
    """Initialize database tables and apply migrations."""
    Base.metadata.create_all(bind=engine)
    _migrate_db()


def get_session():
    """Get a new database session."""
    return SessionLocal()
