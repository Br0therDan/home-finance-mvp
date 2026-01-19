-- migrations/010_market_data.sql
-- Description: Add market data cache tables (market prices) and sync logs.
-- NOTE: fx_rates is already created in 007_multi_currency_foundation.sql

-- 1) market_prices (가격 캐시)
CREATE TABLE IF NOT EXISTS market_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,          -- 예: AAPL
    market TEXT NOT NULL,          -- 예: "US", "KR"
    currency TEXT NOT NULL,        -- 예: USD
    price REAL NOT NULL,
    as_of TEXT NOT NULL,
    source TEXT NOT NULL,          -- 예: "alphavantage"
    UNIQUE(symbol, market, as_of, source)
);

-- 2) data_sync_log (동기화 로그)
CREATE TABLE IF NOT EXISTS data_sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_type TEXT NOT NULL,       -- "fx" / "price"
    provider TEXT NOT NULL,
    status TEXT NOT NULL,          -- "success" / "failed"
    message TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT
);

