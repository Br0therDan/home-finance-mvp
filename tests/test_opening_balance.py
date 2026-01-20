from __future__ import annotations

from datetime import date

from sqlmodel import select

from core.models import JournalLine
from core.services.account_service import create_user_account
from core.services.ledger_service import create_opening_balance_entry


def test_opening_balance_balanced(session, basic_accounts):
    asset_parent_id = basic_accounts["현금"]
    liab_parent_id = basic_accounts["대출금"]

    cash_leaf_id = create_user_account(
        session, "지갑현금", "ASSET", asset_parent_id, currency="KRW"
    )
    loan_leaf_id = create_user_account(
        session, "대출-은행A", "LIABILITY", liab_parent_id, currency="KRW"
    )

    entry_id = create_opening_balance_entry(
        session,
        entry_date=date(2026, 1, 1),
        description="OPENING_BALANCE",
        asset_lines=[JournalLine(account_id=cash_leaf_id, debit=1_000_000.0)],
        liability_lines=[JournalLine(account_id=loan_leaf_id, credit=200_000.0)],
    )

    rows = session.exec(
        select(JournalLine.debit, JournalLine.credit).where(
            JournalLine.entry_id == entry_id
        )
    ).all()
    total_debit = sum(float(r[0]) for r in rows)
    total_credit = sum(float(r[1]) for r in rows)

    assert round(total_debit, 2) == round(total_credit, 2)
