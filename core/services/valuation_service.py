from __future__ import annotations
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

from core.services.market_data_service import AlphaVantageService


def upsert_asset_valuation(
    conn: sqlite3.Connection,
    asset_id: int,
    as_of_date: str,
    value_native: float,
    currency: str,
    note: str | None = None,
    source: str = "manual",
) -> int:
    # Check if exists
    row = conn.execute(
        "SELECT id FROM asset_valuations WHERE asset_id = ? AND as_of_date = ?",
        (asset_id, as_of_date),
    ).fetchone()

    if row:
        conn.execute(
            """UPDATE asset_valuations SET value_native = ?, currency = ?, note = ?, source = ?, updated_at = CURRENT_TIMESTAMP 
               WHERE id = ?""",
            (float(value_native), currency.upper(), note, source, row["id"]),
        )
        return row["id"]
    else:
        cursor = conn.execute(
            """INSERT INTO asset_valuations (asset_id, as_of_date, value_native, currency, note, source) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (asset_id, as_of_date, float(value_native), currency.upper(), note, source),
        )
        return cursor.lastrowid


def get_valuation_history(conn: sqlite3.Connection, asset_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM asset_valuations WHERE asset_id = ? ORDER BY as_of_date DESC, updated_at DESC",
        (asset_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def list_latest_valuations(conn: sqlite3.Connection) -> list[dict]:
    sql = """
        SELECT v.*, a.name as asset_name
        FROM asset_valuations v
        JOIN assets a ON a.id = v.asset_id
        WHERE v.id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (PARTITION BY asset_id ORDER BY as_of_date DESC, id DESC) as rn
                FROM asset_valuations
            ) WHERE rn = 1
        )
    """
    rows = conn.execute(sql).fetchall()
    return [dict(r) for r in rows]


def get_valuations_for_dashboard(conn: sqlite3.Connection) -> dict[int, dict]:
    latest = list_latest_valuations(conn)
    return {r["asset_id"]: r for r in latest}


def update_market_valuations(conn: sqlite3.Connection) -> dict[int, float]:
    """Update valuations for all SECURITY assets using market data."""
    av_service = AlphaVantageService()

    # Find assets with investment profiles (tickers)
    sql = """
        SELECT a.id, p.ticker, p.trading_currency
        FROM assets a
        JOIN investment_profiles p ON p.asset_id = a.id
        WHERE a.asset_type = 'SECURITY'
    """
    security_assets = conn.execute(sql).fetchall()

    results = {}
    for row in security_assets:
        asset_id = row["id"]
        ticker = row["ticker"]
        if not ticker:
            continue

        market_data = av_service.get_latest_price(ticker)
        if market_data:
            # Need total quantity to store TOTAL value in valuation
            qty_row = conn.execute(
                "SELECT SUM(remaining_quantity) FROM investment_lots WHERE asset_id = ?",
                (asset_id,),
            ).fetchone()
            total_qty = float(qty_row[0] or 0.0)
            total_value = market_data["price"] * total_qty

            upsert_asset_valuation(
                conn=conn,
                asset_id=asset_id,
                as_of_date=market_data["as_of_date"],
                value_native=total_value,
                currency=market_data["currency"],
                note=f"Auto-updated from Alpha Vantage (Ticker: {ticker}, Qty: {total_qty})",
                source="alpha_vantage",
            )
            results[asset_id] = total_value

    return results
