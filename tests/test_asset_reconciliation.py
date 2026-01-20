from __future__ import annotations

from datetime import date

from sqlmodel import Session

from core.models import Account, Asset, JournalEntryInput, JournalLine
from core.services.asset_service import reconcile_asset_valuations_with_ledger
from core.services.fx_service import save_rate
from core.services.ledger_service import create_journal_entry
from core.services.valuation_service import ValuationService


def _create_posting_accounts(session: Session) -> dict[str, int]:
    asset_account = Account(
        id=1200,
        name="투자자산",
        type="ASSET",
        parent_id=None,
        is_active=True,
        is_system=False,
        level=2,
        allow_posting=True,
        currency="KRW",
    )
    equity_account = Account(
        id=3100,
        name="자본조정",
        type="EQUITY",
        parent_id=None,
        is_active=True,
        is_system=False,
        level=2,
        allow_posting=True,
        currency="KRW",
    )
    session.add_all([asset_account, equity_account])
    session.commit()
    return {"asset": asset_account.id, "equity": equity_account.id}


def test_reconcile_asset_valuations_with_ledger(session: Session) -> None:
    accounts = _create_posting_accounts(session)

    asset = Asset(
        name="테스트 자산",
        asset_class="STOCK",
        linked_account_id=accounts["asset"],
        acquisition_date=date(2024, 1, 1),
        acquisition_cost=1000.0,
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)

    entry_input = JournalEntryInput(
        entry_date=date(2024, 1, 1),
        description="자산 취득",
        source="manual",
        lines=[
            JournalLine(account_id=accounts["asset"], debit=1000.0, credit=0.0),
            JournalLine(account_id=accounts["equity"], debit=0.0, credit=1000.0),
        ],
    )
    create_journal_entry(session, entry_input)

    save_rate(session, base="KRW", quote="USD", rate=1000.0)
    val_service = ValuationService(session)
    val_service.upsert_asset_valuation(
        asset_id=asset.id,
        as_of_date=date(2024, 1, 31),
        value_native=1.0,
        currency="USD",
    )

    reconciliation = reconcile_asset_valuations_with_ledger(
        session, as_of=date(2024, 1, 31)
    )

    assert reconciliation["base_currency"] == "KRW"
    assert reconciliation["missing_rates"] == []
    assert reconciliation["total_book_value_base"] == 1000.0
    assert reconciliation["total_valuation_value_base"] == 1000.0
    assert reconciliation["total_delta_base"] == 0.0
    assert reconciliation["items"][0]["valued_asset_count"] == 1


def test_reconcile_asset_valuations_missing_fx(session: Session) -> None:
    accounts = _create_posting_accounts(session)

    asset = Asset(
        name="테스트 자산 2",
        asset_class="STOCK",
        linked_account_id=accounts["asset"],
        acquisition_date=date(2024, 2, 1),
        acquisition_cost=500.0,
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)

    entry_input = JournalEntryInput(
        entry_date=date(2024, 2, 1),
        description="자산 취득",
        source="manual",
        lines=[
            JournalLine(account_id=accounts["asset"], debit=500.0, credit=0.0),
            JournalLine(account_id=accounts["equity"], debit=0.0, credit=500.0),
        ],
    )
    create_journal_entry(session, entry_input)

    val_service = ValuationService(session)
    val_service.upsert_asset_valuation(
        asset_id=asset.id,
        as_of_date=date(2024, 2, 28),
        value_native=1.0,
        currency="USD",
    )

    reconciliation = reconcile_asset_valuations_with_ledger(
        session, as_of=date(2024, 2, 28)
    )

    assert reconciliation["total_book_value_base"] == 500.0
    assert reconciliation["total_valuation_value_base"] == 0.0
    assert reconciliation["missing_rates"] == [("KRW", "USD")]
