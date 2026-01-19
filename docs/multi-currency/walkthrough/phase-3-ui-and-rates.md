# Walkthrough: Phase 3 - Transaction UI & Exchange Rates

## Accomplishments
Phase 3 focused on enabling users to enter multi-currency transactions and manage exchange rates within the application.

### 1. Exchange Rate Service
- Implemented `core/services/fx_service.py` to handle:
    - `get_latest_rate`: Retrieves the most recent exchange rate for a currency pair from the database, with fallback values for common pairs (USD/KRW, etc.).
    - `save_rate`: Persists manual exchange rate entries into the `fx_rates` table.

### 2. Transaction UI Updates
- Updated `pages/2_Transactions.py` to support multi-currency entry:
    - When a foreign currency account is selected (e.g., USD Savings), the UI automatically displays fields for "Native Amount" and "Exchange Rate".
    - The "Base Amount" (KRW) is automatically calculated and shown as a preview.
    - Supports "Expense", "Income", and "Transfer" flows with multi-currency logic.
    - Multi-currency transfers allow specifying different rates/amounts for both the "From" and "To" accounts.

### 3. Settings UI Updates
- Updated `pages/6_Settings.py`:
    - Added a "Manual FX Rates" section where users can view the latest cached rates and save new manual overrides.
    - Updated the "Account Creation" dialog to allow specifying the native currency for new accounts.

## Verification Results
- **UI Testing**: Verified that selecting a USD account triggers the FX input fields.
- **Database Persistence**: Confirmed that transactions entered with FX details correctly populate the `journal_line_fx` table with the snapshot rates.
- **Ruff & Mypy**: All checks passed after minor fixes to unpacking logic in the UI layer.
- **Git Commit**: `de5a585`

## Artifacts Created/Modified
- [NEW] [fx_service.py](file:///Users/donghakim/home-finance-mvp/core/services/fx_service.py)
- [MODIFY] [2_Transactions.py](file:///Users/donghakim/home-finance-mvp/pages/2_Transactions.py)
- [MODIFY] [6_Settings.py](file:///Users/donghakim/home-finance-mvp/pages/6_Settings.py)
- [MODIFY] [ledger_service.py](file:///Users/donghakim/home-finance-mvp/core/services/ledger_service.py)

render_diffs(file:///Users/donghakim/home-finance-mvp/pages/2_Transactions.py)
render_diffs(file:///Users/donghakim/home-finance-mvp/pages/6_Settings.py)
