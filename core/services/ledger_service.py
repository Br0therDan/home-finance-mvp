from __future__ import annotations
import sqlite3
from datetime import date
from typing import List, Dict, Optional, Any

from core.models import Account, JournalEntry, JournalEntryInput, JournalLine


def _validate_entry(lines: list[JournalLine]) -> None:
    if not lines or len(lines) < 2:
        raise ValueError("A journal entry must have at least 2 lines.")

    total_debit = sum(max(0.0, float(line.debit)) for line in lines)
    total_credit = sum(max(0.0, float(line.credit)) for line in lines)

    if round(total_debit, 2) != round(total_credit, 2):
        raise ValueError(
            f"Unbalanced entry: debit={total_debit:.2f}, credit={total_credit:.2f}"
        )

    for line in lines:
        if line.debit < 0 or line.credit < 0:
            raise ValueError("Debit/Credit cannot be negative.")
        if line.debit > 0 and line.credit > 0:
            raise ValueError("A single line cannot have both debit and credit.")
        if line.debit == 0 and line.credit == 0:
            raise ValueError("A line must have a debit or credit amount.")


def _validate_posting_accounts(
    conn: sqlite3.Connection, lines: list[JournalLine]
) -> None:
    account_ids = list({int(line.account_id) for line in lines})
    if not account_ids:
        raise ValueError("At least one journal line is required.")

    placeholders = ",".join("?" for _ in account_ids)
    rows = conn.execute(
        f"SELECT id, allow_posting FROM accounts WHERE id IN ({placeholders})",
        account_ids,
    ).fetchall()
    allow_map = {r["id"]: r["allow_posting"] for r in rows}

    for account_id in account_ids:
        if account_id not in allow_map:
            raise ValueError("Account not found.")
        if not allow_map[account_id]:
            raise ValueError(
                "상위(집계) 계정에는 직접 분개할 수 없습니다. 하위 계정을 선택하세요."
            )


