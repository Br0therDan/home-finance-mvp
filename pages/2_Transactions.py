from __future__ import annotations

from datetime import date

import streamlit as st

from core.db import apply_migrations, get_connection
from core.models import JournalEntryInput, JournalLine
from core.services.ledger_service import create_journal_entry, list_accounts

st.set_page_config(page_title="Transactions", page_icon="🧾", layout="wide")

conn = get_connection()
apply_migrations(conn)

st.title("거래 입력")
st.caption("가계부 형태로 입력하면 내부적으로 복식부기 분개가 자동 생성된다.")

accounts = list_accounts(conn, active_only=True)

asset_accounts = [(a["id"], a["name"]) for a in accounts if a["type"] == "ASSET"]
liab_accounts = [(a["id"], a["name"]) for a in accounts if a["type"] == "LIABILITY"]
income_accounts = [(a["id"], a["name"]) for a in accounts if a["type"] == "INCOME"]
expense_accounts = [(a["id"], a["name"]) for a in accounts if a["type"] == "EXPENSE"]

TRANSACTION_TYPES = ["지출(Expense)", "수입(Income)", "이체(Transfer)"]

with st.form("txn_form", clear_on_submit=True):
    ttype = st.selectbox("거래 유형", TRANSACTION_TYPES)
    txn_date = st.date_input("날짜", value=date.today())
    amount = st.number_input("금액", min_value=0.0, value=0.0, step=1000.0)
    memo = st.text_input("메모", value="")

    if ttype == "지출(Expense)":
        exp = st.selectbox("지출 계정(비용)", options=expense_accounts, format_func=lambda x: x[1])
        pay = st.selectbox(
            "결제 계정(현금/예금/카드)",
            options=asset_accounts + liab_accounts,
            format_func=lambda x: x[1],
        )

        submitted = st.form_submit_button("저장")
        if submitted:
            if amount <= 0:
                st.error("금액은 0보다 커야 한다.")
            else:
                entry = JournalEntryInput(
                    entry_date=txn_date,
                    description=memo or "Expense",
                    source="ui:transactions",
                    lines=[
                        JournalLine(account_id=int(exp[0]), debit=float(amount), credit=0.0, memo=memo),
                        JournalLine(account_id=int(pay[0]), debit=0.0, credit=float(amount), memo=memo),
                    ],
                )
                try:
                    eid = create_journal_entry(conn, entry)
                    st.success(f"저장 완료: 전표 #{eid}")
                except Exception as e:
                    st.error(str(e))

    elif ttype == "수입(Income)":
        inc = st.selectbox("수익 계정(Income)", options=income_accounts, format_func=lambda x: x[1])
        recv = st.selectbox("입금 계정(현금/예금)", options=asset_accounts, format_func=lambda x: x[1])

        submitted = st.form_submit_button("저장")
        if submitted:
            if amount <= 0:
                st.error("금액은 0보다 커야 한다.")
            else:
                entry = JournalEntryInput(
                    entry_date=txn_date,
                    description=memo or "Income",
                    source="ui:transactions",
                    lines=[
                        JournalLine(account_id=int(recv[0]), debit=float(amount), credit=0.0, memo=memo),
                        JournalLine(account_id=int(inc[0]), debit=0.0, credit=float(amount), memo=memo),
                    ],
                )
                try:
                    eid = create_journal_entry(conn, entry)
                    st.success(f"저장 완료: 전표 #{eid}")
                except Exception as e:
                    st.error(str(e))

    else:
        from_acct = st.selectbox(
            "출금 계정(from)",
            options=asset_accounts,
            format_func=lambda x: x[1],
        )
        to_acct = st.selectbox(
            "입금 계정(to)",
            options=asset_accounts,
            format_func=lambda x: x[1],
        )

        submitted = st.form_submit_button("저장")
        if submitted:
            if amount <= 0:
                st.error("금액은 0보다 커야 한다.")
            elif int(from_acct[0]) == int(to_acct[0]):
                st.error("from/to 계정은 달라야 한다.")
            else:
                entry = JournalEntryInput(
                    entry_date=txn_date,
                    description=memo or "Transfer",
                    source="ui:transactions",
                    lines=[
                        JournalLine(account_id=int(to_acct[0]), debit=float(amount), credit=0.0, memo=memo),
                        JournalLine(account_id=int(from_acct[0]), debit=0.0, credit=float(amount), memo=memo),
                    ],
                )
                try:
                    eid = create_journal_entry(conn, entry)
                    st.success(f"저장 완료: 전표 #{eid}")
                except Exception as e:
                    st.error(str(e))

st.divider()

st.subheader("자동 분개 규칙(요약)")
st.markdown(
    """
- **지출**: (차) 비용계정 / (대) 결제계정(현금·예금·카드부채)
- **수입**: (차) 입금계정(현금·예금) / (대) 수익계정
- **이체**: (차) to(자산) / (대) from(자산)

카드 사용은 결제계정을 `카드미지급금` 같은 **부채 계정**으로 선택하면 된다.
"""
)
