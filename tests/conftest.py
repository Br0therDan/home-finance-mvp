from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if ROOT.as_posix() not in sys.path:
    sys.path.insert(0, ROOT.as_posix())

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from core.models import Account


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def basic_accounts(session: Session):
    accounts = [
        Account(
            id=1100,
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
            id=2100,
            name="대출금",
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
            name="자본",
            type="EQUITY",
            parent_id=None,
            is_active=True,
            is_system=True,
            level=1,
            allow_posting=False,
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
        Account(
            id=4100,
            name="수익",
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
            name="비용",
            type="EXPENSE",
            parent_id=None,
            is_active=True,
            is_system=True,
            level=1,
            allow_posting=False,
            currency="KRW",
        ),
    ]
    session.add_all(accounts)
    session.commit()
    return {account.name: account.id for account in accounts}
