from __future__ import annotations
import sqlite3
from datetime import datetime
from typing import Optional


def get_latest_rate(
    conn: sqlite3.Connection, base_cur: str, target_cur: str
) -> float | None:
    if base_cur == target_cur:
        return 1.0

    row = conn.execute(
        "SELECT rate FROM fx_rates WHERE base_currency = ? AND quote_currency = ? ORDER BY as_of DESC, id DESC LIMIT 1",
        (base_cur, target_cur),
    ).fetchone()
    return float(row["rate"]) if row else None


def save_rate(
    conn: sqlite3.Connection,
    base: str,
    quote: str,
    rate: float,
    as_of: datetime | None = None,
) -> None:
    timestamp = as_of or datetime.now()
    timestamp_str = (
        timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp
    )

    # Check if exists
    if as_of is None:
        query = "SELECT id FROM fx_rates WHERE base_currency = ? AND quote_currency = ? ORDER BY as_of DESC, id DESC LIMIT 1"
        params = (base, quote)
    else:
        query = "SELECT id FROM fx_rates WHERE base_currency = ? AND quote_currency = ? AND as_of = ?"
        params = (base, quote, timestamp_str)

    row = conn.execute(query, params).fetchone()

    if row:
        conn.execute(
            "UPDATE fx_rates SET rate = ?, as_of = ? WHERE id = ?",
            (rate, timestamp_str, row["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO fx_rates (base_currency, quote_currency, rate, as_of) VALUES (?, ?, ?, ?)",
            (base, quote, rate, timestamp_str),
        )
