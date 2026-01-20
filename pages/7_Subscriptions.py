from datetime import date, timedelta
import pandas as pd
import streamlit as st
from core.db import Session
from core.services.ledger_service import list_posting_accounts
from core.services.settings_service import get_base_currency
from core.services.subscription_service import (
    create_subscription,
    generate_cashflow_projection,
    list_subscriptions,
    process_due_subscriptions,
)

st.set_page_config(page_title="Subscriptions", page_icon="🔁", layout="wide")

st.title("정기 일정(구독) 관리")
st.caption("반복되는 지출/수입 일정을 등록하고 현금흐름을 미리 확인합니다.")

with Session() as session:
    accounts = list_posting_accounts(session, active_only=True)

if len(accounts) == 0:
    st.info(
        "Posting 가능한 하위 계정이 없습니다. 설정에서 하위 계정을 먼저 생성하세요."
    )
    st.stop()


def to_tuple(account: dict) -> tuple:
    return (
        account["id"],
        account["name"],
        account["type"],
        account["parent_id"],
        account["is_active"],
        account["is_system"],
        account["level"],
        account["allow_posting"],
        account["currency"],
    )


account_tuples = [to_tuple(a) for a in accounts]
account_lookup = {int(a[0]): a[1] for a in account_tuples}

with Session() as session:
    base_cur = get_base_currency(session)

st.subheader("정기 일정 등록")
with st.form("subscription_form", clear_on_submit=True):
    name = st.text_input("이름", value="")
    cadence = st.selectbox(
        "주기",
        options=["daily", "weekly", "monthly", "quarterly", "yearly"],
        index=2,
    )
    interval = st.number_input("간격(주기당)", min_value=1, value=1, step=1)
    next_due_date = st.date_input("다음 만기일", value=date.today())
    amount = st.number_input(
        f"금액 ({base_cur})",
        min_value=0.0,
        value=0.0,
        step=1000.0,
        format="%0.2f",
    )
    debit_account = st.selectbox(
        "차변 계정(비용/자산 증가)",
        options=account_tuples,
        format_func=lambda x: x[1],
    )
    credit_account = st.selectbox(
        "대변 계정(현금/부채 증가)",
        options=account_tuples,
        format_func=lambda x: x[1],
    )
    memo = st.text_input("메모", value="")
    auto_create = st.checkbox("만기일에 자동 분개 생성", value=False)
    is_active = st.checkbox("활성화", value=True)
    submitted = st.form_submit_button("정기 일정 저장")

    if submitted:
        try:
            with Session() as session:
                subscription_id = create_subscription(
                    session,
                    name=name,
                    cadence=cadence,
                    interval=int(interval),
                    next_due_date=next_due_date,
                    amount=amount,
                    debit_account_id=int(debit_account[0]),
                    credit_account_id=int(credit_account[0]),
                    memo=memo,
                    is_active=is_active,
                    auto_create_journal=auto_create,
                )
            st.success(f"저장 완료: 구독 #{subscription_id}")
        except Exception as exc:
            st.error(str(exc))

st.divider()

st.subheader("정기 일정 목록")
with Session() as session:
    subscriptions = list_subscriptions(session, active_only=False)
if subscriptions:
    table_rows = []
    for sub in subscriptions:
        table_rows.append(
            {
                "ID": sub["id"],
                "이름": sub["name"],
                "주기": f"{sub['cadence']} x{sub['interval']}",
                "다음 만기일": sub["next_due_date"],
                "금액": sub["amount"],
                "차변 계정": account_lookup.get(sub["debit_account_id"], "-"),
                "대변 계정": account_lookup.get(sub["credit_account_id"], "-"),
                "자동 분개": "Y" if sub["auto_create_journal"] else "N",
                "활성": "Y" if sub["is_active"] else "N",
            }
        )
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True)
else:
    st.info("등록된 정기 일정이 없습니다.")

st.divider()

st.subheader("현금흐름 전망")
col1, col2 = st.columns(2)
with col1:
    projection_start = st.date_input("시작일", value=date.today(), key="proj_start")
with col2:
    projection_end = st.date_input(
        "종료일",
        value=date.today() + timedelta(days=90),
        key="proj_end",
    )

if projection_end < projection_start:
    st.warning("종료일은 시작일 이후여야 합니다.")
else:
    with Session() as session:
        projections = generate_cashflow_projection(
            session, projection_start, projection_end, active_only=True
        )
    if projections:
        projection_rows = [
            {
                "일자": item["due_date"],
                "이름": item["name"],
                "금액": item["amount"],
                "차변 계정": account_lookup.get(item["debit_account_id"], "-"),
                "대변 계정": account_lookup.get(item["credit_account_id"], "-"),
            }
            for item in projections
        ]
        st.dataframe(pd.DataFrame(projection_rows), use_container_width=True)
    else:
        st.info("선택한 기간에 예정된 정기 일정이 없습니다.")

st.divider()

st.subheader("만기 처리")
as_of = st.date_input("처리 기준일", value=date.today(), key="process_as_of")
if st.button("만기 일정 처리 및 자동 분개", type="primary"):
    with Session() as session:
        results = process_due_subscriptions(session, as_of=as_of, create_entries=True)
    if results:
        st.success(f"{len(results)}건 처리되었습니다.")
        st.dataframe(pd.DataFrame(results), use_container_width=True)
    else:
        st.info("처리할 만기 일정이 없습니다.")
