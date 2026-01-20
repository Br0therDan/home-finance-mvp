from __future__ import annotations
import sqlite3
from datetime import date, timedelta
from typing import List, Dict, Optional

from core.models import Loan, LoanSchedule, RepaymentMethod


def generate_loan_schedule(conn: sqlite3.Connection, loan_id: int) -> None:
    row = conn.execute("SELECT * FROM loans WHERE id = ?", (loan_id,)).fetchone()
    if not row:
        raise ValueError("Loan not found")
    loan = dict(row)

    # Clear existing schedule
    conn.execute("DELETE FROM loan_schedules WHERE loan_id = ?", (loan_id,))

    # Calculation constants
    monthly_rate = loan["interest_rate"] / 12
    principal = loan["principal_amount"]
    term = loan["term_months"]

    current_balance = principal
    schedules = []

    # Amortization calculation: M = P [ i(1 + i)^n ] / [ (1 + i)^n – 1]
    if loan["repayment_method"] == "AMORTIZATION":
        if monthly_rate > 0:
            monthly_payment = (
                principal
                * (monthly_rate * (1 + monthly_rate) ** term)
                / ((1 + monthly_rate) ** term - 1)
            )
        else:
            monthly_payment = principal / term

        for i in range(1, term + 1):
            interest_payment = current_balance * monthly_rate
            principal_payment = monthly_payment - interest_payment

            # Adjust last payment for rounding errors
            if i == term:
                principal_payment = current_balance
                monthly_payment = principal_payment + interest_payment

            due_date = _calculate_due_date(loan["start_date"], i, loan["payment_day"])

            # Handle grace period (interest only during grace period)
            if i <= loan["grace_period_months"]:
                principal_payment = 0
                total_payment = interest_payment
            else:
                total_payment = monthly_payment

            current_balance -= principal_payment

            schedules.append(
                (
                    loan_id,
                    due_date.isoformat() if isinstance(due_date, date) else due_date,
                    i,
                    round(principal_payment, 2),
                    round(interest_payment, 2),
                    round(total_payment, 2),
                    round(max(0, current_balance), 2),
                    "PENDING",
                )
            )

    elif loan["repayment_method"] == "BULLET":
        # Principal paid at the end, interest paid monthly
        for i in range(1, term + 1):
            interest_payment = current_balance * monthly_rate
            principal_payment = 0

            if i == term:
                principal_payment = principal

            due_date = _calculate_due_date(loan["start_date"], i, loan["payment_day"])
            current_balance -= principal_payment

            schedules.append(
                (
                    loan_id,
                    due_date.isoformat() if isinstance(due_date, date) else due_date,
                    i,
                    round(principal_payment, 2),
                    round(interest_payment, 2),
                    round(principal_payment + interest_payment, 2),
                    round(max(0, current_balance), 2),
                    "PENDING",
                )
            )

    elif loan["repayment_method"] == "INTEREST_ONLY":
        for i in range(1, term + 1):
            interest_payment = current_balance * monthly_rate
            due_date = _calculate_due_date(loan["start_date"], i, loan["payment_day"])

            schedules.append(
                (
                    loan_id,
                    due_date.isoformat() if isinstance(due_date, date) else due_date,
                    i,
                    0.0,
                    round(interest_payment, 2),
                    round(interest_payment, 2),
                    round(current_balance, 2),
                    "PENDING",
                )
            )

    for s in schedules:
        conn.execute(
            """INSERT INTO loan_schedules (loan_id, due_date, installment_number, principal_payment, 
                                          interest_payment, total_payment, remaining_balance, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            s,
        )


def _calculate_due_date(start_date: Any, month_offset: int, payment_day: int) -> date:
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)

    year = start_date.year + (start_date.month + month_offset - 1) // 12
    month = (start_date.month + month_offset - 1) % 12 + 1

    import calendar

    _, last_day = calendar.monthrange(year, month)
    day = min(payment_day, last_day)

    return date(year, month, day)


def get_loan_summary(conn: sqlite3.Connection, loan_id: int) -> dict:
    row = conn.execute("SELECT * FROM loans WHERE id = ?", (loan_id,)).fetchone()
    if not row:
        return {}
    loan = dict(row)

    schedules_rows = conn.execute(
        "SELECT * FROM loan_schedules WHERE loan_id = ? ORDER BY installment_number",
        (loan_id,),
    ).fetchall()
    schedules = [dict(r) for r in schedules_rows]

    paid_schedules = [s for s in schedules if s["status"] == "PAID"]
    remaining_schedules = [s for s in schedules if s["status"] == "PENDING"]

    total_interest = sum(s["interest_payment"] for s in schedules)
    paid_principal = sum(s["principal_payment"] for s in paid_schedules)

    return {
        "loan_name": loan["name"],
        "principal": loan["principal_amount"],
        "interest_rate": loan["interest_rate"],
        "term_months": loan["term_months"],
        "total_interest": round(total_interest, 2),
        "total_repayment": round(loan["principal_amount"] + total_interest, 2),
        "paid_principal": round(paid_principal, 2),
        "remaining_principal": round(loan["principal_amount"] - paid_principal, 2),
        "next_payment": remaining_schedules[0] if remaining_schedules else None,
        "schedules": schedules,
    }


def list_loans(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM loans ORDER BY start_date DESC").fetchall()
    return [dict(r) for r in rows]


def create_loan(conn: sqlite3.Connection, loan_data: dict) -> int:
    cursor = conn.execute(
        """INSERT INTO loans (name, asset_id, liability_account_id, principal_amount, interest_rate, 
                            term_months, start_date, repayment_method, payment_day, grace_period_months, note)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            loan_data["name"],
            loan_data.get("asset_id"),
            loan_data["liability_account_id"],
            loan_data["principal_amount"],
            loan_data["interest_rate"],
            loan_data["term_months"],
            (
                loan_data["start_date"].isoformat()
                if isinstance(loan_data["start_date"], date)
                else loan_data["start_date"]
            ),
            loan_data["repayment_method"],
            loan_data["payment_day"],
            loan_data["grace_period_months"],
            loan_data.get("note", ""),
        ),
    )
    loan_id = cursor.lastrowid
    generate_loan_schedule(conn, loan_id)
    return loan_id
