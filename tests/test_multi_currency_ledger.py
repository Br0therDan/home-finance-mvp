from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from core.db import apply_migrations
from core.models import JournalEntryInput, JournalLine
from core.services.account_service import create_user_account
from core.services.ledger_service import create_journal_entry


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    return c


@pytest.fixture
def db(conn):
    apply_migrations(conn)
    return conn


def test_multi_currency_journal_entry(db):
    # 1. Setup accounts
    # L1 accounts are seeded by migration (006)
    # Finding '보통예금' (ASSET) parent
    l1_asset = db.execute(
        "SELECT id FROM accounts WHERE name='보통예금' AND level=1"
    ).fetchone()
    l1_equity = db.execute(
        "SELECT id FROM accounts WHERE name='기초자본' AND level=1"
    ).fetchone()  # Corrected name based on seed if needed
    if not l1_equity:
        l1_equity = db.execute(
            "SELECT id FROM accounts WHERE level=1 AND type='EQUITY' LIMIT 1"
        ).fetchone()

    # Create KRW and USD accounts
    create_user_account(db, "신한KRW", "ASSET", l1_asset["id"], currency="KRW")
    usd_acc_id = create_user_account(
        db, "신한USD", "ASSET", l1_asset["id"], currency="USD"
    )
    eq_acc_id = create_user_account(
        db, "자본금", "EQUITY", l1_equity["id"], currency="KRW"
    )

    # 2. Create multi-currency entry (Funding USD account)
    # 1000 USD at 1330 rate = 1,330,000 KRW
    entry = JournalEntryInput(
        entry_date=date(2026, 1, 1),
        description="USD Funding",
        source="manual",
        lines=[
            JournalLine(
                account_id=usd_acc_id,
                debit=1330000.0,
                credit=0.0,
                memo="Deposit 1000 USD",
                native_amount=1000.0,
                native_currency="USD",
                fx_rate=1330.0,
            ),
            JournalLine(
                account_id=eq_acc_id,
                debit=0.0,
                credit=1330000.0,
                memo="Initial Capital",
            ),
        ],
    )

    entry_id = create_journal_entry(db, entry)
    assert entry_id > 0

    # 3. Verify persistence in journal_line_fx
    fx_rows = db.execute("SELECT * FROM journal_line_fx").fetchall()
    assert len(fx_rows) == 1
    assert fx_rows[0]["native_currency"] == "USD"
    assert fx_rows[0]["native_amount"] == 1000.0
    assert fx_rows[0]["fx_rate"] == 1330.0
    assert fx_rows[0]["base_amount"] == 1330000.0


def test_unbalanced_multi_currency_entry_fails(db):
    l1_asset = db.execute(
        "SELECT id FROM accounts WHERE type='ASSET' AND level=1 LIMIT 1"
    ).fetchone()
    usd_acc_id = create_user_account(
        db, "TestUSD", "ASSET", l1_asset["id"], currency="USD"
    )
    krw_acc_id = create_user_account(
        db, "TestKRW", "ASSET", l1_asset["id"], currency="KRW"
    )

    entry = JournalEntryInput(
        entry_date=date(2026, 1, 1),
        description="Unbalanced",
        source="manual",
        lines=[
            JournalLine(
                account_id=usd_acc_id,
                debit=1000.0,
                credit=0.0,
                native_amount=1.0,
                native_currency="USD",
                fx_rate=1000.0,
            ),
            JournalLine(
                account_id=krw_acc_id, debit=0.0, credit=999.0
            ),  # Unbalanced by 1 KRW
        ],
    )

    with pytest.raises(ValueError, match="Unbalanced entry"):
        create_journal_entry(db, entry)
