# Copilot Instructions (home-finance-mvp)

This document is a **task contract** for GitHub Copilot (or any coding agent) to work on this repository safely and consistently.

## Project Summary

A household finance & asset management MVP built with:

- **UI**: Streamlit (multi-page app)
- **DB**: SQLite (`data/app.db`)
- **Accounting model**: Minimal **double-entry ledger** (Journal Entries + Journal Lines)
- **Key capabilities**
  - Transaction input (cashbook UX) → auto-generated journal entries (balanced)
  - Ledger browsing + trial balance
  - Reports: BS (Balance Sheet), IS (Income Statement), Cashflow (simple)
  - Asset register + valuation history
  - Settings: Chart of Accounts (CoA)

## Ground Rules (Non-negotiable)

1. **Single Source of Truth (SSOT)**
   - The ledger tables are the SSOT:
     - `journal_entries`
     - `journal_lines`
   - Reports **must be computed from journal lines**, not from “transaction UI” data.

2. **Double-entry must always balance**
   - For each `journal_entry`:
     - `SUM(debit) == SUM(credit)` (within rounding tolerance)
   - Reject writes that violate this rule.

3. **No breaking DB schema without migration**
   - Any schema change requires a new SQL migration in `migrations/`.
   - Never modify existing migration files.

4. **Keep it local-first**
   - No external services.
   - No cloud dependencies.
   - SQLite stays the only DB for MVP.

5. **Keep changes minimal and incremental**
   - Prefer small, well-scoped PRs.
   - No sweeping refactors unless explicitly requested.

---

## Repository Structure

- `app.py`  
  Streamlit entrypoint; sets up navigation and DB initialization.

- `pages/`  
  Streamlit pages:
  - `1_Dashboard.py`
  - `2_Transactions.py` (cashbook UX → auto-journal core path)
  - `3_Assets.py`
  - `4_Ledger.py`
  - `5_Reports.py`
  - `6_Settings.py`

- `core/db.py`  
  SQLite connection helpers + migration runner.

- `core/services/ledger_service.py`  
  Ledger write validation + balance checks + basic derived calculations.

- `core/services/report_service.py`  
  BS/IS/Cashflow queries and report shaping.

- `core/services/asset_service.py`  
  Asset register CRUD + valuation tracking.

- `migrations/`  
  Ordered SQL migrations and seeds.

---

## Coding Conventions

### Python
- Python 3.11+ preferred
- Use type hints for service functions.
- Avoid global state; Streamlit session state is allowed for UI caching only.
- Centralize DB access in `core/db.py`.

### SQLite & Queries
- Use parameterized queries everywhere (avoid string interpolation).
- Index any column used for filtering/joining frequently (e.g., dates, foreign keys).

### Streamlit UI
- Keep UI logic in `pages/*`.
- Keep business logic in `core/services/*`.
- For new UI components, add to `core/ui/components.py`.

---

## Data Model (Expected)

**accounts**
- id, name, type (ASSET/LIABILITY/EQUITY/INCOME/EXPENSE), parent_id, is_active

**journal_entries**
- id, date, description, source, created_at

**journal_lines**
- id, entry_id, account_id, debit, credit, memo

**assets**
- id, name, asset_class, linked_account_id, acquisition_date, acquisition_cost, disposal_date, note

**valuations**
- id, asset_id, date, value, method

---

## How to Add Features Safely

### When adding a new “Transaction Type”
Example: refund, transfer, investment buy/sell.

**Steps**
1. Add a mapping function:
   - UI input → a list of ledger lines (debit/credit)
2. Validate:
   - total debit == total credit
   - required accounts exist / are active
3. Write to DB:
   - create `journal_entries` row
   - create `journal_lines` rows

**Rules**
- Never store “transaction only” tables that bypass journal.
- If you need convenience tables, they must reference `journal_entries.id` explicitly.

### When adding reports
- Add report queries under `core/services/report_service.py`.
- Keep calculations explainable and based on:
  - account types
  - journal balances
- Prefer SQL aggregation over Python loops (performance and clarity).

---

## Testing Guidance (Lightweight)

MVP uses minimal testing, but for any change to ledger logic:
- Add at least one unit test ensuring:
  - balanced entry is accepted
  - unbalanced entry is rejected
  - BS totals behave as expected

If no test harness exists yet, create:
- `tests/test_ledger.py`
- and add a minimal `pytest` setup.

---

## Performance & UX Guardrails

- Use caching (`st.cache_data`) only for:
  - report aggregates
  - read-only lookup data (accounts list)
- Avoid caching anything that can cause stale balances after writes.
- Provide user feedback on every write:
  - success toast/message
  - error message with exact reason

---

## Security & Privacy

- All data is local on disk.
- Do not introduce telemetry.
- Do not add any external tracking or analytics.

---

## Suggested Next Tasks (in priority order)

1. **Card workflow**
   - Card spend → liability increases
   - Card payment → liability decreases

2. **CSV import**
   - Bank export CSV → map to cashbook entries → generate ledger

3. **Rule-based auto-categorization**
   - Vendor/keywords → account mapping

4. **Asset disposal**
   - Sell asset → cash increase + gain/loss recognition

---

## “Done” Definition for Any PR

A change is considered done when:
- Streamlit app runs with no errors
- DB migrations apply cleanly on an empty DB
- Ledger remains balanced for all new flows
- README remains accurate (update if behavior changes)

---

## Agent Operating Instructions (Copilot)

When working on this repo, always:
1. Read the relevant service file first.
2. Locate the SSOT ledger write path.
3. Make minimal edits.
4. Maintain balanced ledger invariants.
5. Add a migration if schema changes.
6. Run locally:
   - `uv sync`
   - `streamlit run app.py`
7. Summarize what changed and why.
