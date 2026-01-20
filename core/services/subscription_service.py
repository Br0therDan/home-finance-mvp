from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

from sqlmodel import Session, select

from core.models import Account, JournalEntryInput, JournalLine, Subscription
from core.services.ledger_service import create_journal_entry

CADENCE_OPTIONS = {"daily", "weekly", "monthly", "quarterly", "yearly"}


def _validate_cadence(cadence: str, interval: int) -> None:
    if cadence not in CADENCE_OPTIONS:
        raise ValueError(
            "Cadence must be one of daily/weekly/monthly/quarterly/yearly."
        )
    if interval < 1:
        raise ValueError("Interval must be at least 1.")


def _validate_accounts(session: Session, debit_account_id: int, credit_account_id: int):
    debit_account = session.get(Account, debit_account_id)
    credit_account = session.get(Account, credit_account_id)
    if debit_account is None or credit_account is None:
        raise ValueError("Invalid account selection.")
    if not debit_account.allow_posting or not credit_account.allow_posting:
        raise ValueError("Accounts must allow posting.")


def _add_months(current: date, months: int) -> date:
    month_index = current.month - 1 + months
    year = current.year + month_index // 12
    month = month_index % 12 + 1
    day = min(current.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _advance_due_date(current: date, cadence: str, interval: int) -> date:
    if cadence == "daily":
        return current + timedelta(days=interval)
    if cadence == "weekly":
        return current + timedelta(days=7 * interval)
    if cadence == "monthly":
        return _add_months(current, interval)
    if cadence == "quarterly":
        return _add_months(current, 3 * interval)
    if cadence == "yearly":
        return _add_months(current, 12 * interval)
    raise ValueError("Unsupported cadence.")


def create_subscription(
    session: Session,
    *,
    name: str,
    cadence: str,
    interval: int,
    next_due_date: date,
    amount: float,
    debit_account_id: int,
    credit_account_id: int,
    memo: str = "",
    is_active: bool = True,
    auto_create_journal: bool = False,
) -> int:
    _validate_cadence(cadence, interval)
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    _validate_accounts(session, debit_account_id, credit_account_id)

    subscription = Subscription(
        name=name.strip(),
        cadence=cadence,
        interval=interval,
        next_due_date=next_due_date,
        amount=float(amount),
        debit_account_id=debit_account_id,
        credit_account_id=credit_account_id,
        memo=memo.strip(),
        is_active=is_active,
        auto_create_journal=auto_create_journal,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    session.add(subscription)
    session.commit()
    session.refresh(subscription)
    return subscription.id


def list_subscriptions(session: Session, active_only: bool = True) -> list[dict]:
    statement = select(Subscription)
    if active_only:
        statement = statement.where(Subscription.is_active)
    statement = statement.order_by(Subscription.next_due_date, Subscription.name)
    results = session.exec(statement).all()
    return [r.model_dump() for r in results]


def generate_cashflow_projection(
    session: Session,
    start_date: date,
    end_date: date,
    active_only: bool = True,
) -> list[dict]:
    if end_date < start_date:
        raise ValueError("End date must be on or after start date.")

    statement = select(Subscription)
    if active_only:
        statement = statement.where(Subscription.is_active)
    subscriptions = session.exec(statement).all()

    projections: list[dict] = []
    for sub in subscriptions:
        due_date = sub.next_due_date
        while due_date < start_date:
            due_date = _advance_due_date(due_date, sub.cadence, sub.interval)
        while due_date <= end_date:
            projections.append(
                {
                    "subscription_id": sub.id,
                    "name": sub.name,
                    "due_date": due_date,
                    "amount": sub.amount,
                    "debit_account_id": sub.debit_account_id,
                    "credit_account_id": sub.credit_account_id,
                    "memo": sub.memo,
                }
            )
            due_date = _advance_due_date(due_date, sub.cadence, sub.interval)

    projections.sort(key=lambda item: (item["due_date"], item["name"]))
    return projections


def process_due_subscriptions(
    session: Session,
    as_of: date,
    create_entries: bool = True,
) -> list[dict]:
    statement = select(Subscription).where(
        Subscription.is_active, Subscription.next_due_date <= as_of
    )
    subscriptions = session.exec(statement).all()

    results: list[dict] = []
    for sub in subscriptions:
        due_date = sub.next_due_date
        while due_date <= as_of:
            entry_id = None
            if create_entries and sub.auto_create_journal:
                entry = JournalEntryInput(
                    entry_date=due_date,
                    description=sub.name,
                    source="subscription",
                    lines=[
                        JournalLine(
                            account_id=sub.debit_account_id,
                            debit=float(sub.amount),
                            credit=0.0,
                            memo=sub.memo,
                        ),
                        JournalLine(
                            account_id=sub.credit_account_id,
                            debit=0.0,
                            credit=float(sub.amount),
                            memo=sub.memo,
                        ),
                    ],
                )
                entry_id = create_journal_entry(session, entry)

            results.append(
                {
                    "subscription_id": sub.id,
                    "name": sub.name,
                    "due_date": due_date,
                    "amount": sub.amount,
                    "entry_id": entry_id,
                }
            )
            due_date = _advance_due_date(due_date, sub.cadence, sub.interval)

        sub.next_due_date = due_date
        sub.last_run_date = as_of
        sub.updated_at = datetime.now()
        session.add(sub)

    session.commit()
    results.sort(key=lambda item: (item["due_date"], item["name"]))
    return results
