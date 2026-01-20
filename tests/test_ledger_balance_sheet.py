from __future__ import annotations

from datetime import date

from sqlmodel import Session

from core.models import Account, JournalEntryInput, JournalLine
from core.services.fx_service import save_rate
from core.services.ledger_service import balance_sheet, create_journal_entry


def test_balance_sheet_with_fx(session: Session) -> None:
    asset_krw = Account(
        id=1400,
        name="현금",
        type="ASSET",
        parent_id=None,
        is_active=True,
        is_system=False,
        level=2,
        allow_posting=True,
        currency="KRW",
    )
    asset_usd = Account(
        id=1401,
        name="달러예금",
        type="ASSET",
        parent_id=None,
        is_active=True,
        is_system=False,
        level=2,
        allow_posting=True,
        currency="USD",
    )
    equity = Account(
        id=3400,
        name="자본",
        type="EQUITY",
        parent_id=None,
        is_active=True,
        is_system=False,
        level=2,
        allow_posting=True,
        currency="KRW",
    )
    session.add_all([asset_krw, asset_usd, equity])
    session.commit()

    entry_krw = JournalEntryInput(
        entry_date=date(2024, 1, 1),
        description="KRW 잔액",
        source="manual",
        lines=[
            JournalLine(account_id=asset_krw.id, debit=1000.0, credit=0.0),
            JournalLine(account_id=equity.id, debit=0.0, credit=1000.0),
        ],
    )
    create_journal_entry(session, entry_krw)

    entry_usd = JournalEntryInput(
        entry_date=date(2024, 1, 2),
        description="USD 잔액",
        source="manual",
        lines=[
            JournalLine(
                account_id=asset_usd.id,
                debit=1000.0,
                credit=0.0,
                native_amount=1.0,
                native_currency="USD",
                fx_rate=1000.0,
            ),
            JournalLine(account_id=equity.id, debit=0.0, credit=1000.0),
        ],
    )
    create_journal_entry(session, entry_usd)

    save_rate(session, base="KRW", quote="USD", rate=1000.0)

    bs = balance_sheet(session, as_of=date(2024, 1, 31), display_currency="KRW")

    assert bs["total_assets_base"] == 2000.0
    assert len(bs["assets"]) == 2
    assert bs["missing_rates"] == []
