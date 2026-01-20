from datetime import date

from core.models import JournalEntryInput, JournalLine
from core.services.asset_service import reconcile_asset_valuations_with_ledger
from core.services.fx_service import save_rate
from core.services.ledger_service import create_journal_entry
from core.services.valuation_service import upsert_asset_valuation


def _create_posting_accounts(conn) -> dict[str, int]:
    conn.execute(
        """INSERT INTO accounts (id, name, type, parent_id, is_active, is_system, level, allow_posting, currency)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (1200, "투자자산", "ASSET", None, 1, 0, 2, 1, "KRW"),
    )
    conn.execute(
        """INSERT INTO accounts (id, name, type, parent_id, is_active, is_system, level, allow_posting, currency)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (3100, "자본조정", "EQUITY", None, 1, 0, 2, 1, "KRW"),
    )
    conn.commit()
    return {"asset": 1200, "equity": 3100}


def test_reconcile_asset_valuations_with_ledger(conn) -> None:
    accounts = _create_posting_accounts(conn)

    conn.execute(
        """INSERT INTO assets (name, asset_class, linked_account_id, acquisition_date, acquisition_cost, note)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            "테스트 자산",
            "STOCK",
            accounts["asset"],
            date(2024, 1, 1).isoformat(),
            1000.0,
            "",
        ),
    )
    asset_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()

    entry_input = JournalEntryInput(
        entry_date=date(2024, 1, 1),
        description="자산 취득",
        source="manual",
        lines=[
            JournalLine(account_id=accounts["asset"], debit=1000.0, credit=0.0),
            JournalLine(account_id=accounts["equity"], debit=0.0, credit=1000.0),
        ],
    )
    create_journal_entry(conn, entry_input)

    save_rate(conn, base="KRW", quote="USD", rate=1000.0)
    upsert_asset_valuation(
        conn=conn,
        asset_id=asset_id,
        as_of_date=date(2024, 1, 31),
        value_native=1.0,
        currency="USD",
    )

    reconciliation = reconcile_asset_valuations_with_ledger(
        conn, as_of=date(2024, 1, 31)
    )

    assert reconciliation["base_currency"] == "KRW"
    assert reconciliation["missing_rates"] == []
    assert reconciliation["total_book_value_base"] == 1000.0
    assert reconciliation["total_valuation_value_base"] == 1000.0
    assert reconciliation["total_delta_base"] == 0.0
    assert reconciliation["items"][0]["valued_asset_count"] == 1


def test_reconcile_asset_valuations_missing_fx(conn) -> None:
    accounts = _create_posting_accounts(conn)

    conn.execute(
        """INSERT INTO assets (name, asset_class, linked_account_id, acquisition_date, acquisition_cost, note)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            "테스트 자산 2",
            "STOCK",
            accounts["asset"],
            date(2024, 2, 1).isoformat(),
            500.0,
            "",
        ),
    )
    asset_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()

    entry_input = JournalEntryInput(
        entry_date=date(2024, 2, 1),
        description="자산 취득",
        source="manual",
        lines=[
            JournalLine(account_id=accounts["asset"], debit=500.0, credit=0.0),
            JournalLine(account_id=accounts["equity"], debit=0.0, credit=500.0),
        ],
    )
    create_journal_entry(conn, entry_input)

    upsert_asset_valuation(
        conn=conn,
        asset_id=asset_id,
        as_of_date=date(2024, 2, 28),
        value_native=1.0,
        currency="USD",
    )

    reconciliation = reconcile_asset_valuations_with_ledger(
        conn, as_of=date(2024, 2, 28)
    )

    assert reconciliation["total_book_value_base"] == 500.0
    assert reconciliation["total_valuation_value_base"] == 0.0
    assert reconciliation["missing_rates"] == [("KRW", "USD")]
