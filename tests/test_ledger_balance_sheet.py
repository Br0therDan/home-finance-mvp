from datetime import date
from core.models import JournalEntryInput, JournalLine
from core.services.fx_service import save_rate
from core.services.ledger_service import balance_sheet, create_journal_entry


def test_balance_sheet_with_fx(conn) -> None:
    # Use conn.execute instead of session.add_all([asset_krw, asset_usd, equity])
    conn.execute(
        """INSERT INTO accounts (id, name, type, parent_id, is_active, is_system, level, allow_posting, currency)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (1400, "현금", "ASSET", None, 1, 0, 2, 1, "KRW"),
    )
    conn.execute(
        """INSERT INTO accounts (id, name, type, parent_id, is_active, is_system, level, allow_posting, currency)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (1401, "달러예금", "ASSET", None, 1, 0, 2, 1, "USD"),
    )
    conn.execute(
        """INSERT INTO accounts (id, name, type, parent_id, is_active, is_system, level, allow_posting, currency)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (3400, "자본", "EQUITY", None, 1, 0, 2, 1, "KRW"),
    )
    conn.commit()

    entry_krw = JournalEntryInput(
        entry_date=date(2024, 1, 1),
        description="KRW 잔액",
        source="manual",
        lines=[
            JournalLine(account_id=1400, debit=1000.0, credit=0.0),
            JournalLine(account_id=3400, debit=0.0, credit=1000.0),
        ],
    )
    create_journal_entry(conn, entry_krw)

    entry_usd = JournalEntryInput(
        entry_date=date(2024, 1, 2),
        description="USD 잔액",
        source="manual",
        lines=[
            JournalLine(
                account_id=1401,
                debit=1000.0,
                credit=0.0,
                native_amount=1.0,
                native_currency="USD",
                fx_rate=1000.0,
            ),
            JournalLine(account_id=3400, debit=0.0, credit=1000.0),
        ],
    )
    create_journal_entry(conn, entry_usd)

    save_rate(conn, base="KRW", quote="USD", rate=1000.0)

    bs = balance_sheet(conn, as_of=date(2024, 1, 31), display_currency="KRW")

    assert bs["total_assets_base"] == 2000.0
    assert len(bs["assets"]) == 2
    assert bs["missing_rates"] == []
