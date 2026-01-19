from __future__ import annotations

from datetime import date

from sqlmodel import Session

from core.models import JournalEntryInput, JournalLine
from core.services.asset_service import create_asset
from core.services.ledger_service import create_journal_entry

# Note: The original signature expected 'conn: sqlite3.Connection'.
# We update it to 'session: Session'.


def purchase_asset(
    session: Session,
    name: str,
    asset_class: str,
    asset_sub_account_id: int,
    payment_account_id: int,
    acquisition_date: date,
    acquisition_cost: float,
    note: str = "",
) -> int:
    # 1. Create Asset
    asset_id = create_asset(
        session,
        name=name,
        asset_class=asset_class,
        linked_account_id=asset_sub_account_id,
        acquisition_date=acquisition_date,
        acquisition_cost=acquisition_cost,
        note=note,
    )

    # 2. Create Journal Entry
    lines = [
        JournalLine(
            account_id=asset_sub_account_id,
            debit=acquisition_cost,
            credit=0.0,
            memo=f"자산 매입: {name}",
        ),
        JournalLine(
            account_id=payment_account_id,
            debit=0.0,
            credit=acquisition_cost,
            memo=f"자산 매입: {name}",
        ),
    ]

    entry = JournalEntryInput(
        entry_date=acquisition_date,
        description=f"자산 매입: {name}",
        source="system:asset_purchase",
        lines=lines,
    )
    create_journal_entry(session, entry)

    return asset_id


def dispose_asset(
    session: Session,
    asset_id: int,
    asset_name: str,
    linked_account_id: int,
    disposal_date: date,
    sale_price: float,
    deposit_account_id: int,
    gain_loss_account_id: int,
    book_value: float,
) -> None:
    # 1. Update Asset (disposal_date) -> Need to fetch existing fields to satisfy update_asset signature
    # Or simpler: access DB directly here or use update_asset if we have all fields.
    # Let's use direct update via model since we are in refactor mode.
    from core.models import Asset

    asset = session.get(Asset, asset_id)
    if not asset:
        raise ValueError("Asset not found")

    asset.disposal_date = disposal_date
    session.add(asset)
    session.flush()  # Keep transaction open

    # 2. Calculate Gain/Loss
    gain_loss = sale_price - book_value

    lines = [
        # Cash in (Deposit)
        JournalLine(
            account_id=deposit_account_id,
            debit=sale_price,
            credit=0.0,
            memo=f"자산 매각: {asset_name}",
        ),
        # Asset out (Book Value)
        JournalLine(
            account_id=linked_account_id,
            debit=0.0,
            credit=book_value,
            memo=f"자산 매각: {asset_name}",
        ),
    ]

    if gain_loss > 0:
        # Gain (Credit)
        lines.append(
            JournalLine(
                account_id=gain_loss_account_id,
                debit=0.0,
                credit=gain_loss,
                memo=f"처분 이익: {asset_name}",
            )
        )
    elif gain_loss < 0:
        # Loss (Debit)
        lines.append(
            JournalLine(
                account_id=gain_loss_account_id,
                debit=-gain_loss,
                credit=0.0,
                memo=f"처분 손실: {asset_name}",
            )
        )

    entry = JournalEntryInput(
        entry_date=disposal_date,
        description=f"자산 매각: {asset_name}",
        source="system:asset_disposal",
        lines=lines,
    )
    create_journal_entry(session, entry)
    session.commit()
