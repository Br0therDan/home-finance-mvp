# Implementation Plan - Multi-currency (Physical Implementation)

## Executive Summary
Introduce multi-currency support (KRW/USD) to the home-finance-mvp project. Transactions will be recorded using "FX Snapshots" (fixed exchange rates at the time of transaction) in the ledger, while providing "Current Value" reports based on live market rates in the presentation layer.

## Objectives
- Support multiple currencies for accounts (specifically L2 asset accounts).
- Maintain "Single Source of Truth" (SSOT) in Base Currency (KRW) within the ledger.
- Store native currency amounts and exchange rates for foreign currency transactions.
- Provide a display toggle in the UI to switch between Base and Display currencies.

## Implementation Phases

### Phase 1: Foundation (Settings & DB Schema)
- Migration for `app_settings`, `accounts` expansion, `journal_line_fx`, and `fx_rates`.
- Implement `base_currency` configuration in Settings.
- Add `display_currency` selector to Sidebar.

### Phase 2: Core Service Layer (Account & Ledger)
- Update `account_service.py` to handle `currency` per account.
- Update `ledger_service.py` to support FX snapshots and native amounts.
- Add validations for multi-currency transactions.

### Phase 3: Transaction UI & Exchange Rates
- Support FX input in `pages/2_Transactions.py`.
- Implement automatic FX rate fetching and manual overrides.
- Implement specialized "Currency Exchange" template.

### Phase 4: Reports & Dashboard
- Update Dashboard to show "Book Value" (Base) vs "Current Value" (Display).
- Update BS/IS reports to respect currency conversion for display.

### Phase 5: Polish & Walkthrough
- Verification, linting (Ruff/Mypy), and documentation updates.

## Progress Dashboard
| Phase | Task | Status |
| :--- | :--- | :--- |
| **P1** | **Foundation** | [ ] |
| **P2** | **Core Service** | [ ] |
| **P3** | **Transaction UI** | [ ] |
| **P4** | **Visualization** | [ ] |
| **P5** | **Readiness** | [ ] |
