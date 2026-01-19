from __future__ import annotations

from datetime import date

import streamlit as st

from core.db import apply_migrations, get_connection
from core.models import JournalEntryInput, JournalLine
from core.services.ledger_service import create_journal_entry, list_posting_accounts

st.set_page_config(page_title="Transactions", page_icon="🧾", layout="wide")

conn = get_connection()
apply_migrations(conn)

st.title("거래 입력")
st.caption("가계부 형태로 입력하면 내부적으로 복식부기 분개가 자동 생성된다.")

accounts = list_posting_accounts(conn, active_only=True)

if len(accounts) == 0:
    st.info(
        "Posting 가능한 하위 계정이 없습니다. 설정에서 하위 계정을 먼저 생성하세요."
    )
    st.stop()

asset_accounts = [tuple(a) for a in accounts if a["type"] == "ASSET"]
liab_accounts = [tuple(a) for a in accounts if a["type"] == "LIABILITY"]
income_accounts = [tuple(a) for a in accounts if a["type"] == "INCOME"]
expense_accounts = [tuple(a) for a in accounts if a["type"] == "EXPENSE"]

TRANSACTION_TYPES = ["지출(Expense)", "수입(Income)", "이체(Transfer)"]

with st.form("txn_form", clear_on_submit=True):
    ttype = st.selectbox("거래 유형", TRANSACTION_TYPES)
    txn_date = st.date_input("날짜", value=date.today())
    amount = st.number_input("금액", min_value=0.0, value=0.0, step=1000.0)
    memo = st.text_input("메모", value="")

    from core.services.fx_service import get_latest_rate
    from core.services.settings_service import get_base_currency

    base_cur = get_base_currency(conn)

    if ttype == "지출(Expense)":
        exp = st.selectbox(
            "지출 계정(비용)", options=expense_accounts, format_func=lambda x: x[1]
        )
        pay = st.selectbox(
            "결제 계정(현금/예금/카드)",
            options=asset_accounts + liab_accounts,
            format_func=lambda x: x[1],
        )

        # FX Handling
        (
            pay_id,
            pay_name,
            pay_type,
            pay_parent_id,
            pay_active,
            pay_system,
            pay_level,
            pay_posting,
            pay_currency,
        ) = pay
        is_fx = pay_currency != base_cur

        native_amount = 0.0
        fx_rate = 1.0
        if is_fx:
            col1, col2 = st.columns(2)
            with col1:
                native_amount = st.number_input(
                    f"외화 금액 ({pay_currency})", min_value=0.0, value=0.0, step=1.0
                )
            with col2:
                latest_rate = get_latest_rate(conn, base_cur, pay_currency)
                fx_rate = st.number_input(
                    "환율 (KRW/외화)", min_value=0.0, value=latest_rate, step=1.0
                )

            amount = round(native_amount * fx_rate, 0)
            st.info(f"계산된 장부 금액: {amount:,.0f} {base_cur}")

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
                        JournalLine(
                            account_id=int(exp[0]),
                            debit=float(amount),
                            credit=0.0,
                            memo=memo,
                        ),
                        JournalLine(
                            account_id=int(pay[0]),
                            debit=0.0,
                            credit=float(amount),
                            memo=memo,
                            native_amount=float(native_amount) if is_fx else None,
                            native_currency=pay_currency if is_fx else None,
                            fx_rate=float(fx_rate) if is_fx else None,
                        ),
                    ],
                )
                try:
                    eid = create_journal_entry(conn, entry)
                    st.success(f"저장 완료: 전표 #{eid}")
                except Exception as e:
                    st.error(str(e))

    elif ttype == "수입(Income)":
        inc = st.selectbox(
            "수익 계정(Income)", options=income_accounts, format_func=lambda x: x[1]
        )
        recv = st.selectbox(
            "입금 계정(현금/예금)", options=asset_accounts, format_func=lambda x: x[1]
        )

        # FX Handling
        (
            recv_id,
            recv_name,
            recv_type,
            recv_p,
            recv_a,
            recv_s,
            recv_l,
            recv_post,
            recv_currency,
        ) = recv
        is_fx = recv_currency != base_cur

        native_amount = 0.0
        fx_rate = 1.0
        if is_fx:
            col1, col2 = st.columns(2)
            with col1:
                native_amount = st.number_input(
                    f"외화 금액 ({recv_currency})", min_value=0.0, value=0.0, step=1.0
                )
            with col2:
                latest_rate = get_latest_rate(conn, base_cur, recv_currency)
                fx_rate = st.number_input(
                    "환율 (KRW/외화)", min_value=0.0, value=latest_rate, step=1.0
                )

            amount = round(native_amount * fx_rate, 0)
            st.info(f"계산된 장부 금액: {amount:,.0f} {base_cur}")

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
                        JournalLine(
                            account_id=int(recv[0]),
                            debit=float(amount),
                            credit=0.0,
                            memo=memo,
                            native_amount=float(native_amount) if is_fx else None,
                            native_currency=recv_currency if is_fx else None,
                            fx_rate=float(fx_rate) if is_fx else None,
                        ),
                        JournalLine(
                            account_id=int(inc[0]),
                            debit=0.0,
                            credit=float(amount),
                            memo=memo,
                        ),
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

        # Advanced FX Handling for Transfers
        f_id, f_name, f_type, f_p, f_a, f_s, f_l, f_post, f_currency = from_acct
        t_id, t_name, t_type, t_p, t_a, t_s, t_l, t_post, t_currency = to_acct

        is_f_fx = f_currency != base_cur
        is_t_fx = t_currency != base_cur

        f_native = 0.0
        t_native = 0.0
        f_rate = 1.0
        t_rate = 1.0

        if is_f_fx or is_t_fx:
            st.info(
                "💡 멀티 통화 이체: 양쪽 계정의 현지 통화 금액과 환율을 각각 입력할 수 있습니다."
            )
            col1, col2 = st.columns(2)
            if is_f_fx:
                with col1:
                    f_native = st.number_input(
                        f"출금 외화 ({f_currency})",
                        min_value=0.0,
                        value=0.0,
                        key="f_native",
                    )
                    f_rate = st.number_input(
                        f"출금 환율 ({f_currency})",
                        min_value=0.0,
                        value=get_latest_rate(conn, base_cur, f_currency),
                        key="f_rate",
                    )
            if is_t_fx:
                with col2:
                    t_native = st.number_input(
                        f"입금 외화 ({t_currency})",
                        min_value=0.0,
                        value=0.0,
                        key="t_native",
                    )
                    t_rate = st.number_input(
                        f"입금 환율 ({t_currency})",
                        min_value=0.0,
                        value=get_latest_rate(conn, base_cur, t_currency),
                        key="t_rate",
                    )

            # Decide base amount
            if is_f_fx and not is_t_fx:
                amount = round(f_native * f_rate, 0)
            elif is_t_fx and not is_f_fx:
                amount = round(t_native * t_rate, 0)
            elif is_f_fx and is_t_fx:
                # Both FX, use from_acct as base if native provided, else to_acct
                amount = (
                    round(f_native * f_rate, 0)
                    if f_native > 0
                    else round(t_native * t_rate, 0)
                )

            st.info(f"계산된 장부 금액: {amount:,.0f} {base_cur}")

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
                        JournalLine(
                            account_id=int(to_acct[0]),
                            debit=float(amount),
                            credit=0.0,
                            memo=memo,
                            native_amount=float(t_native) if is_t_fx else None,
                            native_currency=t_currency if is_t_fx else None,
                            fx_rate=float(t_rate) if is_t_fx else None,
                        ),
                        JournalLine(
                            account_id=int(from_acct[0]),
                            debit=0.0,
                            credit=float(amount),
                            memo=memo,
                            native_amount=float(f_native) if is_f_fx else None,
                            native_currency=f_currency if is_f_fx else None,
                            fx_rate=float(f_rate) if is_f_fx else None,
                        ),
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
