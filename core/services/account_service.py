from __future__ import annotations

from sqlmodel import Session, func, select

from core.models import Account, Asset, JournalLine

HOUSEHOLD_GROUP_LABELS = {
    "Cash": "현금 (Cash)",
    "Bank": "은행 (Bank)",
    "Credit Card": "신용카드 (Credit Card)",
    "Investment": "투자 (Investment)",
    "Home": "주거/주택 (Home)",
    "Vehicle": "차량 (Vehicle)",
    "Household Expenses": "생활비 (Household Expenses)",
    "Income": "수입 (Income)",
    "Other": "기타 (Other)",
}

HOUSEHOLD_L1_GROUP_MAP = {
    "현금": "Cash",
    "보통예금": "Bank",
    "정기예금": "Bank",
    "증권/투자자산": "Investment",
    "부동산": "Home",
    "전세보증금(임차)": "Home",
    "차량/운송수단": "Vehicle",
    "카드미지급금": "Credit Card",
    "주택담보대출": "Home",
    "전세보증금(임대)": "Home",
}


def _resolve_l1_account_name(
    account: Account, account_lookup: dict[int, Account]
) -> str | None:
    current = account
    while current.parent_id:
        parent = account_lookup.get(int(current.parent_id))
        if parent is None:
            break
        current = parent
    return current.name if current else None


def _household_group_for(account_type: str, l1_name: str | None) -> str:
    if account_type == "INCOME":
        return "Income"
    if account_type == "EXPENSE":
        return "Household Expenses"
    if l1_name and l1_name in HOUSEHOLD_L1_GROUP_MAP:
        return HOUSEHOLD_L1_GROUP_MAP[l1_name]
    return "Other"


def list_household_accounts(
    session: Session,
    active_only: bool = True,
    include_system: bool = False,
) -> list[dict]:
    account_lookup = {
        account.id: account for account in session.exec(select(Account)).all()
    }
    statement = select(Account).where(Account.allow_posting)
    if active_only:
        statement = statement.where(Account.is_active)
    if not include_system:
        statement = statement.where(Account.is_system == 0)
    statement = statement.order_by(Account.type, Account.name)
    accounts = session.exec(statement).all()

    results = []
    for account in accounts:
        l1_name = _resolve_l1_account_name(account, account_lookup)
        group_key = _household_group_for(account.type, l1_name)
        results.append(
            {
                **account.model_dump(),
                "l1_name": l1_name,
                "household_group": group_key,
                "household_group_label": HOUSEHOLD_GROUP_LABELS[group_key],
            }
        )
    return results


def list_household_account_groups(
    session: Session,
    active_only: bool = True,
    include_system: bool = False,
) -> list[dict]:
    accounts = list_household_accounts(
        session, active_only=active_only, include_system=include_system
    )
    grouped: dict[str, list[dict]] = {key: [] for key in HOUSEHOLD_GROUP_LABELS}
    for account in accounts:
        grouped[account["household_group"]].append(account)
    return [
        {
            "group": group_key,
            "label": HOUSEHOLD_GROUP_LABELS[group_key],
            "accounts": grouped[group_key],
        }
        for group_key in HOUSEHOLD_GROUP_LABELS
    ]


def list_system_accounts_by_type(session: Session, type_: str) -> list[dict]:
    statement = (
        select(Account)
        .where(Account.type == type_, Account.is_system, Account.level == 1)
        .order_by(Account.name)
    )
    results = session.exec(statement).all()

    return [
        {
            "id": r.id,
            "name": r.name,
            "type": r.type,
            "level": r.level,
            "is_system": 1 if r.is_system else 0,
            "allow_posting": 1 if r.allow_posting else 0,
        }
        for r in results
    ]


def create_user_account(
    session: Session,
    name: str,
    type_: str,
    parent_id: int,
    is_active: bool = True,
    currency: str | None = None,
) -> int:
    parent = session.get(Account, parent_id)

    if parent is None:
        raise ValueError("상위 계정을 선택해야 합니다.")
    if parent.type != type_:
        raise ValueError("상위 계정의 타입과 동일해야 합니다.")
    if parent.type != type_:
        raise ValueError("상위 계정의 타입과 동일해야 합니다.")

    # Auto-manage: Parent becomes aggregate (allow_posting=False) if it was a leaf
    if parent.allow_posting:
        parent.allow_posting = False
        session.add(parent)

    level = parent.level + 1

    # Calculate next 6-digit ID (parent_id * 100 + sequence)
    parent_id_int = parent.id
    range_min = parent_id_int * 100 + 1
    range_max = parent_id_int * 100 + 99

    # Max ID query
    statement = select(func.max(Account.id)).where(
        Account.id >= range_min, Account.id <= range_max
    )
    max_id = session.exec(statement).one()

    new_id = max_id + 1 if max_id else range_min

    if new_id > range_max:
        raise ValueError(
            f"해당 분류({parent.name})의 하위 계정 한도(99개)를 초과했습니다."
        )

    new_account = Account(
        id=new_id,
        name=name.strip(),
        type=type_,
        parent_id=parent_id_int,
        is_active=is_active,
        is_system=False,
        level=level,
        allow_posting=True,
        currency=currency.upper() if currency else "KRW",
    )
    session.add(new_account)
    session.commit()
    session.refresh(new_account)

    return new_account.id


def update_user_account(
    session: Session,
    account_id: int,
    name: str,
    is_active: bool,
    currency: str | None = None,
) -> None:
    account = session.get(Account, account_id)

    if account is None:
        raise ValueError("계정을 찾을 수 없습니다.")
    # Removed system/posting restrictions for maximum flexibility

    account.name = name.strip()
    account.is_active = is_active
    if currency:
        account.currency = currency.upper()

    session.add(account)
    session.commit()


def delete_user_account(session: Session, account_id: int) -> None:
    account = session.get(Account, account_id)

    if account is None:
        raise ValueError("계정을 찾을 수 없습니다.")
    # Removed system/posting restrictions

    # Check children
    child_count = session.exec(
        select(func.count(Account.id)).where(Account.parent_id == account_id)
    ).one()
    if child_count > 0:
        raise ValueError("하위 계정이 있어 삭제할 수 없습니다.")

    # Check journal lines
    line_count = session.exec(
        select(func.count(JournalLine.id)).where(JournalLine.account_id == account_id)
    ).one()
    if line_count > 0:
        raise ValueError("전표에 사용된 계정은 삭제할 수 없습니다.")

    # Check linked assets
    linked_asset = session.exec(
        select(Asset).where(Asset.linked_account_id == account_id)
    ).first()
    if linked_asset:
        raise ValueError(
            f"이 계정은 자산 '{linked_asset.name}'에 연결되어 있어 삭제할 수 없습니다. 자산을 먼저 삭제하세요."
        )

    session.delete(account)
    session.commit()
