from datetime import date

import streamlit as st

from core.db import Session
from core.models import JournalEntryInput, JournalLine
from core.services.fx_service import get_latest_rate
from core.services.ledger_service import create_journal_entry, list_posting_accounts
from core.services.settings_service import get_base_currency

st.set_page_config(page_title="Transactions", page_icon="🧾", layout="wide")

st.title("거래 입력")
st.caption("가계부 형태로 입력하면 내부적으로 복식부기 분개가 자동 생성된다.")

with Session() as session:
    accounts = list_posting_accounts(session, active_only=True)

if len(accounts) == 0:
    st.info(
        "Posting 가능한 하위 계정이 없습니다. 설정에서 하위 계정을 먼저 생성하세요."
    )
    st.stop()


def to_tuple(a):
    return (
        a["id"],
        a["name"],
        a["type"],
        a["parent_id"],
        a["is_active"],
        a["is_system"],
        a["level"],
        a["allow_posting"],
        a["currency"],
    )


asset_accounts = [to_tuple(a) for a in accounts if a["type"] == "ASSET"]
liab_accounts = [to_tuple(a) for a in accounts if a["type"] == "LIABILITY"]
income_accounts = [to_tuple(a) for a in accounts if a["type"] == "INCOME"]
expense_accounts = [to_tuple(a) for a in accounts if a["type"] == "EXPENSE"]

TRANSACTION_TYPES = ["지출(Expense)", "수입(Income)", "이체(Transfer)"]

ttype = st.selectbox("거래 유형", TRANSACTION_TYPES)
txn_date = st.date_input("날짜", value=date.today())

