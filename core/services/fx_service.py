from __future__ import annotations

import sqlite3
from datetime import datetime


def get_latest_rate(conn: sqlite3.Connection, base: str, quote: str) -> float:
    """Get the latest exchange rate for base per 1 quote."""
    if base == quote:
        return 1.0

    row = conn.execute(
        """
        SELECT rate FROM fx_rates
        WHERE base_currency = ? AND quote_currency = ?
        ORDER BY as_of DESC, created_at DESC
        LIMIT 1
        """,
        (base.upper(), quote.upper()),
    ).fetchone()

    if row:
        return float(row["rate"])

    # Fallback/Default rates if not found in DB
    defaults = {
        ("KRW", "USD"): 1350.0,
        ("KRW", "JPY"): 9.0,
        ("KRW", "EUR"): 1450.0,
    }
    return defaults.get((base.upper(), quote.upper()), 1.0)


def save_rate(
    conn: sqlite3.Connection,
    base: str,
    quote: str,
    rate: float,
    as_of: str | None = None,
    source: str = "manual",
) -> None:
    if not as_of:
        as_of = datetime.now().strftime("%Y-%m-%d")

    with conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO fx_rates (base_currency, quote_currency, rate, as_of, source)
            VALUES (?, ?, ?, ?, ?)
            """,
            (base.upper(), quote.upper(), rate, as_of, source),
        )
