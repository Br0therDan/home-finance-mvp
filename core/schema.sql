-- Household Finance & Asset Management Master Schema

-- System Settings
CREATE TABLE IF NOT EXISTS app_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    base_currency TEXT NOT NULL DEFAULT 'KRW',
    alpha_vantage_api_key TEXT,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Foreign Exchange Rates
CREATE TABLE IF NOT EXISTS fx_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    base_currency TEXT NOT NULL,
    quote_currency TEXT NOT NULL,
    rate REAL NOT NULL,
    as_of DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_fx_rates_base_quote ON fx_rates (base_currency, quote_currency);
CREATE INDEX IF NOT EXISTS ix_fx_rates_as_of ON fx_rates (as_of);

-- Chart of Accounts
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL, -- ASSET, LIABILITY, EQUITY, INCOME, EXPENSE
    name TEXT NOT NULL,
    parent_id INTEGER,
    level INTEGER NOT NULL DEFAULT 1,
    is_active INTEGER NOT NULL DEFAULT 1,
    is_system INTEGER NOT NULL DEFAULT 0,
    allow_posting INTEGER NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'KRW',
    description TEXT,
    account_number TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES accounts (id)
);
CREATE INDEX IF NOT EXISTS ix_accounts_type ON accounts (type);

-- Journal
CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date DATE NOT NULL,
    description TEXT NOT NULL,
    source TEXT NOT NULL, -- manual, purchase, loan_payment, subscription
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_journal_entries_date ON journal_entries (entry_date);

CREATE TABLE IF NOT EXISTS journal_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    debit REAL NOT NULL DEFAULT 0.0,
    credit REAL NOT NULL DEFAULT 0.0,
    memo TEXT NOT NULL,
    native_amount REAL,
    native_currency TEXT,
    fx_rate REAL,
    FOREIGN KEY (entry_id) REFERENCES journal_entries (id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts (id)
);
CREATE INDEX IF NOT EXISTS ix_journal_lines_entry_id ON journal_lines (entry_id);
CREATE INDEX IF NOT EXISTS ix_journal_lines_account_id ON journal_lines (account_id);

-- Assets
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    asset_class TEXT NOT NULL, -- 상세분류
    asset_type TEXT NOT NULL DEFAULT 'OTHER', -- SECURITY, REAL_ESTATE, VEHICLE, OTHER
    linked_account_id INTEGER NOT NULL,
    acquisition_date DATE NOT NULL,
    acquisition_cost REAL NOT NULL,
    disposal_date DATE,
    depreciation_method TEXT NOT NULL DEFAULT 'NONE',
    useful_life_years INTEGER,
    salvage_value REAL NOT NULL DEFAULT 0.0,
    note TEXT NOT NULL,
    FOREIGN KEY (linked_account_id) REFERENCES accounts (id)
);

CREATE TABLE IF NOT EXISTS asset_valuations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    as_of_date DATE NOT NULL,
    value_native REAL NOT NULL,
    currency TEXT NOT NULL,
    method TEXT NOT NULL DEFAULT 'market',
    note TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    fx_rate REAL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets (id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_asset_valuations_asset_date ON asset_valuations (asset_id, as_of_date);

CREATE TABLE IF NOT EXISTS investment_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL UNIQUE,
    ticker TEXT NOT NULL,
    exchange TEXT,
    trading_currency TEXT NOT NULL,
    security_type TEXT,
    isin TEXT,
    broker TEXT,
    FOREIGN KEY (asset_id) REFERENCES assets (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS real_estate_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL UNIQUE,
    address TEXT NOT NULL,
    property_type TEXT NOT NULL, -- APARTMENT, VILLA, OFFICE, LAND, etc.
    area_sqm REAL,
    exclusive_area_sqm REAL,
    floor INTEGER,
    total_floors INTEGER,
    completion_date DATE,
    FOREIGN KEY (asset_id) REFERENCES assets (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS investment_lots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    lot_date DATE NOT NULL,
    quantity REAL NOT NULL,
    remaining_quantity REAL NOT NULL,
    unit_price_native REAL NOT NULL,
    fees_native REAL NOT NULL DEFAULT 0.0,
    currency TEXT NOT NULL,
    fx_rate REAL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS investment_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    event_type TEXT NOT NULL, -- BUY, SELL, DIVIDEND, SPLIT
    event_date DATE NOT NULL,
    quantity REAL,
    price_per_unit_native REAL,
    gross_amount_native REAL,
    fees_native REAL NOT NULL DEFAULT 0.0,
    currency TEXT NOT NULL,
    fx_rate REAL,
    cash_account_id INTEGER,
    income_account_id INTEGER,
    fee_account_id INTEGER,
    journal_entry_id INTEGER,
    note TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets (id) ON DELETE CASCADE,
    FOREIGN KEY (cash_account_id) REFERENCES accounts (id),
    FOREIGN KEY (income_account_id) REFERENCES accounts (id),
    FOREIGN KEY (fee_account_id) REFERENCES accounts (id),
    FOREIGN KEY (journal_entry_id) REFERENCES journal_entries (id)
);

-- Subscriptions / Recurring
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cadence TEXT NOT NULL, -- MONTHLY, YEARLY, etc.
    interval INTEGER NOT NULL DEFAULT 1,
    next_due_date DATE NOT NULL,
    amount REAL NOT NULL,
    debit_account_id INTEGER NOT NULL,
    credit_account_id INTEGER NOT NULL,
    memo TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    auto_create_journal INTEGER NOT NULL DEFAULT 0,
    last_run_date DATE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (debit_account_id) REFERENCES accounts (id),
    FOREIGN KEY (credit_account_id) REFERENCES accounts (id)
);

-- Loans
CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    asset_id INTEGER,
    liability_account_id INTEGER NOT NULL,
    principal_amount REAL NOT NULL,
    interest_rate REAL NOT NULL,
    term_months INTEGER NOT NULL,
    start_date DATE NOT NULL,
    repayment_method TEXT NOT NULL DEFAULT 'AMORTIZATION',
    payment_day INTEGER NOT NULL DEFAULT 1,
    grace_period_months INTEGER NOT NULL DEFAULT 0,
    note TEXT NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets (id),
    FOREIGN KEY (liability_account_id) REFERENCES accounts (id)
);

CREATE TABLE IF NOT EXISTS loan_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_id INTEGER NOT NULL,
    due_date DATE NOT NULL,
    installment_number INTEGER NOT NULL,
    principal_payment REAL NOT NULL,
    interest_payment REAL NOT NULL,
    total_payment REAL NOT NULL,
    remaining_balance REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, PAID
    journal_entry_id INTEGER,
    FOREIGN KEY (loan_id) REFERENCES loans (id) ON DELETE CASCADE,
    FOREIGN KEY (journal_entry_id) REFERENCES journal_entries (id)
);
CREATE INDEX IF NOT EXISTS ix_loan_schedules_loan_due ON loan_schedules (loan_id, due_date);

-- Evidences
CREATE TABLE IF NOT EXISTS evidences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER,
    loan_id INTEGER,
    file_path TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES assets (id),
    FOREIGN KEY (loan_id) REFERENCES loans (id)
);
