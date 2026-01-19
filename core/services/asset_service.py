from __future__ import annotations

import sqlite3
from datetime import date


def create_asset(
    conn: sqlite3.Connection,
    name: str,
    asset_class: str,
    linked_account_id: int,
    acquisition_date: date,
    acquisition_cost: float,
    note: str = "",
) -> int:
    with conn:
        cur = conn.execute(
            """
            INSERT INTO assets(name, asset_class, linked_account_id, acquisition_date, acquisition_cost, note)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                asset_class,
                linked_account_id,
                acquisition_date.isoformat(),
                float(acquisition_cost),
                note,
            ),
        )
        return int(cur.lastrowid)


def list_assets(conn: sqlite3.Connection):
    return conn.execute(
        """
        SELECT a.id, a.name, a.asset_class, a.acquisition_date, a.acquisition_cost,
               a.linked_account_id, a.note,
               acc.name AS linked_account
        FROM assets a
        JOIN accounts acc ON acc.id = a.linked_account_id
        WHERE a.disposal_date IS NULL
        ORDER BY a.acquisition_date DESC, a.id DESC
        """
    ).fetchall()


def update_asset(
    conn: sqlite3.Connection,
    asset_id: int,
    name: str,
    asset_class: str,
    linked_account_id: int,
    acquisition_date: date,
    acquisition_cost: float,
    note: str,
) -> None:
    with conn:
        conn.execute(
            """
            UPDATE assets
            SET name = ?, asset_class = ?, linked_account_id = ?, 
                acquisition_date = ?, acquisition_cost = ?, note = ?
            WHERE id = ?
            """,
            (
                name.strip(),
                asset_class,
                int(linked_account_id),
                acquisition_date.isoformat(),
                float(acquisition_cost),
                note,
                int(asset_id),
            ),
        )


def delete_asset(conn: sqlite3.Connection, asset_id: int) -> None:
    with conn:
        # Note: valuation records have ON DELETE CASCADE in the schema
        conn.execute("DELETE FROM assets WHERE id = ?", (int(asset_id),))


def add_valuation(
    conn: sqlite3.Connection,
    asset_id: int,
    v_date: date,
    value: float,
    method: str = "manual",
) -> int:
    with conn:
        cur = conn.execute(
            """
            INSERT INTO valuations(asset_id, valuation_date, value, method)
            VALUES (?, ?, ?, ?)
            """,
            (asset_id, v_date.isoformat(), float(value), method),
        )
        return int(cur.lastrowid)


def latest_valuation(conn: sqlite3.Connection, asset_id: int):
    return conn.execute(
        """
        SELECT valuation_date, value, method
        FROM valuations
        WHERE asset_id = ?
        ORDER BY valuation_date DESC, id DESC
        LIMIT 1
        """,
        (asset_id,),
    ).fetchone()


def valuation_history(conn: sqlite3.Connection, asset_id: int):
    return conn.execute(
        """
        SELECT valuation_date, value, method
        FROM valuations
        WHERE asset_id=?
        ORDER BY valuation_date DESC, id DESC
        """,
        (asset_id,),
    ).fetchall()
