from __future__ import annotations

from typing import Optional
from sqlmodel import Session, select, func
from core.models import Account, JournalLine, Asset


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

    if max_id:
        new_id = max_id + 1
    else:
        new_id = range_min

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
