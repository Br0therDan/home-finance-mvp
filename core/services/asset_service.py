from __future__ import annotations
import sqlite3
from datetime import date, datetime
from typing import List, Dict, Optional, Any

from core.models import (
    Asset,
    AssetValuation,
    InvestmentEvent,
    InvestmentLot,
    InvestmentProfile,
)


def create_asset(
    conn: sqlite3.Connection,
    name: str,
    asset_class: str,
    linked_account_id: int,
    acquisition_date: date,
    acquisition_cost: float,
    asset_type: str = "OTHER",
    depreciation_method: str = "NONE",
    useful_life_years: int | None = None,
    salvage_value: float = 0.0,
    note: str = "",
) -> int:
    cursor = conn.execute(
        """INSERT INTO assets (name, asset_class, asset_type, linked_account_id, acquisition_date, acquisition_cost, 
                             depreciation_method, useful_life_years, salvage_value, note)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            name,
            asset_class,
            asset_type,
            linked_account_id,
            (
                acquisition_date.isoformat()
                if isinstance(acquisition_date, date)
                else acquisition_date
            ),
            float(acquisition_cost),
            depreciation_method,
            useful_life_years,
            float(salvage_value),
            note,
        ),
    )
    return cursor.lastrowid


def create_investment_profile(
    conn: sqlite3.Connection,
    asset_id: int,
    ticker: str,
    trading_currency: str,
    exchange: str | None = None,
    security_type: str | None = None,
    isin: str | None = None,
    broker: str | None = None,
) -> int:
    cursor = conn.execute(
        """INSERT INTO investment_profiles (asset_id, ticker, exchange, trading_currency, security_type, isin, broker)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            asset_id,
            ticker.strip(),
            exchange.strip() if exchange else None,
            trading_currency.strip(),
            security_type.strip() if security_type else None,
            isin.strip() if isin else None,
            broker.strip() if broker else None,
        ),
    )
    return cursor.lastrowid


def add_investment_lot(
    conn: sqlite3.Connection,
    asset_id: int,
    lot_date: date,
    quantity: float,
    unit_price_native: float,
    currency: str,
    fees_native: float = 0.0,
    fx_rate: float | None = None,
) -> int:
    cursor = conn.execute(
        """INSERT INTO investment_lots (asset_id, lot_date, quantity, remaining_quantity, unit_price_native, 
                                      fees_native, currency, fx_rate)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            asset_id,
            lot_date.isoformat() if isinstance(lot_date, date) else lot_date,
            float(quantity),
            float(quantity),
            float(unit_price_native),
            float(fees_native),
            currency.strip(),
            fx_rate,
        ),
    )
    return cursor.lastrowid


def record_investment_event(
    conn: sqlite3.Connection,
    asset_id: int,
    event_type: str,
    event_date: date,
    currency: str,
    quantity: float | None = None,
    price_per_unit_native: float | None = None,
    gross_amount_native: float | None = None,
    fees_native: float = 0.0,
    fx_rate: float | None = None,
    cash_account_id: int | None = None,
    income_account_id: int | None = None,
    fee_account_id: int | None = None,
    journal_entry_id: int | None = None,
    note: str | None = None,
) -> int:
    cursor = conn.execute(
        """INSERT INTO investment_events (asset_id, event_type, event_date, quantity, price_per_unit_native, 
                                        gross_amount_native, fees_native, currency, fx_rate, 
                                        cash_account_id, income_account_id, fee_account_id, journal_entry_id, note)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            asset_id,
            event_type.strip().upper(),
            event_date.isoformat() if isinstance(event_date, date) else event_date,
            float(quantity) if quantity is not None else None,
            float(price_per_unit_native) if price_per_unit_native is not None else None,
            float(gross_amount_native) if gross_amount_native is not None else None,
            float(fees_native),
            currency.strip(),
            fx_rate,
            cash_account_id,
            income_account_id,
            fee_account_id,
            journal_entry_id,
            note,
        ),
    )
    return cursor.lastrowid


