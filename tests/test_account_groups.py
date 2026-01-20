from __future__ import annotations

from sqlmodel import Session

from core.models import Account
from core.services.account_service import list_household_accounts


def test_household_groups_hide_system_accounts(session: Session) -> None:
    accounts = [
        Account(
            id=1000,
            name="현금",
            type="ASSET",
            parent_id=None,
            is_active=True,
            is_system=True,
            level=1,
            allow_posting=False,
            currency="KRW",
        ),
        Account(
            id=2000,
            name="카드미지급금",
            type="LIABILITY",
            parent_id=None,
            is_active=True,
            is_system=True,
            level=1,
            allow_posting=False,
            currency="KRW",
        ),
        Account(
            id=3000,
            name="자본/순자산",
            type="EQUITY",
            parent_id=None,
            is_active=True,
            is_system=True,
            level=1,
            allow_posting=False,
            currency="KRW",
        ),
        Account(
            id=4100,
            name="근로/급여수익",
            type="INCOME",
            parent_id=None,
            is_active=True,
            is_system=True,
            level=1,
            allow_posting=False,
            currency="KRW",
        ),
        Account(
            id=5100,
            name="식비",
            type="EXPENSE",
            parent_id=None,
            is_active=True,
            is_system=True,
            level=1,
            allow_posting=False,
            currency="KRW",
        ),
        Account(
            id=100001,
            name="지갑현금",
            type="ASSET",
            parent_id=1000,
            is_active=True,
            is_system=False,
            level=2,
            allow_posting=True,
            currency="KRW",
        ),
        Account(
            id=200001,
            name="삼성카드",
            type="LIABILITY",
            parent_id=2000,
            is_active=True,
            is_system=False,
            level=2,
            allow_posting=True,
            currency="KRW",
        ),
        Account(
            id=410001,
            name="급여",
            type="INCOME",
            parent_id=4100,
            is_active=True,
            is_system=False,
            level=2,
            allow_posting=True,
            currency="KRW",
        ),
        Account(
            id=510001,
            name="외식",
            type="EXPENSE",
            parent_id=5100,
            is_active=True,
            is_system=False,
            level=2,
            allow_posting=True,
            currency="KRW",
        ),
        Account(
            id=300101,
            name="기초순자산(Opening Equity)",
            type="EQUITY",
            parent_id=3000,
            is_active=True,
            is_system=True,
            level=2,
            allow_posting=True,
            currency="KRW",
        ),
    ]
    session.add_all(accounts)
    session.commit()

    household_accounts = list_household_accounts(session, active_only=True)
    account_map = {account["name"]: account for account in household_accounts}

    assert "기초순자산(Opening Equity)" not in account_map
    assert account_map["지갑현금"]["household_group"] == "Cash"
    assert account_map["삼성카드"]["household_group"] == "Credit Card"
    assert account_map["급여"]["household_group"] == "Income"
    assert account_map["외식"]["household_group"] == "Household Expenses"
