# Implementation Plan: Phase 4 - Reports & Dashboard

## Objective
Update the reporting layer to display "Book Value" (based on transaction-time FX) and "Current Value" (based on current market rates), while supporting the session-selected `display_currency`.

## Proposed Changes

### 1. Report Service Updates
#### [MODIFY] `core/services/report_service.py` (or `ledger_service.py` if used for reports)
- `account_balances_multi_currency(conn, as_of, quote_currency)`:
    - Return a list/dict of accounts with:
        - `base_balance` (Book value in KRW)
        - `native_balance` (Cumulative balance in account's native currency)
        - `current_value` (native_balance converted to `quote_currency` using current rates)

### 2. Dashboard Updates
#### [MODIFY] `pages/1_Dashboard.py`
- Display "Net Worth" in both `base_currency` (KRW) and the sidebar-selected `display_currency`.
- Show a table of multi-currency assets with their Book Value vs. Current Value (Mark-to-Market).

### 3. Financial Reports (BS/IS)
#### [MODIFY] `pages/5_Reports.py`
- Update Balance Sheet to support display in the selected `display_currency`.
- Add a footnote or column explaining the "Book Value" basis for historical cost reporting.

## Verification Plan
### Manual Verification
- Select `USD` in the sidebar.
- Verify that the Dashboard "Total Assets" is converted to USD using the latest rate.
- Compare "Book Value" (KRW total from all transactions) vs "Current Value" (calculated from current spot rate * native balance).
- Ensure BS totals balance even when converted (using a single point-in-time rate for display).
