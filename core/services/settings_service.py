from __future__ import annotations
import sqlite3
from typing import Optional


def get_settings(conn: sqlite3.Connection):
    row = conn.execute("SELECT * FROM app_settings ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        # Create default
        conn.execute("INSERT INTO app_settings (base_currency) VALUES ('KRW')")
        row = conn.execute(
            "SELECT * FROM app_settings ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return dict(row)


def get_base_currency(conn: sqlite3.Connection) -> str:
    settings = get_settings(conn)
    return settings["base_currency"]


def set_base_currency(conn: sqlite3.Connection, currency: str) -> None:
    settings = get_settings(conn)
    conn.execute(
        "UPDATE app_settings SET base_currency = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (currency.upper(), settings["id"]),
    )


def get_av_api_key(conn: sqlite3.Connection) -> str | None:
    settings = get_settings(conn)
    return settings.get("alpha_vantage_api_key")


def set_av_api_key(conn: sqlite3.Connection, api_key: str) -> None:
    settings = get_settings(conn)
    conn.execute(
        "UPDATE app_settings SET alpha_vantage_api_key = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (api_key.strip(), settings["id"]),
    )
