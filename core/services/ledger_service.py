from __future__ import annotations

import sqlite3
from datetime import date
from typing import Dict, List, Tuple

from core.models import JournalEntryInput, JournalLine


def _validate_entry(lines: List[JournalLine]) -> None:
    if not lines or len(lines) < 2:
        raise ValueError("A journal entry must have at least 2 lines.")

    total_debit = sum(max(0.0, float(l.debit)) for l in lines)
    total_credit = sum(max(0.0, float(l.credit)) for l in lines)

    if round(total_debit, 2) != round(total_credit, 2):
        raise ValueError(f"Unbalanced entry: debit={total_debit:.2f}, credit={total_credit:.2f}")

    for l in lines:
        if l.debit < 0 or l.credit < 0:
            raise ValueError("Debit/Credit cannot be negative.")
        if l.debit > 0 and l.credit > 0:
            raise ValueError("A single line cannot have both debit and credit.")
        if l.debit == 0 and l.credit == 0:
            raise ValueError("A line must have a debit or credit amount.")


def create_journal_entry(conn: sqlite3.Connection, entry: JournalEntryInput) -> int:
    _validate_entry(entry.lines)

    with conn:
        cur = conn.execute(
            """
            INSERT INTO journal_entries(entry_date, description, source)
            VALUES (?, ?, ?)
            """,
            (entry.entry_date.isoformat(), entry.description, entry.source),
        )
        entry_id = int(cur.lastrowid)

        conn.executemany(
            """
            INSERT INTO journal_lines(entry_id, account_id, debit, credit, memo)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (entry_id, l.account_id, float(l.debit), float(l.credit), l.memo)
                for l in entry.lines
            ],
        )

    return entry_id


def list_accounts(conn: sqlite3.Connection, active_only: bool = True):
    q = "SELECT id, name, type, parent_id, is_active FROM accounts"
    params: Tuple = ()
    if active_only:
        q += " WHERE is_active = 1"
    q += " ORDER BY type, name"
    return conn.execute(q, params).fetchall()


def get_account(conn: sqlite3.Connection, account_id: int):
    return conn.execute(
        "SELECT id, name, type FROM accounts WHERE id=?",
        (account_id,),
    ).fetchone()


def account_balances(conn: sqlite3.Connection, as_of: date | None = None) -> Dict[int, float]:
    """Return raw balance = sum(debit - credit) per account."""
    params: List = []
    where = ""
    if as_of is not None:
        where = "WHERE je.entry_date <= ?"
        params.append(as_of.isoformat())

    rows = conn.execute(
        f"""
        SELECT jl.account_id AS account_id,
               SUM(jl.debit - jl.credit) AS balance
        FROM journal_lines jl
        JOIN journal_entries je ON je.id = jl.entry_id
        {where}
        GROUP BY jl.account_id
        """,
        tuple(params),
    ).fetchall()

    return {int(r["account_id"]): float(r["balance"] or 0.0) for r in rows}


def trial_balance(conn: sqlite3.Connection, as_of: date | None = None):
    bal = account_balances(conn, as_of=as_of)
    accounts = list_accounts(conn, active_only=False)

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


def balance_sheet(conn: sqlite3.Connection, as_of: date | None = None):
    """Compute a simple balance sheet using raw balances.

    Convention:
      - Assets: positive balances typically
      - Liabilities/Equity: negative balances typically

    For display:
      assets_value = max(balance, 0)
      liab_eq_value = max(-balance, 0)
    """
    bal = account_balances(conn, as_of=as_of)
    accounts = list_accounts(conn, active_only=True)

    assets = []
    liabilities = []
    equity = []

    for a in accounts:
        t = a["type"]
        b = float(bal.get(int(a["id"]), 0.0))

        if t == "ASSET":
            v = b
            if abs(v) > 1e-9:
                assets.append((a["name"], v))
        elif t == "LIABILITY":
            v = -b
            if abs(v) > 1e-9:
                liabilities.append((a["name"], v))
        elif t == "EQUITY":
            v = -b
            if abs(v) > 1e-9:
                equity.append((a["name"], v))

    total_assets = sum(v for _, v in assets)
    total_liab = sum(v for _, v in liabilities)
    total_eq = sum(v for _, v in equity)

    return {
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "total_assets": total_assets,
        "total_liabilities": total_liab,
        "total_equity": total_eq,
        "net_worth": total_assets - total_liab,
        "balanced_gap": total_assets - (total_liab + total_eq),
    }


def income_statement(conn: sqlite3.Connection, start: date, end: date):
    """Simple P&L (Income Statement) within [start, end]."""
    rows = conn.execute(
        """
        SELECT a.type AS type, a.name AS account,
               SUM(jl.debit - jl.credit) AS raw_balance
        FROM journal_lines jl
        JOIN journal_entries je ON je.id = jl.entry_id
        JOIN accounts a ON a.id = jl.account_id
        WHERE je.entry_date >= ? AND je.entry_date <= ?
          AND a.type IN ('INCOME', 'EXPENSE')
        GROUP BY a.type, a.name
        ORDER BY a.type, a.name
        """,
        (start.isoformat(), end.isoformat()),
    ).fetchall()

    income = []
    expense = []
    for r in rows:
        t = r["type"]
        b = float(r["raw_balance"] or 0.0)
        # For INCOME, normal is credit => negative raw balance
        if t == "INCOME":
            income.append((r["account"], -b))
        else:
            expense.append((r["account"], b))

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
    """Very lightweight cashflow proxy: movement of cash/bank accounts by month."""
    # Consider asset accounts with '현금' or '예금' or 'Cash' or 'Bank' words
    cash_like = conn.execute(
        """
        SELECT id, name FROM accounts
        WHERE type='ASSET'
          AND (name LIKE '%현금%' OR name LIKE '%예금%' OR name LIKE '%Cash%' OR name LIKE '%Bank%')
        """
    ).fetchall()
    cash_ids = [int(r["id"]) for r in cash_like]

    if not cash_ids:
        return []

    placeholders = ",".join(["?"] * len(cash_ids))

    rows = conn.execute(
        f"""
        SELECT substr(je.entry_date, 1, 7) AS ym,
               SUM(CASE WHEN jl.account_id IN ({placeholders}) THEN (jl.debit - jl.credit) ELSE 0 END) AS net
        FROM journal_entries je
        JOIN journal_lines jl ON jl.entry_id = je.id
        WHERE substr(je.entry_date, 1, 4) = ?
        GROUP BY ym
        ORDER BY ym
        """,
        tuple(cash_ids) + (str(year),),
    ).fetchall()

    return [{"month": r["ym"], "net_cash_change": float(r["net"] or 0.0)} for r in rows]
