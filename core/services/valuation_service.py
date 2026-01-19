from __future__ import annotations
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict
from core.db import get_connection


class ValuationService:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self._conn = conn or get_connection()

    def upsert_asset_valuation(
        self,
        asset_id: int,
        as_of_date: str,
        value_native: float,
        currency: str,
        note: Optional[str] = None,
    ) -> int:
        now = datetime.now().isoformat()
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO asset_valuations (
                    asset_id, as_of_date, value_native, currency, note, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(asset_id, as_of_date) DO UPDATE SET
                    value_native = excluded.value_native,
                    currency = excluded.currency,
                    note = excluded.note,
                    updated_at = excluded.updated_at
                """,
                (
                    asset_id,
                    as_of_date,
                    float(value_native),
                    currency.upper(),
                    note,
                    now,
                ),
            )
            return int(cur.lastrowid) if cur.lastrowid else -1

    def get_latest_valuation(self, asset_id: int) -> Optional[dict]:
        row = self._conn.execute(
            """
            SELECT * FROM asset_valuations 
            WHERE asset_id = ? 
            ORDER BY as_of_date DESC, updated_at DESC 
            LIMIT 1
            """,
            (asset_id,),
        ).fetchone()
        return dict(row) if row else None

    def list_latest_valuations(self) -> List[dict]:
        """Returns the latest valuation for each asset."""
        rows = self._conn.execute(
            """
            SELECT v.*, a.name as asset_name
            FROM asset_valuations v
            JOIN assets a ON a.id = v.asset_id
            WHERE v.id IN (
                SELECT id FROM asset_valuations
                GROUP BY asset_id
                HAVING MAX(as_of_date)
            )
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def get_valuations_for_dashboard(self) -> Dict[int, dict]:
        """Returns a mapping of asset_id -> latest valuation dict."""
        latest = self.list_latest_valuations()
        return {r["asset_id"]: r for r in latest}
