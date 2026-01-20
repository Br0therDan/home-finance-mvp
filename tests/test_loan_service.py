from datetime import date
from sqlmodel import Session
from core.models import Loan, RepaymentMethod
from core.services.loan_service import generate_loan_schedule, get_loan_summary


def test_generate_loan_schedule_amortization(session: Session):
    loan = Loan(
        name="Test Amortization",
        principal_amount=12000000,
        interest_rate=0.036,  # 3.6%
        term_months=12,
        start_date=date(2024, 1, 1),
        repayment_method=RepaymentMethod.AMORTIZATION,
        liability_account_id=2100,  # Assuming a valid liability account ID from seed
    )
    session.add(loan)
    session.commit()
    session.refresh(loan)

    generate_loan_schedule(session, loan.id)

    summary = get_loan_summary(session, loan.id)
    assert summary["total_interest"] > 0
    assert summary["remaining_principal"] == 12000000

    # 3.6% / 12 = 0.3% per month.
    # M = 12M * (0.003 * 1.003^12) / (1.003^12 - 1) approx 1,019,655
    assert summary["total_repayment"] > 12000000


def test_generate_loan_schedule_bullet(session: Session):
    loan = Loan(
        name="Test Bullet",
        principal_amount=10000000,
        interest_rate=0.05,
        term_months=12,
        start_date=date(2024, 1, 1),
        repayment_method=RepaymentMethod.BULLET,
        liability_account_id=2100,
    )
    session.add(loan)
    session.commit()
    session.refresh(loan)

    generate_loan_schedule(session, loan.id)

    summary = get_loan_summary(session, loan.id)
    # 10M * 0.05 approx 500,000 total interest
    assert 499999 < summary["total_interest"] < 500001
