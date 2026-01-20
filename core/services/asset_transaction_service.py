from __future__ import annotations

import sqlite3
from datetime import date

from core.models import JournalEntryInput, JournalLine
from core.services.asset_service import create_asset
from core.services.ledger_service import create_journal_entry


def purchase_asset(
    conn: sqlite3.Connection,
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
        conn,
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
    create_journal_entry(conn, entry)

    return asset_id


def dispose_asset(
    conn: sqlite3.Connection,
    asset_id: int,
    asset_name: str,
    linked_account_id: int,
    disposal_date: date,
    sale_price: float,
    deposit_account_id: int,
    gain_loss_account_id: int,
    book_value: float,
) -> None:
    # 1. Update Asset (disposal_date)
    conn.execute(
        "UPDATE assets SET disposal_date = ? WHERE id = ?",
        (
            (
                disposal_date.isoformat()
                if isinstance(disposal_date, date)
                else disposal_date
            ),
            asset_id,
        ),
    )

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
    create_journal_entry(conn, entry)
