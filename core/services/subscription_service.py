from __future__ import annotations

import calendar
import sqlite3
from datetime import date, timedelta
from typing import Any

from core.models import JournalEntryInput, JournalLine
from core.services.ledger_service import create_journal_entry

CADENCE_OPTIONS = {"daily", "weekly", "monthly", "quarterly", "yearly"}


def _validate_cadence(cadence: str, interval: int) -> None:
    if cadence not in CADENCE_OPTIONS:
        raise ValueError(
            "Cadence must be one of daily/weekly/monthly/quarterly/yearly."
        )
    if interval < 1:
        raise ValueError("Interval must be at least 1.")


def _validate_accounts(
    conn: sqlite3.Connection, debit_account_id: int, credit_account_id: int
):
    # Minimal check
    debit = conn.execute(
        "SELECT allow_posting FROM accounts WHERE id = ?", (debit_account_id,)
    ).fetchone()
    credit = conn.execute(
        "SELECT allow_posting FROM accounts WHERE id = ?", (credit_account_id,)
    ).fetchone()
    if debit is None or credit is None:
        raise ValueError("Invalid account selection.")
    if not debit["allow_posting"] or not credit["allow_posting"]:
        raise ValueError("Accounts must allow posting.")


def _add_months(current: date, months: int) -> date:
    month_index = current.month - 1 + months
    year = current.year + month_index // 12
    month = month_index % 12 + 1
    day = min(current.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _advance_due_date(current: Any, cadence: str, interval: int) -> date:
    if isinstance(current, str):
        current = date.fromisoformat(current)

    if cadence == "daily":
        return current + timedelta(days=interval)
    if cadence == "weekly":
        return current + timedelta(days=7 * interval)
    if cadence == "monthly":
        return _add_months(current, interval)
    if cadence == "quarterly":
        return _add_months(current, 3 * interval)
    if cadence == "yearly":
        return _add_months(current, 12 * interval)
    raise ValueError("Unsupported cadence.")


def create_subscription(
    conn: sqlite3.Connection,
    *,
    name: str,
    cadence: str,
    interval: int,
    next_due_date: date,
    amount: float,
    debit_account_id: int,
    credit_account_id: int,
    memo: str = "",
    is_active: bool = True,
    auto_create_journal: bool = False,
) -> int:
    _validate_cadence(cadence, interval)
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    _validate_accounts(conn, debit_account_id, credit_account_id)

    cursor = conn.execute(
        """INSERT INTO subscriptions (name, cadence, interval, next_due_date, amount, 
                                    debit_account_id, credit_account_id, memo, is_active, auto_create_journal)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            name.strip(),
            cadence,
            interval,
            (
                next_due_date.isoformat()
                if isinstance(next_due_date, date)
                else next_due_date
            ),
            float(amount),
            debit_account_id,
            credit_account_id,
            memo.strip(),
            1 if is_active else 0,
            1 if auto_create_journal else 0,
        ),
    )
    return cursor.lastrowid


def list_subscriptions(
    conn: sqlite3.Connection, active_only: bool = True
) -> list[dict]:
    query = "SELECT * FROM subscriptions"
    if active_only:
        query += " WHERE is_active = 1"
    query += " ORDER BY next_due_date, name"

    rows = conn.execute(query).fetchall()
    return [dict(r) for r in rows]


def generate_cashflow_projection(
    conn: sqlite3.Connection,
    start_date: date,
    end_date: date,
    active_only: bool = True,
) -> list[dict]:
    if end_date < start_date:
        raise ValueError("End date must be on or after start date.")

    query = "SELECT * FROM subscriptions"
    if active_only:
        query += " WHERE is_active = 1"
    subscriptions = conn.execute(query).fetchall()

    projections: list[dict] = []
    for sub in subscriptions:
        due_date = (
            date.fromisoformat(sub["next_due_date"])
            if isinstance(sub["next_due_date"], str)
            else sub["next_due_date"]
        )
        cadence = sub["cadence"]
        interval = sub["interval"]

        while due_date < start_date:
            due_date = _advance_due_date(due_date, cadence, interval)
        while due_date <= end_date:
            projections.append(
                {
                    "subscription_id": sub["id"],
                    "name": sub["name"],
                    "due_date": due_date,
                    "amount": sub["amount"],
                    "debit_account_id": sub["debit_account_id"],
                    "credit_account_id": sub["credit_account_id"],
                    "memo": sub["memo"],
                }
            )
            due_date = _advance_due_date(due_date, cadence, interval)

    projections.sort(key=lambda item: (item["due_date"], item["name"]))
    return projections


def process_due_subscriptions(
    conn: sqlite3.Connection,
    as_of: date,
    create_entries: bool = True,
) -> list[dict]:
    as_of_str = as_of.isoformat() if isinstance(as_of, date) else as_of
    subscriptions = conn.execute(
        "SELECT * FROM subscriptions WHERE is_active = 1 AND next_due_date <= ?",
        (as_of_str,),
    ).fetchall()

    results: list[dict] = []
    for sub in subscriptions:
        due_date = (
            date.fromisoformat(sub["next_due_date"])
            if isinstance(sub["next_due_date"], str)
            else sub["next_due_date"]
        )
        cadence = sub["cadence"]
        interval = sub["interval"]

        while due_date <= as_of:
            entry_id = None
            if create_entries and sub["auto_create_journal"]:
                entry = JournalEntryInput(
                    entry_date=due_date,
                    description=sub["name"],
                    source="subscription",
                    lines=[
                        JournalLine(
                            account_id=sub["debit_account_id"],
                            debit=float(sub["amount"]),
                            credit=0.0,
                            memo=sub["memo"],
                        ),
                        JournalLine(
                            account_id=sub["credit_account_id"],
                            debit=0.0,
                            credit=float(sub["amount"]),
                            memo=sub["memo"],
                        ),
                    ],
                )
                entry_id = create_journal_entry(conn, entry)

            results.append(
                {
                    "subscription_id": sub["id"],
                    "name": sub["name"],
                    "due_date": due_date,
                    "amount": sub["amount"],
                    "entry_id": entry_id,
                }
            )
            due_date = _advance_due_date(due_date, cadence, interval)

        conn.execute(
            "UPDATE subscriptions SET next_due_date = ?, last_run_date = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (due_date.isoformat(), as_of_str, sub["id"]),
        )

    results.sort(key=lambda item: (item["due_date"], item["name"]))
    return results
