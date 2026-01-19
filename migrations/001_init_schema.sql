-- 001_init_schema.sql

CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('ASSET','LIABILITY','EQUITY','INCOME','EXPENSE')),
  parent_id INTEGER NULL REFERENCES accounts(id) ON DELETE SET NULL,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_accounts_name_type ON accounts(name, type);

CREATE TABLE IF NOT EXISTS journal_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entry_date TEXT NOT NULL, -- ISO date
  description TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'manual',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS ix_journal_entries_date ON journal_entries(entry_date);

CREATE TABLE IF NOT EXISTS journal_lines (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entry_id INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
  account_id INTEGER NOT NULL REFERENCES accounts(id),
  debit REAL NOT NULL DEFAULT 0 CHECK (debit >= 0),
  credit REAL NOT NULL DEFAULT 0 CHECK (credit >= 0),
  memo TEXT NOT NULL DEFAULT '',
  CHECK (NOT (debit > 0 AND credit > 0)),
  CHECK (debit > 0 OR credit > 0)
);

CREATE INDEX IF NOT EXISTS ix_journal_lines_entry_id ON journal_lines(entry_id);
CREATE INDEX IF NOT EXISTS ix_journal_lines_account_id ON journal_lines(account_id);

CREATE TABLE IF NOT EXISTS assets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  asset_class TEXT NOT NULL,
  linked_account_id INTEGER NOT NULL REFERENCES accounts(id),
  acquisition_date TEXT NOT NULL,
  acquisition_cost REAL NOT NULL DEFAULT 0 CHECK (acquisition_cost >= 0),
  disposal_date TEXT NULL,
  note TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS ix_assets_class ON assets(asset_class);

CREATE TABLE IF NOT EXISTS valuations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
  valuation_date TEXT NOT NULL,
  value REAL NOT NULL CHECK (value >= 0),
  method TEXT NOT NULL DEFAULT 'manual'
);

CREATE INDEX IF NOT EXISTS ix_valuations_asset_date ON valuations(asset_id, valuation_date);
