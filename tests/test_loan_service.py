from datetime import date

from core.models import RepaymentMethod
from core.services.loan_service import generate_loan_schedule, get_loan_summary


def test_generate_loan_schedule_amortization(conn):
    conn.execute(
        """INSERT INTO loans (name, principal_amount, interest_rate, term_months, start_date, repayment_method, liability_account_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            "Test Amortization",
            12000000,
            0.036,
            12,
            date(2024, 1, 1).isoformat(),
            RepaymentMethod.AMORTIZATION,
            2100,
        ),
    )
    loan_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()

    generate_loan_schedule(conn, loan_id)

    summary = get_loan_summary(conn, loan_id)
    assert summary["total_interest"] > 0
    assert summary["remaining_principal"] == 12000000

    # 3.6% / 12 = 0.3% per month.
    # M = 12M * (0.003 * 1.003^12) / (1.003^12 - 1) approx 1,019,655
    assert summary["total_repayment"] > 12000000


def test_generate_loan_schedule_bullet(conn):
    conn.execute(
        """INSERT INTO loans (name, principal_amount, interest_rate, term_months, start_date, repayment_method, liability_account_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            "Test Bullet",
            10000000,
            0.05,
            12,
            date(2024, 1, 1).isoformat(),
            RepaymentMethod.BULLET,
            2100,
        ),
    )
    loan_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()

    generate_loan_schedule(conn, loan_id)

    summary = get_loan_summary(conn, loan_id)
    # 10M * 0.05 approx 500,000 total interest
    assert 499999 < summary["total_interest"] < 500001
