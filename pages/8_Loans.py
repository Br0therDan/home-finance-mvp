from datetime import date
import pandas as pd
import streamlit as st
from core.db import Session
from core.models import RepaymentMethod
from core.services.loan_service import generate_loan_schedule, get_loan_summary

st.set_page_config(page_title="Loans", page_icon="🏦", layout="wide")

st.title("부채 및 대출 관리")

# Tab Interface
tabs = st.tabs(["대출 목록", "신규 대출 등록", "상환 일정"])

with tabs[0]:
    with Session() as session:
        loans_rows = session.execute("SELECT * FROM loans").fetchall()
    if not loans_rows:
        st.info("등록된 대출이 없습니다.")
    else:
        for loan_row in loans_rows:
            loan = dict(loan_row)
            with Session() as session:
                summary = get_loan_summary(session, loan["id"])
            with st.expander(
                f"🏦 {loan['name']} ({summary['remaining_principal']:,} / {loan['principal_amount']:,} KRW)"
            ):
                col1, col2 = st.columns(2)
                col1.write(f"**총 상환액:** {summary['total_repayment']:,} KRW")
                col1.write(f"**총 이자:** {summary['total_interest']:,} KRW")
                col2.write(f"**상환 방식:** {loan['repayment_method']}")
                col2.write(f"**이자율:** {loan['interest_rate'] * 100}%")

                if summary["next_payment"]:
                    st.info(
                        f"다음 상환일: {summary['next_payment']['due_date']} (금액: {summary['next_payment']['total_payment']:,})"
                    )

with tabs[1]:
    with st.form("new_loan_form"):
        name = st.text_input("대출명", placeholder="○○은행 주택담보대출")
        col1, col2 = st.columns(2)
        principal = col1.number_input("대출 원금", min_value=0.0, step=1000000.0)
        rate = col2.number_input("연 이자율 (%)", min_value=0.0, step=0.1) / 100

        col3, col4 = st.columns(2)
        term = col3.number_input("대출 기간 (개월)", min_value=1, value=36)
        loan_start_date = col4.date_input("대출 시작일", value=date.today())

        method = st.selectbox(
            "상환 방식",
            [
                RepaymentMethod.AMORTIZATION,
                RepaymentMethod.BULLET,
                RepaymentMethod.INTEREST_ONLY,
            ],
        )

        with Session() as session:
            accounts_rows = session.execute(
                "SELECT id, name FROM accounts WHERE type = 'LIABILITY' AND is_active = 1"
            ).fetchall()
        accounts = [dict(r) for r in accounts_rows]

        if not accounts:
            st.error("연결할 부채 계정이 없습니다. 계정을 먼저 생성하세요.")
        else:
            liab_acc_id = st.selectbox(
                "연결 부채 계정",
                options=[a["id"] for a in accounts],
                format_func=lambda x: next(a["name"] for a in accounts if a["id"] == x),
            )

            if st.form_submit_button("대출 등록"):
                try:
                    with Session() as session:
                        session.execute(
                            """INSERT INTO loans (name, principal_amount, interest_rate, term_months, start_date, repayment_method, liability_account_id)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (
                                name,
                                principal,
                                rate,
                                int(term),
                                loan_start_date.isoformat(),
                                method,
                                liab_acc_id,
                            ),
                        )
                        new_id = session.execute(
                            "SELECT last_insert_rowid()"
                        ).fetchone()[0]
                        session.commit()

                        generate_loan_schedule(session, new_id)
                    st.success(f"대출 '{name}'이 등록되고 상환 일정이 생성되었습니다.")
                    st.rerun()
                except Exception as e:
                    st.error(f"대출 등록 실패: {e}")

with tabs[2]:
    sql = """
        SELECT s.*, l.name as loan_name
        FROM loan_schedules s
        JOIN loans l ON l.id = s.loan_id
        ORDER BY s.due_date
    """
    with Session() as session:
        schedules_rows = session.execute(sql).fetchall()

    if not schedules_rows:
        st.info("상환 일정이 없습니다.")
    else:
        sched_data = []
        for row in schedules_rows:
            s = dict(row)
            sched_data.append(
                {
                    "대출명": s["loan_name"],
                    "상환일": s["due_date"],
                    "회차": s["installment_number"],
                    "납입원금": s["principal_payment"],
                    "이자": s["interest_payment"],
                    "합계": s["total_payment"],
                    "잔액": s["remaining_balance"],
                    "상태": s["status"],
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
