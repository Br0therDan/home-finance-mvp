# Walkthrough: Phase 4 - Reports & Dashboard

## Accomplishments
Phase 4 focused on providing visibility into multi-currency holdings, comparing "Book Value" (historical cost) with "Current Value" (market value), and supporting the global "Display Currency" across all reports.

### 1. Multi-Currency Balance Calculation
- Enhanced `ledger_service.py` with `account_balances_multi`:
    - This function calculates both the base currency balance (KRW) and the native currency balance (USD, JPY, etc.) for every account by joining the `journal_line_fx` table.
- Updated `balance_sheet` to:
    - Automatically convert native balances to the "Base Currency" (KRW) using current rates to show **Current Value**.
    - Compare this against the **Book Value** (the actual KRW recorded at the time of transaction).
    - Convert all final balances to the user's selected **Display Currency** (sidebar setting).

### 2. Dashboard Enhancements
- Updated `pages/1_Dashboard.py`:
    - Key metrics (Total Assets, Net Worth) now reflect the selected Display Currency.
    - Added an expander to show the "Book Value" in KRW for reference.
    - The BS summary table now includes columns for: Native Balance, Display Value (current), and Book Value (base).

### 3. Financial Reports Updates
- Updated `pages/5_Reports.py`:
    - The Balance Sheet now supports the Display Currency setting.
    - Simplified the BS views to focus on evaluation values in the selected currency.
- Updated `core/ui/formatting.py`:
    - Added a generic `fmt(value, currency)` function that handles symbols and decimal places for KRW, USD, JPY, and EUR.

## Verification Results
- **Scenario Testing**:
    - Entered a transaction at 1,300 USD/KRW.
    - Updated market rate to 1,400 USD/KRW in Settings.
    - Verified that Dashboard shows the higher "Current Value" while the "Book Value" remains 1,300.
    - Switched sidebar to "USD" and verified that all totals are correctly converted back to USD at current rates.
- **Ruff & Mypy**: All checks passing.
- **Git Commit**: `097b65b`

## Artifacts Created/Modified
- [MODIFY] [ledger_service.py](file:///Users/donghakim/home-finance-mvp/core/services/ledger_service.py)
- [MODIFY] [1_Dashboard.py](file:///Users/donghakim/home-finance-mvp/pages/1_Dashboard.py)
- [MODIFY] [5_Reports.py](file:///Users/donghakim/home-finance-mvp/pages/5_Reports.py)
- [MODIFY] [formatting.py](file:///Users/donghakim/home-finance-mvp/core/ui/formatting.py)
