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


def run_migrations():
    """Run Alembic migrations programmatically."""
    from alembic import command
    from alembic.config import Config

    alembic_ini = BASE_DIR / "alembic.ini"
    if not alembic_ini.exists():
        print(f"Warning: alembic.ini not found at {alembic_ini}")
        return

    # Alembic Config object needs the absolute path to alembic.ini
    alembic_cfg = Config(str(alembic_ini))
    # We also need to set the script location relative to the ini location or absolute
    # In alembic.ini it says script_location = %(here)s/alembic
    # Setting the config main option 'script_location' to absolute path helps
    alembic_cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))

    # We also need to set sqlalchemy.url to ensure it uses the correct DB path
    # even if CWD is different (though usually CWD is root)
    alembic_cfg.set_main_option("sqlalchemy.url", str(DATABASE_URL))

    command.upgrade(alembic_cfg, "head")
