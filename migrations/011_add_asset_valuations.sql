-- migrations/011_add_asset_valuations.sql
-- Description: Add asset_valuations table for manual valuation tracking.

CREATE TABLE IF NOT EXISTS asset_valuations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    as_of_date TEXT NOT NULL,          -- YYYY-MM-DD
    value_native REAL NOT NULL,        -- Valuation amount
    currency TEXT NOT NULL,            -- e.g., KRW, USD, JPY
    note TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE,
    UNIQUE(asset_id, as_of_date)
);

CREATE INDEX IF NOT EXISTS ix_asset_valuations_asset_date ON asset_valuations(asset_id, as_of_date);
