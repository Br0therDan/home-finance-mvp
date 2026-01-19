from __future__ import annotations
from datetime import datetime
from typing import List, Optional, Dict, Type
import sqlite3
from core.db import get_connection
from core.integrations.interfaces import PriceProvider, FXProvider, PriceQuote, FxRate
from core.integrations.providers.alphavantage_price_provider import (
    AlphaVantagePriceProvider,
)
from core.integrations.providers.fx_providers import ManualFXProvider


class MarketDataService:
    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self._conn = conn or get_connection()
        self._price_providers: Dict[str, PriceProvider] = {
            "alphavantage": AlphaVantagePriceProvider()
        }
        self._fx_providers: Dict[str, FXProvider] = {"manual": ManualFXProvider()}

    def sync_prices(
        self, symbols: List[str], market: str, provider_name: str = "alphavantage"
    ):
        provider = self._price_providers.get(provider_name)
        if not provider:
            raise ValueError(f"Unknown price provider: {provider_name}")

        started_at = datetime.now().isoformat()
        log_id = self._log_sync_start("price", provider_name, started_at)

        try:
            quotes = provider.get_latest_prices(symbols, market)
            self._upsert_market_prices(quotes)
            self._log_sync_finish(log_id, "success", f"Synced {len(quotes)} symbols.")
        except Exception as e:
            self._log_sync_finish(log_id, "failed", str(e))
            raise e

    def save_manual_fx_rate(self, base: str, quote: str, rate: float, as_of: str):
        started_at = datetime.now().isoformat()
        log_id = self._log_sync_start("fx", "manual", started_at)

        try:
            fx_rate = FxRate(
                base_currency=base,
                quote_currency=quote,
                rate=rate,
                as_of=as_of,
                source="manual",
            )
            self._upsert_fx_rates([fx_rate])
            self._log_sync_finish(
                log_id, "success", f"Saved manual FX: {base}/{quote} = {rate}"
            )
        except Exception as e:
            self._log_sync_finish(log_id, "failed", str(e))
            raise e

    def get_latest_price(self, symbol: str, market: str) -> Optional[dict]:
        row = self._conn.execute(
            """
            SELECT * FROM market_prices 
            WHERE symbol = ? AND market = ? 
            ORDER BY as_of DESC LIMIT 1
            """,
            (symbol, market),
        ).fetchone()
        return dict(row) if row else None

    def get_latest_fx(self, base: str, quote: str) -> Optional[dict]:
        row = self._conn.execute(
            """
            SELECT * FROM fx_rates 
            WHERE base_currency = ? AND quote_currency = ? 
            ORDER BY as_of DESC LIMIT 1
            """,
            (base, quote),
        ).fetchone()
        return dict(row) if row else None

    def get_last_sync_log(self, data_type: str) -> Optional[dict]:
        row = self._conn.execute(
            """
            SELECT * FROM data_sync_log 
            WHERE data_type = ? 
            ORDER BY started_at DESC LIMIT 1
            """,
            (data_type,),
        ).fetchone()
        return dict(row) if row else None

    def _upsert_market_prices(self, quotes: List[PriceQuote]):
        with self._conn:
            for q in quotes:
                self._conn.execute(
                    """
                    INSERT INTO market_prices (symbol, market, currency, price, as_of, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol, market, as_of, source) DO UPDATE SET
                        price = excluded.price,
                        currency = excluded.currency
                    """,
                    (q.symbol, q.market, q.currency, q.price, q.as_of, q.source),
                )

    def _upsert_fx_rates(self, rates: List[FxRate]):
        with self._conn:
            for r in rates:
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO fx_rates (base_currency, quote_currency, rate, as_of, source)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        r.base_currency.upper(),
                        r.quote_currency.upper(),
                        r.rate,
                        r.as_of,
                        r.source,
                    ),
                )

    def _log_sync_start(self, data_type: str, provider: str, started_at: str) -> int:
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO data_sync_log (data_type, provider, status, started_at)
                VALUES (?, ?, ?, ?)
                """,
                (data_type, provider, "running", started_at),
            )
            return cursor.lastrowid

    def _log_sync_finish(self, log_id: int, status: str, message: str):
        with self._conn:
            self._conn.execute(
                """
                UPDATE data_sync_log 
                SET status = ?, message = ?, finished_at = ?
                WHERE id = ?
                """,
                (status, message, datetime.now().isoformat(), log_id),
            )
