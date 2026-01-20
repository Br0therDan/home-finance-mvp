from __future__ import annotations

from datetime import date

import pytest
from sqlmodel import select

from core.models import JournalEntryInput, JournalLine
from core.services.account_service import create_user_account
from core.services.ledger_service import create_journal_entry


def test_multi_currency_journal_entry(session, basic_accounts):
    l1_asset_id = basic_accounts["현금"]
    l1_equity_id = basic_accounts["자본"]

    create_user_account(session, "신한KRW", "ASSET", l1_asset_id, currency="KRW")
    usd_acc_id = create_user_account(
        session, "신한USD", "ASSET", l1_asset_id, currency="USD"
    )
    eq_acc_id = create_user_account(
        session, "자본금", "EQUITY", l1_equity_id, currency="KRW"
    )

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

    entry_id = create_journal_entry(session, entry)
    assert entry_id > 0

    lines = session.exec(
        select(JournalLine).where(JournalLine.entry_id == entry_id)
    ).all()
    fx_lines = [line for line in lines if line.native_currency == "USD"]
    assert len(fx_lines) == 1
    assert fx_lines[0].native_amount == 1000.0
    assert fx_lines[0].fx_rate == 1330.0


def test_unbalanced_multi_currency_entry_fails(session, basic_accounts):
    l1_asset_id = basic_accounts["현금"]
    usd_acc_id = create_user_account(
        session, "TestUSD", "ASSET", l1_asset_id, currency="USD"
    )
    krw_acc_id = create_user_account(
        session, "TestKRW", "ASSET", l1_asset_id, currency="KRW"
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
                account_id=krw_acc_id,
                debit=0.0,
                credit=999.0,
            ),
        ],
    )

    with pytest.raises(ValueError, match="Unbalanced entry"):
        create_journal_entry(session, entry)
