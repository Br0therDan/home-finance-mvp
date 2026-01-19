from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

# DB Path Configuration
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "app.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Engine with Echo for debugging (optional)
engine = create_engine(DATABASE_URL, echo=False)


def get_session():
    """Dependency for getting a SQLModel Session."""
    with Session(engine) as session:
        yield session


def init_db():
    """Create tables (useful for dev/testing, but Alembic is preferred)."""
    SQLModel.metadata.create_all(engine)
