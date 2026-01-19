# Implementation Plan: Phase 3 - Transaction UI & Exchange Rates

## Objective
Enable users to enter foreign currency transactions through the UI and manage exchange rates.

## Proposed Changes

### 1. Exchange Rate Service
#### [NEW] `core/services/fx_service.py`
- `get_latest_rate(db, base, quote) -> float`: Get most recent rate from `fx_rates` or a default.
- `save_rate(db, base, quote, rate, as_of, source)`: Cache a new rate.

### 2. Transaction UI Updates
#### [MODIFY] `pages/2_Transactions.py`
- When an account is selected, check its currency.
- If currency != `base_currency`:
    - Display "Native Amount" field.
    - Display "Exchange Rate" field (pre-filled with latest rate).
    - Automatically update `debit`/`credit` (Base Amount) as `native_amount * rate`.
- Ensure `JournalLine` objects are created with `native_amount`, `native_currency`, and `fx_rate`.

### 3. Settings UI Updates
#### [MODIFY] `pages/6_Settings.py`
- Add a "Manual Exchange Rates" section to view and update current rates (USD/KRW, etc.).

### 4. Advanced Workflow: Currency Exchange
#### [NEW] Simple "Currency Exchange" template in `pages/2_Transactions.py`:
- Dedicated UI for transferring between accounts of different currencies (e.g., KRW Account -> USD Account).

## Verification Plan
### Manual Verification
- Create a USD Account in Settings.
- Go to Transactions, select the USD Account.
- Verify that FX-related fields appear.
- Save a transaction and verify in Ledger that it shows both base and native details (can check DB).
- Verify that changing the rate updates the base amount in real-time.
