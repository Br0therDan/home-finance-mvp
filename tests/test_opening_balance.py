from __future__ import annotations

import sqlite3
from datetime import date

from core.db import apply_migrations
from core.models import JournalLine
from core.services.ledger_service import create_opening_balance_entry


def test_opening_balance_balanced():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    apply_migrations(conn)

    cash = conn.execute(
        "SELECT id FROM accounts WHERE name = '현금' AND type = 'ASSET'"
    ).fetchone()
    loan = conn.execute(
        "SELECT id FROM accounts WHERE name = '대출금' AND type = 'LIABILITY'"
    ).fetchone()

    assert cash is not None
    assert loan is not None

    entry_id = create_opening_balance_entry(
        conn,
        entry_date=date(2026, 1, 1),
        description="OPENING_BALANCE",
        asset_lines=[JournalLine(account_id=int(cash["id"]), debit=1_000_000.0)],
        liability_lines=[JournalLine(account_id=int(loan["id"]), credit=200_000.0)],
    )

    rows = conn.execute(
        "SELECT debit, credit FROM journal_lines WHERE entry_id = ?",
        (int(entry_id),),
    ).fetchall()
    total_debit = sum(float(r["debit"]) for r in rows)
    total_credit = sum(float(r["credit"]) for r in rows)

    assert round(total_debit, 2) == round(total_credit, 2)
