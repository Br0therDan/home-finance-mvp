# Implementation Plan: Phase 2 - Core Service Layer (Account & Ledger)

## Objective
Update the core business logic to support multi-currency accounts and record FX snapshots in the ledger.

## Proposed Changes

### 1. Account Service Expansion
#### [MODIFY] `core/services/account_service.py`
- `create_user_account`: Add `currency` parameter (default: `base_currency`).
- `update_user_account`: Allow updating `currency` (only if no journal lines exist for the account).
- Add validation to ensure currency is valid (existing in `fx_rates` or a predefined list).

### 2. Ledger Service Expansion
#### [MODIFY] `core/models.py`
- `JournalLine`: Add `native_amount`, `native_currency`, `fx_rate` optional fields.

#### [MODIFY] `core/services/ledger_service.py`
- `create_journal_entry`:
    - Accept native currency details for foriegn currency lines.
    - Calculate and validate `base_amount` (debit/credit) based on `native_amount * fx_rate`.
    - Persist snapshots into `journal_line_fx` table.
- `trial_balance`: Ensure it returns balances in `base_currency` (default behavior remains).

### 3. Verification Plan
#### Automated Tests
- [NEW] `tests/test_multi_currency_ledger.py`:
    - Test balanced entry with foreign currency lines.
    - Test validation failures (unbalanced base amounts, mismatched native calculations).
    - Test account currency isolation.

## Verification Checklist
- [ ] `Account` creation with `USD` works.
- [ ] `Journal Entry` with a `USD` line correctly populates `journal_line_fx`.
- [ ] `Ruff` & `Mypy` clean.
