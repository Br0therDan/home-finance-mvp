import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if ROOT.as_posix() not in sys.path:
    sys.path.insert(0, ROOT.as_posix())


@pytest.fixture
def conn():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Initialize schema
    schema_path = ROOT / "core" / "schema.sql"
    with open(schema_path, encoding="utf-8") as f:
        conn.executescript(f.read())

    yield conn
    conn.close()


@pytest.fixture
def session(conn):
    # For backward compatibility in tests that expect 'session' (now a connection)
    return conn


@pytest.fixture
def basic_accounts(conn):
    accounts = [
        (1100, "현금", "ASSET", None, 1, 1, 1, 0, "KRW"),
        (2100, "대출금", "LIABILITY", None, 1, 1, 1, 0, "KRW"),
        (3000, "자본", "EQUITY", None, 1, 1, 1, 0, "KRW"),
        (300101, "기초순자산(Opening Equity)", "EQUITY", 3000, 1, 1, 2, 1, "KRW"),
        (4100, "수익", "INCOME", None, 1, 1, 1, 0, "KRW"),
        (5100, "비용", "EXPENSE", None, 1, 1, 1, 0, "KRW"),
    ]

    for acc in accounts:
        conn.execute(
            """INSERT INTO accounts (id, name, type, parent_id, is_active, is_system, level, allow_posting, currency)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            acc,
        )
    conn.commit()

    # Return a map of name to ID
    cursor = conn.execute("SELECT name, id FROM accounts")
    return {row["name"]: row["id"] for row in cursor.fetchall()}