def create_journal_entry(conn: sqlite3.Connection, entry_in: JournalEntryInput) -> int:
    _validate_entry(entry_in.lines)
    _validate_posting_accounts(conn, entry_in.lines)

    # Create Entry
    cursor = conn.execute(
        "INSERT INTO journal_entries (entry_date, description, source) VALUES (?, ?, ?)",
        (
            (
                entry_in.entry_date.isoformat()
                if isinstance(entry_in.entry_date, date)
                else entry_in.entry_date
            ),
            entry_in.description,
            entry_in.source,
        ),
    )
    entry_id = cursor.lastrowid

    for line in entry_in.lines:
        conn.execute(
            """INSERT INTO journal_lines (entry_id, account_id, debit, credit, memo, native_amount, native_currency, fx_rate)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry_id,
                line.account_id,
                float(line.debit),
                float(line.credit),
                line.memo,
                line.native_amount,
                line.native_currency,
                line.fx_rate,
            ),
        )

    return entry_id


def list_accounts(conn: sqlite3.Connection, active_only: bool = True) -> list[dict]:
    query = "SELECT * FROM accounts"
    if active_only:
        query += " WHERE is_active = 1"
    query += " ORDER BY type, name"

    rows = conn.execute(query).fetchall()
    return [dict(r) for r in rows]


def list_posting_accounts(
    conn: sqlite3.Connection, active_only: bool = True
) -> list[dict]:
    query = "SELECT * FROM accounts WHERE allow_posting = 1"
    if active_only:
        query += " AND is_active = 1"
    query += " ORDER BY type, name"

    rows = conn.execute(query).fetchall()
    return [dict(r) for r in rows]


def get_account(conn: sqlite3.Connection, account_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    return dict(row) if row else None


def get_account_by_name(
    conn: sqlite3.Connection, name: str, type_: str | None = None
) -> Optional[dict]:
    query = "SELECT * FROM accounts WHERE name = ?"
    params = [name]
    if type_:
        query += " AND type = ?"
        params.append(type_)

    row = conn.execute(query, params).fetchone()
    return dict(row) if row else None


def account_balances(
    conn: sqlite3.Connection, as_of: date | None = None
) -> dict[int, float]:
    query = """
        SELECT jl.account_id, SUM(jl.debit - jl.credit) AS balance
        FROM journal_lines jl
        JOIN journal_entries je ON je.id = jl.entry_id
    """
    params = []
    if as_of:
        query += " WHERE je.entry_date <= ?"
        params.append(as_of.isoformat() if isinstance(as_of, date) else as_of)

    query += " GROUP BY jl.account_id"

    rows = conn.execute(query, params).fetchall()
    return {r["account_id"]: (r["balance"] or 0.0) for r in rows}


def account_balances_multi(
    conn: sqlite3.Connection, as_of: date | None = None
) -> dict[int, dict[str, float]]:
    where_clause = ""
    params = []
    if as_of:
        where_clause = "WHERE je.entry_date <= ?"
        params.append(as_of.isoformat() if isinstance(as_of, date) else as_of)

    sql = f"""
        SELECT 
            jl.account_id,
            SUM(jl.debit - jl.credit) AS base_balance,
            SUM(
                CASE 
                    WHEN jl.native_amount IS NOT NULL THEN (
                        CASE WHEN jl.debit > 0 THEN jl.native_amount ELSE -jl.native_amount END
                    )
                    ELSE (jl.debit - jl.credit)
                END
            ) AS native_balance
        FROM journal_lines jl
        JOIN journal_entries je ON je.id = jl.entry_id
        {where_clause}
        GROUP BY jl.account_id
    """

    rows = conn.execute(sql, params).fetchall()

    return {
        r["account_id"]: {
            "base": float(r["base_balance"] or 0.0),
            "native": float(r["native_balance"] or 0.0),
        }
        for r in rows
    }


def trial_balance(conn: sqlite3.Connection, as_of: date | None = None):
    bal = account_balances(conn, as_of=as_of)
    accounts = list_accounts(conn, active_only=False)  # list of dicts

    results = []
    for a in accounts:
        b = float(bal.get(int(a["id"]), 0.0))
        results.append(
            {
                "account_id": int(a["id"]),
                "account": a["name"],
                "type": a["type"],
                "debit": b if b > 0 else 0.0,
                "credit": -b if b < 0 else 0.0,
                "raw_balance": b,
            }
        )
    return results


def balance_sheet(
    conn: sqlite3.Connection,
    as_of: date | None = None,
    display_currency: str | None = None,
):
    from core.services.fx_service import get_latest_rate
    from core.services.settings_service import get_base_currency

    base_cur = get_base_currency(conn)
    quote_cur = display_currency or base_cur

    bal_multi = account_balances_multi(conn, as_of=as_of)
    accounts = list_accounts(conn, active_only=True)

    acc_currencies = {
        int(a["id"]): a.get("currency", base_cur) or base_cur for a in accounts
    }

    assets = []
    liabilities = []
    equity = []
    missing_rates: set[tuple[str, str]] = set()

    for a in accounts:
        aid = int(a["id"])
        t = a["type"]
        b_data = bal_multi.get(aid, {"base": 0.0, "native": 0.0})
        base_val = b_data["base"]
        native_val = b_data["native"]
        native_cur = acc_currencies.get(aid, base_cur)

        book_val = base_val

        if native_cur == base_cur:
            current_val_base = base_val
        else:
            current_rate = get_latest_rate(conn, base_cur, native_cur)
            if current_rate is None:
                missing_rates.add((base_cur, native_cur))
                current_val_base = base_val
            else:
                current_val_base = native_val * current_rate

        if quote_cur == base_cur:
            disp_val = current_val_base
        else:
            krw_quote_rate = get_latest_rate(conn, base_cur, quote_cur)
            if krw_quote_rate is None or krw_quote_rate == 0:
                missing_rates.add((base_cur, quote_cur))
                disp_val = current_val_base
            else:
                disp_val = current_val_base / krw_quote_rate

        item = {
            "id": aid,
            "name": a["name"],
            "currency": native_cur,
            "native_balance": native_val,
            "book_value_base": book_val,
            "current_value_base": current_val_base,
            "display_value": disp_val,
        }

        if t == "ASSET":
            if abs(base_val) > 1e-9 or abs(native_val) > 1e-9:
                assets.append(item)
        elif t == "LIABILITY":
            item.update(
                {k: -v for k, v in item.items() if isinstance(v, float)}
            )  # Flip signs
            if abs(base_val) > 1e-9 or abs(native_val) > 1e-9:
                liabilities.append(item)
        elif t == "EQUITY":
            item.update({k: -v for k, v in item.items() if isinstance(v, float)})
            if abs(base_val) > 1e-9 or abs(native_val) > 1e-9:
                equity.append(item)

    total_assets_base = sum(i["current_value_base"] for i in assets)
    total_liab_base = sum(i["current_value_base"] for i in liabilities)
    total_eq_base = sum(i["book_value_base"] for i in equity)

    total_assets_disp = sum(i["display_value"] for i in assets)
    total_liab_disp = sum(i["display_value"] for i in liabilities)
    total_eq_disp = sum(i["display_value"] for i in equity)

    return {
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "total_assets_base": total_assets_base,
        "total_liabilities_base": total_liab_base,
        "total_equity_base": total_eq_base,
        "total_assets_disp": total_assets_disp,
        "total_liabilities_disp": total_liab_disp,
        "total_equity_disp": total_eq_disp,
        "net_worth_base": total_assets_base - total_liab_base,
        "net_worth_disp": total_assets_disp - total_liab_disp,
        "display_currency": quote_cur,
        "base_currency": base_cur,
        "missing_rates": sorted(missing_rates),
    }


def income_statement(conn: sqlite3.Connection, start: date, end: date):
    sql = """
        SELECT a.type AS type, a.name AS account,
               SUM(jl.debit - jl.credit) AS raw_balance
        FROM journal_lines jl
        JOIN journal_entries je ON je.id = jl.entry_id
        JOIN accounts a ON a.id = jl.account_id
        WHERE je.entry_date >= ? AND je.entry_date <= ?
          AND a.type IN ('INCOME', 'EXPENSE')
        GROUP BY a.type, a.name
        ORDER BY a.type, a.name
    """
    rows = conn.execute(
        sql,
        (
            start.isoformat() if isinstance(start, date) else start,
            end.isoformat() if isinstance(end, date) else end,
        ),
    ).fetchall()

    income = []
    expense = []
    for r in rows:
        t = r["type"]
        name = r["account"]
        b = float(r["raw_balance"] or 0.0)
        if t == "INCOME":
            income.append((name, -b))
        else:
            expense.append((name, b))

    total_income = sum(v for _, v in income)
    total_expense = sum(v for _, v in expense)
    return {
        "income": income,
        "expense": expense,
        "total_income": total_income,
        "total_expense": total_expense,
        "net_profit": total_income - total_expense,
    }


def monthly_cashflow(conn: sqlite3.Connection, year: int):
    """Return monthly cashflow for cash-equivalent accounts."""
    cash_name_patterns = [
        "%현금%",
        "%보통예금%",
        "%정기예금%",
        "%cash%",
        "%checking%",
        "%savings%",
    ]
    name_clauses = " OR ".join(
        f"LOWER(a.name) LIKE LOWER(?)" for _ in range(len(cash_name_patterns))
    )

    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    base_params = list(cash_name_patterns)

    opening_sql = f"""
        WITH cash_accounts AS (
            SELECT a.id
            FROM accounts a
            WHERE a.is_active = 1
              AND ({name_clauses})
        )
        SELECT COALESCE(SUM(jl.debit - jl.credit), 0) AS opening_balance
        FROM journal_lines jl
        JOIN journal_entries je ON je.id = jl.entry_id
        WHERE jl.account_id IN (SELECT id FROM cash_accounts)
          AND je.entry_date < ?
    """

    monthly_sql = f"""
        WITH cash_accounts AS (
            SELECT a.id
            FROM accounts a
            WHERE a.is_active = 1
              AND ({name_clauses})
        )
        SELECT strftime('%m', je.entry_date) AS month,
               SUM(jl.debit - jl.credit) AS net_change
        FROM journal_lines jl
        JOIN journal_entries je ON je.id = jl.entry_id
        WHERE jl.account_id IN (SELECT id FROM cash_accounts)
          AND je.entry_date >= ?
          AND je.entry_date <= ?
        GROUP BY strftime('%m', je.entry_date)
        ORDER BY strftime('%m', je.entry_date)
    """

    opening_balance = float(
        conn.execute(opening_sql, base_params + [start_date]).fetchone()[0] or 0.0
    )
    rows = conn.execute(monthly_sql, base_params + [start_date, end_date]).fetchall()
    monthly_map = {int(r["month"]): float(r["net_change"] or 0.0) for r in rows}

    results = []
    running_balance = opening_balance
    for month in range(1, 13):
        net_change = monthly_map.get(month, 0.0)
        running_balance += net_change
        results.append(
            {
                "month": month,
                "net_change": net_change,
                "ending_balance": running_balance,
            }
        )
    return results