def get_investment_performance(conn: sqlite3.Connection, asset_id: int) -> dict | None:
    # Latest valuation
    val_row = conn.execute(
        "SELECT * FROM asset_valuations WHERE asset_id = ? ORDER BY as_of_date DESC, id DESC LIMIT 1",
        (asset_id,),
    ).fetchone()
    if not val_row:
        return None

    # Cost basis from lots
    lot_row = conn.execute(
        "SELECT SUM(remaining_quantity * unit_price_native + fees_native) FROM investment_lots WHERE asset_id = ?",
        (asset_id,),
    ).fetchone()
    cost_basis_native = float(lot_row[0] or 0.0)

    unrealized_pl_native = val_row["value_native"] - cost_basis_native

    return {
        "asset_id": asset_id,
        "as_of_date": val_row["as_of_date"],
        "currency": val_row["currency"],
        "market_value_native": val_row["value_native"],
        "cost_basis_native": cost_basis_native,
        "unrealized_pl_native": unrealized_pl_native,
        "valuation_method": val_row["method"],
        "valuation_fx_rate": val_row["fx_rate"],
    }


def list_assets(conn: sqlite3.Connection) -> list[dict]:
    sql = """
        SELECT a.*, acc.name AS linked_account_name
        FROM assets a
        JOIN accounts acc ON acc.id = a.linked_account_id
        WHERE a.disposal_date IS NULL
        ORDER BY a.acquisition_date DESC, a.id DESC
    """
    rows = conn.execute(sql).fetchall()
    output = []
    for r in rows:
        data = dict(r)
        data["linked_account"] = r[
            "linked_account_name"
        ]  # Compatibility with UI expectations
        output.append(data)
    return output


def get_asset(conn: sqlite3.Connection, asset_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
    return dict(row) if row else None


def update_asset(
    conn: sqlite3.Connection,
    asset_id: int,
    name: str,
    asset_class: str,
    linked_account_id: int,
    acquisition_date: date,
    acquisition_cost: float,
    asset_type: str,
    depreciation_method: str,
    useful_life_years: int | None,
    salvage_value: float,
    note: str,
) -> None:
    conn.execute(
        """UPDATE assets SET name = ?, asset_class = ?, asset_type = ?, linked_account_id = ?, 
                          acquisition_date = ?, acquisition_cost = ?, depreciation_method = ?, 
                          useful_life_years = ?, salvage_value = ?, note = ?
           WHERE id = ?""",
        (
            name.strip(),
            asset_class,
            asset_type,
            linked_account_id,
            (
                acquisition_date.isoformat()
                if isinstance(acquisition_date, date)
                else acquisition_date
            ),
            float(acquisition_cost),
            depreciation_method,
            useful_life_years,
            float(salvage_value),
            note,
            asset_id,
        ),
    )


def delete_asset(conn: sqlite3.Connection, asset_id: int) -> None:
    conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))


def calculate_asset_depreciation(conn: sqlite3.Connection, as_of: date | None = None):
    # This was a complex one, let's simplify for the DTO world
    from core.services.ledger_service import account_balances

    if as_of is None:
        as_of = date.today()

    assets = conn.execute(
        "SELECT * FROM assets WHERE depreciation_method != 'NONE' AND disposal_date IS NULL"
    ).fetchall()

    results = []
    for a in assets:
        acq_date = (
            date.fromisoformat(a["acquisition_date"])
            if isinstance(a["acquisition_date"], str)
            else a["acquisition_date"]
        )
        months_since = (as_of.year - acq_date.year) * 12 + (
            as_of.month - acq_date.month
        )
        if months_since <= 0:
            results.append({"asset_id": a["id"], "periodic": 0.0, "accumulated": 0.0})
            continue

        useful_months = (a["useful_life_years"] or 5) * 12
        depreciable_amount = a["acquisition_cost"] - a["salvage_value"]

        if a["depreciation_method"] == "STRAIGHT_LINE":
            monthly_dep = depreciable_amount / useful_months
            accumulated = min(depreciable_amount, monthly_dep * months_since)
            results.append(
                {
                    "asset_id": a["id"],
                    "periodic": monthly_dep,
                    "accumulated": accumulated,
                }
            )
        elif a["depreciation_method"] == "DECLINING_BALANCE":
            # Simple double-declining balance approx
            rate = 2.0 / (a["useful_life_years"] or 5)
            # This would normally need year-by-year calculation, but let's keep it simple for MVP
            # NB: Just a placeholder for the logic
            accumulated = a["acquisition_cost"] * (
                1 - (1 - rate) ** (months_since / 12)
            )
            results.append(
                {
                    "asset_id": a["id"],
                    "periodic": 0.0,  # complex to calc mid-period without history
                    "accumulated": min(depreciable_amount, accumulated),
                }
            )
    return results


