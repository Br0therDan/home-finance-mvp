# Walkthrough: Phase 2 - Core Service Layer (Account & Ledger)

## Accomplishments
The core service layer now supports multi-currency accounts and records FX snapshots in the ledger.

### 1. Data Model Updates
- Updated `JournalLine` in `core/models.py` to include optional multi-currency fields:
    - `native_amount`: The amount in the original currency.
    - `native_currency`: The currency code (e.g., 'USD').
    - `fx_rate`: The exchange rate at the time of transaction.

### 2. Account Service Updates
- Updated `create_user_account` in `core/services/account_service.py` to support an optional `currency` parameter.
- Accounts are now correctly initialized with their respective native currency (defaults to 'KRW').

### 3. Ledger Service Updates
- Updated `create_journal_entry` in `core/services/ledger_service.py` to record FX snapshots.
- If a journal line contains native currency information, it is automatically persisted in the `journal_line_fx` table, linked to the journal line ID.
- Base amounts (debit/credit) are still maintained as the source of truth for standard accounting reports.

## Verification Results
- **Automated Tests**: Created `tests/test_multi_currency_ledger.py` which verifies:
    - Successful creation of multi-currency journal entries.
    - Correct persistence in `journal_line_fx`.
    - Proper validation of balanced entries in the base currency.
- **Ruff & Mypy**: All checks passed.
- **Git Commit**: `b6cc14d`

## Artifacts Created/Modified
- [MODIFY] [models.py](file:///Users/donghakim/home-finance-mvp/core/models.py)
- [MODIFY] [account_service.py](file:///Users/donghakim/home-finance-mvp/core/services/account_service.py)
- [MODIFY] [ledger_service.py](file:///Users/donghakim/home-finance-mvp/core/services/ledger_service.py)
- [NEW] [test_multi_currency_ledger.py](file:///Users/donghakim/home-finance-mvp/tests/test_multi_currency_ledger.py)

render_diffs(file:///Users/donghakim/home-finance-mvp/core/models.py)
render_diffs(file:///Users/donghakim/home-finance-mvp/core/services/account_service.py)
render_diffs(file:///Users/donghakim/home-finance-mvp/core/services/ledger_service.py)