with Session() as session:
    base_cur = get_base_currency(session)

    # Account Selection (Reactive)
    if ttype == "지출(Expense)":
        exp = st.selectbox(
            "지출 계정(비용)", options=expense_accounts, format_func=lambda x: x[1]
        )
        pay = st.selectbox(
            "결제 계정(현금/예금/카드)",
            options=asset_accounts + liab_accounts,
            format_func=lambda x: x[1],
        )
        target_currency = (pay[8] if len(pay) > 8 else base_cur) if pay else base_cur

    elif ttype == "수입(Income)":
        inc = st.selectbox(
            "수익 계정(Income)", options=income_accounts, format_func=lambda x: x[1]
        )
        recv = st.selectbox(
            "입금 계정(현금/예금)", options=asset_accounts, format_func=lambda x: x[1]
        )
        target_currency = (recv[8] if len(recv) > 8 else base_cur) if recv else base_cur

    else:  # 이체(Transfer)
        from_acct = st.selectbox(
            "출금 계정(from)", options=asset_accounts, format_func=lambda x: x[1]
        )
        to_acct = st.selectbox(
            "입금 계정(to)", options=asset_accounts, format_func=lambda x: x[1]
        )
        if to_acct:
            target_currency = to_acct[8] if len(to_acct) > 8 else base_cur
        else:
            target_currency = base_cur

    st.divider()

    is_fx = target_currency != base_cur

    from ui.utils import get_currency_config

    base_cfg = get_currency_config(base_cur)
    target_cfg = get_currency_config(target_currency)

    with st.form("txn_form_rest", clear_on_submit=True):
        is_base_int = base_cfg["precision"] == 0
        base_step = int(base_cfg["step"]) if is_base_int else float(base_cfg["step"])
        base_val = 0 if is_base_int else 0.0

        amount_base = st.number_input(
            f"장부 금액 ({base_cur})",
            min_value=base_val,
            value=base_val,
            step=base_step,
            format=base_cfg["format"],
            help="외화 거래인 경우 환율에 따라 자동 계산됩니다.",
        )

        native_amount = 0.0
        fx_rate = 1.0

        if is_fx:
            st.info(
                f"💡 선택한 계정의 기본 통화가 {target_currency}입니다. 외화 정보를 입력하세요."
            )
            col1, col2 = st.columns(2)
            with col1:
                is_tgt_int = target_cfg["precision"] == 0
                tgt_step = (
                    int(target_cfg["step"]) if is_tgt_int else float(target_cfg["step"])
                )
                tgt_val = 0 if is_tgt_int else 0.0

                native_amount = st.number_input(
                    f"외화 금액 ({target_currency})",
                    min_value=tgt_val,
                    value=tgt_val,
                    step=tgt_step,
                    format=target_cfg["format"],
                )
            with col2:
                with Session() as session:
                    latest_rate = get_latest_rate(session, base_cur, target_currency)
            rate_missing = latest_rate is None
            if rate_missing:
                st.warning(
                    f"{base_cur}/{target_currency} 환율이 없습니다. 설정에서 환율을 먼저 저장하세요."
                )
                latest_rate = 0.0
            fx_rate = st.number_input(
                f"환율 ({base_cur}/{target_currency})",
                min_value=0.0,
                value=latest_rate,
                step=0.01,
            )

        if native_amount > 0 and fx_rate > 0:
            amount_base = round(native_amount * fx_rate, 0)
            st.success(f"예정 장부 금액: {amount_base:,.0f} {base_cur}")

        memo = st.text_input("메모", value="")
        submitted = st.form_submit_button("거래 저장")

        if submitted:
            if amount_base <= 0 and native_amount <= 0:
                st.error("금액을 입력해 주세요.")
            elif is_fx and fx_rate <= 0:
                st.error("환율이 없습니다. 설정에서 환율을 저장해 주세요.")
            else:
                # Final calculation for submission
                final_amount = (
                    amount_base
                    if amount_base > 0
                    else round(native_amount * fx_rate, 0)
                )

                if ttype == "지출(Expense)":
                    lines = [
                        JournalLine(
                            account_id=int(exp[0]),
                            debit=float(final_amount),
                            credit=0.0,
                            memo=memo,
                        ),
                        JournalLine(
                            account_id=int(pay[0]),
                            debit=0.0,
                            credit=float(final_amount),
                            memo=memo,
                            native_amount=float(native_amount) if is_fx else None,
                            native_currency=target_currency if is_fx else None,
                            fx_rate=float(fx_rate) if is_fx else None,
                        ),
                    ]
                elif ttype == "수입(Income)":
                    lines = [
                        JournalLine(
                            account_id=int(recv[0]),
                            debit=float(final_amount),
                            credit=0.0,
                            memo=memo,
                            native_amount=float(native_amount) if is_fx else None,
                            native_currency=target_currency if is_fx else None,
                            fx_rate=float(fx_rate) if is_fx else None,
                        ),
                        JournalLine(
                            account_id=int(inc[0]),
                            debit=0.0,
                            credit=float(final_amount),
                            memo=memo,
                        ),
                    ]
                else:  # Transfer
                    lines = [
                        JournalLine(
                            account_id=int(to_acct[0]),
                            debit=float(final_amount),
                            credit=0.0,
                            memo=memo,
                            native_amount=float(native_amount) if is_fx else None,
                            native_currency=target_currency if is_fx else None,
                            fx_rate=float(fx_rate) if is_fx else None,
                        ),
                        JournalLine(
                            account_id=int(from_acct[0]),
                            debit=0.0,
                            credit=float(final_amount),
                            memo=memo,
                        ),
                    ]

                entry = JournalEntryInput(
                    entry_date=txn_date,
                    description=memo or ttype.split("(")[0],
                    source="ui:transactions",
                    lines=lines,
                )
                try:
                    with Session() as session:
                        eid = create_journal_entry(session, entry)
                    st.success(f"저장 완료: 전표 #{eid}")
                    st.balloons()
                except Exception as e:
                    st.error(str(e))

st.divider()
st.subheader("자동 분개 규칙(요약)")
st.markdown(
    """
- **지출**: (차) 비용계정 / (대) 결제계정(현금·예금·카드부채)
- **수입**: (차) 입금계정(현금·예금) / (대) 수익계정
- **이체**: (차) to(자산) / (대) from(자산)

선택한 계정의 **기본 통화**가 기준 통화(KRW)와 다를 경우 자동으로 외화 입력 칸이 활성화됩니다.
"""
)
