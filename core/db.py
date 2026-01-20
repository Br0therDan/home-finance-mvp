import sqlite3
from pathlib import Path

# DB Path Configuration
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "app.db"
SCHEMA_PATH = BASE_DIR / "core" / "schema.sql"


def get_connection():
    """Return a raw sqlite3 connection with dict factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


class Session:
    """A minimal wrapper to maintain 'with Session(engine) as session' usage,
    but adapting it to raw connection for less refactoring in business logic."""

    def __init__(self, engine=None):
        self.conn = get_connection()

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.conn.close()

    @staticmethod
    def exec(conn, statement):
        # Placeholder to help with refactoring transition
        pass


# Global engine placeholder for compatibility
engine = None


def init_db():
    """Initialize the database using the schema.sql file."""
    if not DB_PATH.parent.exists():
        DB_PATH.parent.mkdir(parents=True)

    with get_connection() as conn:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
