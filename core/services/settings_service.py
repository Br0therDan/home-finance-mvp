from __future__ import annotations

import sqlite3


def get_base_currency(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT base_currency FROM app_settings WHERE id = 1").fetchone()
    if row:
        return str(row["base_currency"])
    return "KRW"


def set_base_currency(conn: sqlite3.Connection, currency: str) -> None:
    with conn:
        conn.execute(
            """
            UPDATE app_settings
            SET base_currency = ?, updated_at = datetime('now')
            WHERE id = 1
            """,
            (currency.upper(),),
        )