def reconcile_asset_valuations_with_ledger(
    conn: sqlite3.Connection, as_of: date | None = None
) -> dict:
    from core.services.fx_service import get_latest_rate
    from core.services.ledger_service import account_balances
    from core.services.settings_service import get_base_currency

    base_currency = get_base_currency(conn)
    rows = conn.execute("SELECT * FROM assets WHERE disposal_date IS NULL").fetchall()
    assets = [dict(r) for r in rows]

    if not assets:
        return {
            "base_currency": base_currency,
            "items": [],
            "total_book_value_base": 0.0,
            "total_valuation_value_base": 0.0,
            "total_delta_base": 0.0,
            "missing_rates": [],
        }

    asset_by_id = {int(asset["id"]): asset for asset in assets}
    linked_account_ids = {int(asset["linked_account_id"]) for asset in assets}

    placeholders = ",".join("?" for _ in linked_account_ids)
    account_rows = conn.execute(
        f"SELECT id, name FROM accounts WHERE id IN ({placeholders})",
        list(linked_account_ids),
    ).fetchall()
    account_name_map = {int(row["id"]): row["name"] for row in account_rows}

    balances = account_balances(conn, as_of=as_of)

    where_clause = ""
    params = []
    if as_of:
        where_clause = "WHERE v.as_of_date <= ?"
        params.append(as_of.isoformat() if isinstance(as_of, date) else as_of)

    sql = f"""
        WITH latest AS (
            SELECT
                v.asset_id,
                v.value_native,
                v.currency,
                v.as_of_date,
                ROW_NUMBER() OVER (
                    PARTITION BY v.asset_id
                    ORDER BY v.as_of_date DESC, v.id DESC
                ) AS rn
            FROM asset_valuations v
            {where_clause}
        )
        SELECT asset_id, value_native, currency, as_of_date
        FROM latest
        WHERE rn = 1
    """

    rows = conn.execute(sql, params).fetchall()

    valuation_totals: dict[int, float] = {}
    valued_assets_by_account: dict[int, set[int]] = {}
    missing_rates: set[tuple[str, str]] = set()

    for row in rows:
        asset_id = int(row["asset_id"])
        asset = asset_by_id.get(asset_id)
        if asset is None:
            continue
        currency = str(row["currency"])
        rate = get_latest_rate(conn, base_currency, currency)
        if rate is None:
            missing_rates.add((base_currency, currency))
            continue
        valuation_base = float(row["value_native"]) * rate
        account_id = int(asset["linked_account_id"])
        valuation_totals[account_id] = (
            valuation_totals.get(account_id, 0.0) + valuation_base
        )
        valued_assets_by_account.setdefault(account_id, set()).add(asset_id)

    assets_by_account: dict[int, list[int]] = {}
    for asset in assets:
        assets_by_account.setdefault(int(asset["linked_account_id"]), []).append(
            int(asset["id"])
        )

    items = []
    total_book = 0.0
    total_valuation = 0.0

    for account_id in sorted(linked_account_ids):
        book_value = float(balances.get(account_id, 0.0))
        valuation_value = float(valuation_totals.get(account_id, 0.0))
        asset_ids = assets_by_account.get(account_id, [])
        valued_asset_ids = valued_assets_by_account.get(account_id, set())
        item = {
            "account_id": account_id,
            "account_name": account_name_map.get(account_id, ""),
            "book_value_base": book_value,
            "valuation_value_base": valuation_value,
            "delta_base": valuation_value - book_value,
            "asset_count": len(asset_ids),
            "valued_asset_count": len(valued_asset_ids),
            "unvalued_asset_ids": [
                aid for aid in asset_ids if aid not in valued_asset_ids
            ],
        }
        items.append(item)
        total_book += book_value
        total_valuation += valuation_value

    return {
        "base_currency": base_currency,
        "items": items,
        "total_book_value_base": total_book,
        "total_valuation_value_base": total_valuation,
        "total_delta_base": total_valuation - total_book,
        "missing_rates": sorted(missing_rates),
    }


def get_asset_investments(conn: sqlite3.Connection, asset_id: int) -> dict:
    profile_row = conn.execute(
        "SELECT * FROM investment_profiles WHERE asset_id = ?", (asset_id,)
    ).fetchone()
    lots_rows = conn.execute(
        "SELECT * FROM investment_lots WHERE asset_id = ? ORDER BY lot_date",
        (asset_id,),
    ).fetchall()
    events_rows = conn.execute(
        "SELECT * FROM investment_events WHERE asset_id = ? ORDER BY event_date",
        (asset_id,),
    ).fetchall()

    return {
        "profile": dict(profile_row) if profile_row else None,
        "lots": [dict(r) for r in lots_rows],
        "events": [dict(r) for r in events_rows],
    }
