from datetime import date
from core.services.account_service import create_user_account
from core.services.subscription_service import (
    create_subscription,
    generate_cashflow_projection,
    process_due_subscriptions,
)


def test_generate_projection_monthly(conn, basic_accounts):
    asset_parent_id = basic_accounts["현금"]
    expense_parent_id = basic_accounts["비용"]

    cash_id = create_user_account(conn, "월급통장", "ASSET", asset_parent_id)
    rent_id = create_user_account(conn, "월세", "EXPENSE", expense_parent_id)

    create_subscription(
        conn,
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
        conn, start_date=date(2026, 1, 1), end_date=date(2026, 3, 31)
    )

    due_dates = [item["due_date"] for item in projections]
    assert due_dates == [date(2026, 1, 15), date(2026, 2, 15), date(2026, 3, 15)]


def test_process_due_subscriptions_creates_entries(conn, basic_accounts):
    asset_parent_id = basic_accounts["현금"]
    expense_parent_id = basic_accounts["비용"]

    cash_id = create_user_account(conn, "생활비통장", "ASSET", asset_parent_id)
    gym_id = create_user_account(conn, "헬스장", "EXPENSE", expense_parent_id)

    create_subscription(
        conn,
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
        conn, as_of=date(2026, 2, 1), create_entries=True
    )

    assert len(results) == 2
    subscriptions = conn.execute("SELECT * FROM subscriptions").fetchall()
    # Check date - it might be stored as string in SQLite
    sub_date = subscriptions[0]["next_due_date"]
    if isinstance(sub_date, str):
        sub_date = date.fromisoformat(sub_date)
    assert sub_date == date(2026, 3, 1)

    entries = conn.execute(
        "SELECT * FROM journal_entries WHERE source = 'subscription'"
    ).fetchall()
    assert len(entries) == 2
