from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from core.db import apply_migrations, get_connection
from core.models import JournalLine
from core.services.ledger_service import (
    create_opening_balance_entry,
    get_account_by_name,
    has_opening_balance_entry,
    list_accounts,
    list_posting_accounts,
)

st.set_page_config(page_title="Day0 Setup", page_icon="🧭", layout="wide")

conn = get_connection()
apply_migrations(conn)

st.title("Day0 기초 잔액 설정")
st.caption(
    "과거 거래 복원 없이 오늘 기준 기초자산/부채를 입력해 OPENING_BALANCE 전표를 생성합니다."
)

accounts = list_accounts(conn, active_only=True)
posting_accounts = list_posting_accounts(conn, active_only=True)
asset_accounts = [
    (a["id"], a["name"]) for a in posting_accounts if a["type"] == "ASSET"
]
liab_accounts = [
    (a["id"], a["name"]) for a in posting_accounts if a["type"] == "LIABILITY"
]

if len(asset_accounts) == 0:
    st.info("자산 하위(Posting) 계정이 없습니다. 설정에서 하위 계정을 먼저 생성하세요.")
    st.stop()

opening_equity = get_account_by_name(
    conn, "기초순자산", "EQUITY"
) or get_account_by_name(conn, "기초자본(Opening Balance)", "EQUITY")

if opening_equity is None:
    st.error("기초순자산(EQUITY) 계정이 없습니다. 마이그레이션을 먼저 적용하세요.")
    st.stop()

if has_opening_balance_entry(conn):
    st.warning(
        "이미 OPENING_BALANCE 전표가 존재합니다. 재생성은 기본적으로 차단됩니다."
    )

    existing = conn.execute(
        """
        SELECT je.id, je.entry_date, je.description
        FROM journal_entries je
        WHERE je.source = 'opening_balance'
        ORDER BY je.id DESC
        LIMIT 1
        """
    ).fetchone()

    if existing:
        st.write(
            f"전표ID: {existing['id']} / 날짜: {existing['entry_date']} / 설명: {existing['description']}"
        )
        lines = conn.execute(
            """
            SELECT a.name AS account, a.type, jl.debit, jl.credit, jl.memo
            FROM journal_lines jl
            JOIN accounts a ON a.id = jl.account_id
            WHERE jl.entry_id = ?
            ORDER BY a.type, a.name
            """,
            (int(existing["id"]),),
        ).fetchall()
        df = pd.DataFrame(lines, columns=["계정", "유형", "차변", "대변", "메모"])
        st.dataframe(df, use_container_width=True, hide_index=True)
    st.stop()

if "asset_rows" not in st.session_state:
    st.session_state.asset_rows = 2
if "liab_rows" not in st.session_state:
    st.session_state.liab_rows = 2

st.subheader("입력")

with st.form("opening_balance_form"):
    col1, col2 = st.columns(2)
    with col1:
        entry_date = st.date_input("기준일(Day0)", value=date.today())
    with col2:
        description = st.text_input("설명", value="OPENING_BALANCE")

    st.markdown("#### 자산(ASSET) 입력")
    for i in range(st.session_state.asset_rows):
        a1, a2 = st.columns([3, 2])
        with a1:
            st.selectbox(
                f"자산 계정 #{i + 1}",
                options=asset_accounts,
                format_func=lambda x: x[1],
                key=f"asset_account_{i}",
            )
        with a2:
            st.number_input(
                f"금액 #{i + 1}",
                min_value=0.0,
                step=10000.0,
                value=0.0,
                key=f"asset_amount_{i}",
            )

    if st.form_submit_button("자산 행 추가"):
        st.session_state.asset_rows += 1
        st.rerun()

    st.markdown("#### 부채(LIABILITY) 입력")
    for i in range(st.session_state.liab_rows):
        l1, l2 = st.columns([3, 2])
        with l1:
            st.selectbox(
                f"부채 계정 #{i + 1}",
                options=liab_accounts,
                format_func=lambda x: x[1],
                key=f"liab_account_{i}",
            )
        with l2:
            st.number_input(
                f"금액 #{i + 1}",
                min_value=0.0,
                step=10000.0,
                value=0.0,
                key=f"liab_amount_{i}",
            )

    if st.form_submit_button("부채 행 추가"):
        st.session_state.liab_rows += 1
        st.rerun()

    st.markdown("#### 전표 미리보기")
    account_name = {a["id"]: a["name"] for a in accounts}

    asset_lines: list[JournalLine] = []
    for i in range(st.session_state.asset_rows):
        account = st.session_state.get(f"asset_account_{i}")
        amount = float(st.session_state.get(f"asset_amount_{i}", 0.0))
        if account and amount > 0:
            asset_lines.append(
                JournalLine(
                    account_id=int(account[0]), debit=amount, credit=0.0, memo="Day0"
                )
            )

    liability_lines: list[JournalLine] = []
    for i in range(st.session_state.liab_rows):
        account = st.session_state.get(f"liab_account_{i}")
        amount = float(st.session_state.get(f"liab_amount_{i}", 0.0))
        if account and amount > 0:
            liability_lines.append(
                JournalLine(
                    account_id=int(account[0]), debit=0.0, credit=amount, memo="Day0"
                )
            )

    preview_rows = []
    total_debit = 0.0
    total_credit = 0.0
    for line in asset_lines:
        preview_rows.append(
            {
                "계정": account_name.get(line.account_id, str(line.account_id)),
                "차변": line.debit,
                "대변": 0.0,
                "구분": "자산",
            }
        )
        total_debit += line.debit

    for line in liability_lines:
        preview_rows.append(
            {
                "계정": account_name.get(line.account_id, str(line.account_id)),
                "차변": 0.0,
                "대변": line.credit,
                "구분": "부채",
            }
        )
        total_credit += line.credit

    gap = total_debit - total_credit
    if abs(gap) > 1e-9:
        if gap > 0:
            preview_rows.append(
                {"계정": "기초순자산", "차변": 0.0, "대변": gap, "구분": "자본"}
            )
            total_credit += gap
        else:
            preview_rows.append(
                {"계정": "기초순자산", "차변": -gap, "대변": 0.0, "구분": "자본"}
            )
            total_debit += -gap

    if preview_rows:
        preview_df = pd.DataFrame(preview_rows)
        st.dataframe(preview_df, use_container_width=True, hide_index=True)
        st.caption(f"합계: 차변 {total_debit:,.0f} / 대변 {total_credit:,.0f}")
    else:
        st.info("자산 또는 부채 라인을 입력하세요.")

    submitted = st.form_submit_button("OPENING_BALANCE 생성")
    if submitted:
        try:
            entry_id = create_opening_balance_entry(
                conn,
                entry_date=entry_date,
                description=description or "OPENING_BALANCE",
                asset_lines=asset_lines,
                liability_lines=liability_lines,
            )
            st.success(f"OPENING_BALANCE 전표 생성 완료: #{entry_id}")
        except Exception as e:
            st.error(str(e))
