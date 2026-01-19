-- Migration: 007_multi_currency_foundation.sql
-- Goal: Set up tables for multi-currency support

-- 1. App Settings table
CREATE TABLE IF NOT EXISTS app_settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    base_currency TEXT NOT NULL DEFAULT 'KRW',
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (id = 1) -- Ensure only one row exists for global settings
);

-- Insert default row if not exists
INSERT OR IGNORE INTO app_settings (id, base_currency) VALUES (1, 'KRW');

-- 2. Expand accounts table with currency
ALTER TABLE accounts ADD COLUMN currency TEXT NOT NULL DEFAULT 'KRW';

-- 3. Journal Line FX table (FX Snapshots)
CREATE TABLE IF NOT EXISTS journal_line_fx (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    line_id INTEGER NOT NULL UNIQUE,
    native_currency TEXT NOT NULL,
    native_amount REAL NOT NULL,
    base_currency TEXT NOT NULL,
    fx_rate REAL NOT NULL,
    base_amount REAL NOT NULL,
    rate_source TEXT NOT NULL DEFAULT 'manual',
    quoted_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (line_id) REFERENCES journal_lines(id) ON DELETE CASCADE
);

-- 4. FX Rates table (Historical/Current cache)
CREATE TABLE IF NOT EXISTS fx_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    base_currency TEXT NOT NULL,
    quote_currency TEXT NOT NULL,
    rate REAL NOT NULL,
    as_of TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(base_currency, quote_currency, as_of)
);
