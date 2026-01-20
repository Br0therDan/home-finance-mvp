from __future__ import annotations

from datetime import date

from sqlmodel import select

from core.models import JournalEntry, Subscription
from core.services.account_service import create_user_account
from core.services.subscription_service import (
    create_subscription,
    generate_cashflow_projection,
    process_due_subscriptions,
)


def test_generate_projection_monthly(session, basic_accounts):
    asset_parent_id = basic_accounts["현금"]
    expense_parent_id = basic_accounts["비용"]

    cash_id = create_user_account(session, "월급통장", "ASSET", asset_parent_id)
    rent_id = create_user_account(session, "월세", "EXPENSE", expense_parent_id)

    create_subscription(
        session,
        name="월세",
        cadence="monthly",
        interval=1,
        next_due_date=date(2026, 1, 15),
        amount=550000.0,
        debit_account_id=rent_id,
        credit_account_id=cash_id,
        memo="Rent",
    )

    projections = generate_cashflow_projection(
        session, start_date=date(2026, 1, 1), end_date=date(2026, 3, 31)
    )

    due_dates = [item["due_date"] for item in projections]
    assert due_dates == [date(2026, 1, 15), date(2026, 2, 15), date(2026, 3, 15)]


def test_process_due_subscriptions_creates_entries(session, basic_accounts):
    asset_parent_id = basic_accounts["현금"]
    expense_parent_id = basic_accounts["비용"]

    cash_id = create_user_account(session, "생활비통장", "ASSET", asset_parent_id)
    gym_id = create_user_account(session, "헬스장", "EXPENSE", expense_parent_id)

    create_subscription(
        session,
        name="헬스장",
        cadence="monthly",
        interval=1,
        next_due_date=date(2026, 1, 1),
        amount=120000.0,
        debit_account_id=gym_id,
        credit_account_id=cash_id,
        memo="Gym",
        auto_create_journal=True,
    )

    results = process_due_subscriptions(
        session, as_of=date(2026, 2, 1), create_entries=True
    )

    assert len(results) == 2
    subscriptions = session.exec(select(Subscription)).all()
    assert subscriptions[0].next_due_date == date(2026, 3, 1)

    entries = session.exec(
        select(JournalEntry).where(JournalEntry.source == "subscription")
    ).all()
    assert len(entries) == 2
