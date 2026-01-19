# Implementation Plan: Phase 1 - Foundation (Setting & DB Schema)

## Objective
Set up the database structure for multi-currency support and implement global currency settings (Base/Display).

## Proposed Changes

### 1. Database Migrations
#### [NEW] `migrations/007_multi_currency_foundation.sql`
- `app_settings` (id, key, value, updated_at): Store `base_currency`.
- `accounts` (ALTER): Add `currency` column (TEXT, default 'KRW').
- `journal_line_fx` (id, line_id, native_currency, native_amount, base_currency, fx_rate, base_amount, rate_source, quoted_at): Store FX snapshots.
- `fx_rates` (id, base_currency, quote_currency, rate, as_of, source): Store current/historical rates.

### 2. UI Updates
#### [MODIFY] `app.py`
- Add `display_currency` selectbox to `st.sidebar`.
- Default to `base_currency` from `app_settings`.

#### [MODIFY] `pages/6_Settings.py`
- Add "Global Settings" section.
- Allow users to set/update `base_currency`.

### 3. Service Layer
#### [NEW] `core/services/settings_service.py`
- `get_base_currency(conn) -> str`
- `set_base_currency(conn, currency: str)`

## Verification Plan

### Automated Tests
- `pytest` to check schema existence after migration.
- `pytest` to check settings CRUD.

### Manual Verification
- Run app and check if `base_currency` can be updated in Settings.
- Check if Sidebar shows `display_currency` selector.
- Inspect `data/app.db` using SQLite CLI to verify table structure.
