from __future__ import annotations

import sqlite3
from datetime import date

from core.models import JournalEntryInput, JournalLine


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

    placeholders = ",".join(["?"] * len(account_ids))
    rows = conn.execute(
        f"SELECT id, allow_posting FROM accounts WHERE id IN ({placeholders})",
        tuple(account_ids),
    ).fetchall()
    allow_map = {int(r["id"]): int(r["allow_posting"]) for r in rows}

    for account_id in account_ids:
        if account_id not in allow_map:
            raise ValueError("Account not found.")
        if allow_map[account_id] != 1:
            raise ValueError(
                "상위(집계) 계정에는 직접 분개할 수 없습니다. 하위 계정을 선택하세요."
            )


def create_journal_entry(conn: sqlite3.Connection, entry: JournalEntryInput) -> int:
    _validate_entry(entry.lines)
    _validate_posting_accounts(conn, entry.lines)

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
                (
                    entry_id,
                    line.account_id,
                    float(line.debit),
                    float(line.credit),
                    line.memo,
                )
                for line in entry.lines
            ],
        )

        # Persistence for FX snapshots
        # We need the IDs of the newly inserted journal_lines to link them.
        # SQLite's lastrowid only gives the last one. Using a more reliable way:
        line_rows = conn.execute(
            "SELECT id, account_id FROM journal_lines WHERE entry_id = ? ORDER BY id ASC",
            (entry_id,),
        ).fetchall()

        fx_payloads = []
        for i, row in enumerate(line_rows):
            line_input = entry.lines[i]
            if (
                line_input.native_currency
                and line_input.native_amount is not None
                and line_input.fx_rate
            ):
                from core.services.settings_service import get_base_currency

                base_cur = get_base_currency(conn)

                fx_payloads.append(
                    (
                        int(row["id"]),
                        line_input.native_currency.upper(),
                        float(line_input.native_amount),
                        base_cur,
                        float(line_input.fx_rate),
                        float(line_input.debit or line_input.credit),
                        "manual",
                    )
                )

        if fx_payloads:
            conn.executemany(
                """
                INSERT INTO journal_line_fx (line_id, native_currency, native_amount, base_currency, fx_rate, base_amount, rate_source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                fx_payloads,
            )

    return entry_id


def list_accounts(conn: sqlite3.Connection, active_only: bool = True):
    q = """
    SELECT id, name, type, parent_id, is_active, is_system, level, allow_posting
    FROM accounts
    """
    params: tuple = ()
    if active_only:
        q += " WHERE is_active = 1"
    q += " ORDER BY type, name"
    return conn.execute(q, params).fetchall()


def list_posting_accounts(conn: sqlite3.Connection, active_only: bool = True):
    q = """
    SELECT id, name, type, parent_id, is_active, is_system, level, allow_posting, currency
    FROM accounts
    WHERE allow_posting = 1
    """
    params: tuple = ()
    if active_only:
        q += " AND is_active = 1"
    q += " ORDER BY type, name"
    return conn.execute(q, params).fetchall()


def get_account(conn: sqlite3.Connection, account_id: int):
    return conn.execute(
        "SELECT id, name, type FROM accounts WHERE id=?",
        (account_id,),
    ).fetchone()


def get_account_by_name(conn: sqlite3.Connection, name: str, type_: str | None = None):
    if type_:
        return conn.execute(
            "SELECT id, name, type FROM accounts WHERE name=? AND type=?",
            (name, type_),
        ).fetchone()
    return conn.execute(
        "SELECT id, name, type FROM accounts WHERE name=?",
        (name,),
    ).fetchone()


def has_opening_balance_entry(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT COUNT(1) AS cnt FROM journal_entries WHERE source = ?",
        ("opening_balance",),
    ).fetchone()
    return int(row["cnt"] or 0) > 0


def create_opening_balance_entry(
    conn: sqlite3.Connection,
    entry_date: date,
    description: str,
    asset_lines: list[JournalLine],
    liability_lines: list[JournalLine],
) -> int:
    if has_opening_balance_entry(conn):
        raise ValueError("OPENING_BALANCE entry already exists.")

    lines: list[JournalLine] = []
    for line in asset_lines:
        if line.debit < 0 or line.credit < 0:
            raise ValueError("Amount cannot be negative.")
        if line.debit > 0:
            lines.append(
                JournalLine(
                    account_id=line.account_id,
                    debit=line.debit,
                    credit=0.0,
                    memo=line.memo,
                )
            )

    for line in liability_lines:
        if line.debit < 0 or line.credit < 0:
            raise ValueError("Amount cannot be negative.")
        if line.credit > 0:
            lines.append(
                JournalLine(
                    account_id=line.account_id,
                    debit=0.0,
                    credit=line.credit,
                    memo=line.memo,
                )
            )

    if not lines:
        raise ValueError("At least one opening balance line is required.")

    total_debit = sum(float(line.debit) for line in lines)
    total_credit = sum(float(line.credit) for line in lines)

    equity = get_account_by_name(conn, "기초순자산", "EQUITY")
    if equity is None:
        equity = get_account_by_name(conn, "기초자본(Opening Balance)", "EQUITY")
    if equity is None:
        raise ValueError("Opening equity account not found.")

    gap = total_debit - total_credit
    if abs(gap) > 1e-9:
        if gap > 0:
            lines.append(
                JournalLine(
                    account_id=int(equity["id"]),
                    debit=0.0,
                    credit=float(gap),
                    memo=description,
                )
            )
        else:
            lines.append(
                JournalLine(
                    account_id=int(equity["id"]),
                    debit=float(-gap),
                    credit=0.0,
                    memo=description,
                )
            )

    entry = JournalEntryInput(
        entry_date=entry_date,
        description=description,
        source="opening_balance",
        lines=lines,
    )
    return create_journal_entry(conn, entry)


def account_balances(
    conn: sqlite3.Connection, as_of: date | None = None
) -> dict[int, float]:
    """Return raw balance = sum(debit - credit) per account."""
    params: list[str] = []
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
