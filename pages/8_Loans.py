from datetime import date
import streamlit as st
from sqlmodel import Session
from core.db import engine
from core.models import Loan, Account, RepaymentMethod
from core.services.loan_service import generate_loan_schedule, get_loan_summary
import pandas as pd

st.set_page_config(page_title="Loans", page_icon="🏦", layout="wide")

session = Session(engine)

st.title("부채 및 대출 관리")

# Tab Interface
tabs = st.tabs(["대출 목록", "신규 대출 등록", "상환 일정"])

with tabs[0]:
    loans = session.exec(select(Loan)).all()
    if not loans:
        st.info("등록된 대출이 없습니다.")
    else:
        for loan in loans:
            summary = get_loan_summary(session, loan.id)
            with st.expander(
                f"🏦 {loan.name} ({summary['remaining_principal']:,} / {loan.principal_amount:,} KRW)"
            ):
                col1, col2 = st.columns(2)
                col1.write(f"**총 상환액:** {summary['total_repayment']:,} KRW")
                col1.write(f"**총 이자:** {summary['total_interest']:,} KRW")
                col2.write(f"**상환 방식:** {loan.repayment_method}")
                col2.write(f"**이자율:** {loan.interest_rate * 100}%")

                if summary["next_payment"]:
                    st.info(
                        f"다음 상환일: {summary['next_payment'].due_date} (금액: {summary['next_payment'].total_payment:,})"
                    )

with tabs[1]:
    with st.form("new_loan_form"):
        name = st.text_input("대출명", placeholder="○○은행 주택담보대출")
        col1, col2 = st.columns(2)
        principal = col1.number_input("대출 원금", min_value=0.0, step=1000000.0)
        rate = col2.number_input("연 이자율 (%)", min_value=0.0, step=0.1) / 100

        col3, col4 = st.columns(2)
        term = col3.number_input("대출 기간 (개월)", min_value=1, value=36)
        start_date = col4.date_input("대출 시작일", value=date.today())

        method = st.selectbox(
            "상환 방식",
            [
                RepaymentMethod.AMORTIZATION,
                RepaymentMethod.BULLET,
                RepaymentMethod.INTEREST_ONLY,
            ],
        )

        accounts = session.exec(
            select(Account).where(Account.type == "LIABILITY")
        ).all()
        liab_acc_id = st.selectbox(
            "연결 부채 계정",
            options=[a.id for a in accounts],
            format_func=lambda x: next(a.name for a in accounts if a.id == x),
        )

        if st.form_submit_button("대출 등록"):
            new_loan = Loan(
                name=name,
                principal_amount=principal,
                interest_rate=rate,
                term_months=int(term),
                start_date=start_date,
                repayment_method=method,
                liability_account_id=liab_acc_id,
            )
            session.add(new_loan)
            session.commit()
            session.refresh(new_loan)

            generate_loan_schedule(session, new_loan.id)
            st.success(f"대출 '{name}'이 등록되고 상환 일정이 생성되었습니다.")
            st.rerun()

with tabs[2]:
    # Integrated view of all loan schedules
    from core.models import LoanSchedule

    schedules = session.exec(
        select(LoanSchedule, Loan).join(Loan).order_by(LoanSchedule.due_date)
    ).all()

    if not schedules:
        st.info("상환 일정이 없습니다.")
    else:
        sched_data = []
        for s, l in schedules:
            sched_data.append(
                {
                    "대출명": l.name,
                    "상환일": s.due_date,
                    "회차": s.installment_number,
                    "납입원금": s.principal_payment,
                    "이자": s.interest_payment,
                    "합계": s.total_payment,
                    "잔액": s.remaining_balance,
                    "상태": s.status,
                }
            )

        df = pd.DataFrame(sched_data)
        st.dataframe(
            df.style.format(
                {
                    "납입원금": "{:,.0f}",
                    "이자": "{:,.0f}",
                    "합계": "{:,.0f}",
                    "잔액": "{:,.0f}",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )

from sqlmodel import select  # Ensure select is imported for tabs[0]
