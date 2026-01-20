from __future__ import annotations

from core.services.account_service import list_household_accounts


def test_household_groups_hide_system_accounts(conn) -> None:
    accounts = [
        (1000, "현금", "ASSET", None, 1, 1, 1, 0, "KRW"),
        (2000, "카드미지급금", "LIABILITY", None, 1, 1, 1, 0, "KRW"),
        (3000, "자본/순자산", "EQUITY", None, 1, 1, 1, 0, "KRW"),
        (4100, "근로/급여수익", "INCOME", None, 1, 1, 1, 0, "KRW"),
        (5100, "식비", "EXPENSE", None, 1, 1, 1, 0, "KRW"),
        (100001, "지갑현금", "ASSET", 1000, 1, 0, 2, 1, "KRW"),
        (200001, "삼성카드", "LIABILITY", 2000, 1, 0, 2, 1, "KRW"),
        (410001, "급여", "INCOME", 4100, 1, 0, 2, 1, "KRW"),
        (510001, "외식", "EXPENSE", 5100, 1, 0, 2, 1, "KRW"),
        (300101, "기초순자산(Opening Equity)", "EQUITY", 3000, 1, 1, 2, 1, "KRW"),
    ]

    for acc in accounts:
        conn.execute(
            """INSERT INTO accounts (id, name, type, parent_id, is_active, is_system, level, allow_posting, currency)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            acc,
        )
    conn.commit()

    household_accounts = list_household_accounts(conn, active_only=True)
    account_map = {account["name"]: account for account in household_accounts}

    assert "기초순자산(Opening Equity)" not in account_map
    assert account_map["지갑현금"]["household_group"] == "Cash"
    assert account_map["삼성카드"]["household_group"] == "Credit Card"
    assert account_map["급여"]["household_group"] == "Income"
    assert account_map["외식"]["household_group"] == "Household Expenses"
