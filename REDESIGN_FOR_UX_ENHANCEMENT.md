# Redesign for UX Enhancement

## Purpose
This document aligns the product redesign around a household-first experience. The goal is to make asset management the primary task while keeping finance tracking automatic and behind the scenes. Users should feel like they are organizing their household assets, not doing accounting.

## Goals
- **Household-UX-first philosophy**: “asset management first, finance automated.”
  - Users start with what they own and manage today.
  - Financial records are created automatically and kept consistent without extra steps.
- **Asset registration, updates, valuation, and disposal UX**
  - Register assets with minimal steps (name, category, purchase date, estimated value).
  - Update value with a single action from the asset detail view.
  - See a simple valuation history timeline.
  - Dispose of assets with a guided flow that asks “what happened?” and “what did you receive?”
- **Prioritized household asset categories**
  - Primary categories: Cash & Bank, Vehicles, Home & Property, Electronics, Furniture, Jewelry & Collectibles, Investments, Retirement, Business Interests.
  - Optional categories: Loans Receivable, Insurance Cash Value, Other.
- **Simplified Chart of Accounts (CoA)**
  - Show only a small set of user-facing accounts that map to the core categories above.
  - Hide system-only accounts and accounting terms from everyday UX.
- **Net-worth consistency requirements**
  - Net worth must always reconcile between asset views and ledger views.
  - A change to an asset’s value should be visible immediately in the net worth total.
- **Investment asset valuation & dashboard**
  - Provide a dedicated investment view with holdings, latest value, and change over time.
  - Allow manual valuation updates per holding, with a clean snapshot history.
- **Subscription/recurring transaction model**
  - Support household recurring items (subscriptions, utilities, membership fees).
  - Present as “planned spending” and generate ledger entries automatically on schedule.
- **Clarified mapping between resource assets and finance-ledger assets**
  - Resource assets (real-world items) must map to ledger accounts without exposing accounting terms.
  - Users see a single asset record; the system manages the linked ledger posting account.

## Code Review for Issue Resolution
- Ensure that asset-related changes do not break the ledger’s double-entry balance.
- Confirm that new UX flows create or update journal entries correctly.
- Verify that reports use journal lines as the single source of truth.
- Check that any new tables are introduced only through migrations.
- Keep UI changes in Streamlit pages and business logic in service modules.

## Enhancement Plan
1. **Asset-first onboarding**
   - Start with a guided asset inventory workflow.
   - Add a simple net-worth summary after each step.
2. **Unified asset detail view**
   - Combine asset info, valuations, and ledger impact into one page.
   - Provide quick actions: update value, dispose, add note.
3. **Investment dashboard**
   - Separate section for investments with trend indicators and latest valuation.
4. **Recurring household items**
   - Add a simple “recurring payments” manager.
   - Convert these to scheduled ledger entries automatically.
5. **Simplified CoA exposure**
   - Present a user-friendly category list that maps to ledger accounts.
   - Keep accounting-specific fields hidden from general UI.

---

# Technical Appendix: Data Model Changes

> The following items describe the expected data model additions or adjustments needed to support the UX changes.

## Asset Enhancements
- **assets**
  - Add `category` (household category label).
  - Add `status` (active, disposed).
  - Add `display_name` for user-friendly labels if different from ledger label.
  - Keep `linked_account_id` as the ledger mapping.

## Valuation Enhancements
- **valuations**
  - Add `source` (manual, market, import).
  - Add `notes` for valuation context.

## Recurring Items
- **recurring_transactions** (new)
  - `id`, `name`, `amount`, `currency`, `frequency`, `next_run_date`, `is_active`
  - `debit_account_id`, `credit_account_id`
  - `linked_entry_id` for generated journal entries

## Investment Holdings
- **investment_holdings** (new)
  - `id`, `asset_id`, `ticker`, `quantity`, `cost_basis`
- **investment_prices** (new)
  - `id`, `holding_id`, `date`, `price`, `source`

## Ledger Mapping and Consistency
- Each asset record must map to a single ledger posting account.
- Net worth should be calculated from journal lines and cross-checked against asset totals.
- Disposal flows must generate balanced journal entries tied back to the asset.
