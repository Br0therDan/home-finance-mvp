from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

APP_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "app.db"
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or APP_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path.as_posix(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def _ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version TEXT PRIMARY KEY,
          applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )


def _applied_versions(conn: sqlite3.Connection) -> set[str]:
    _ensure_migrations_table(conn)
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {r["version"] for r in rows}


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Apply SQL migrations in lexical order. Safe to call multiple times."""
    MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
    applied = _applied_versions(conn)

    migration_files = sorted([p for p in MIGRATIONS_DIR.glob("*.sql") if p.is_file()])
    for p in migration_files:
        version = p.name
        if version in applied:
            continue

        sql = p.read_text(encoding="utf-8")
        with conn:
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations(version) VALUES(?)",
                (version,),
            )


def fetch_df(conn: sqlite3.Connection, query: str, params: tuple = ()):
    import pandas as pd

    return pd.read_sql_query(query, conn, params=params)


def execute_many(conn: sqlite3.Connection, query: str, rows: Iterable[tuple]) -> None:
    with conn:
        conn.executemany(query, list(rows))
