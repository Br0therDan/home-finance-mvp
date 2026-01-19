from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from core.db import apply_migrations, get_connection
from core.services.ledger_service import (
    balance_sheet,
    income_statement,
    monthly_cashflow,
)
from core.ui.formatting import krw

st.set_page_config(page_title="Reports", page_icon="📈", layout="wide")

conn = get_connection()
apply_migrations(conn)

st.title("리포트")

st.subheader("재무상태표(BS)")
as_of = st.date_input("기준일", value=date.today())
bs = balance_sheet(conn, as_of=as_of)

assets_df = pd.DataFrame(bs["assets"], columns=["자산", "금액"])
liab_df = pd.DataFrame(bs["liabilities"], columns=["부채", "금액"])
eq_df = pd.DataFrame(bs["equity"], columns=["자본", "금액"])

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("총 자산", krw(bs["total_assets"]))
with col2:
    st.metric("총 부채", krw(bs["total_liabilities"]))
with col3:
    st.metric("순자산", krw(bs["net_worth"]))

c1, c2, c3 = st.columns(3)
with c1:
    st.dataframe(assets_df, width="stretch", hide_index=True)
with c2:
    st.dataframe(liab_df, width="stretch", hide_index=True)
with c3:
    st.dataframe(eq_df, width="stretch", hide_index=True)

st.caption(f"BS 불일치(자산 - (부채+자본)) = {krw(bs['balanced_gap'])}")

st.divider()

st.subheader("손익계산서(IS)")
col1, col2 = st.columns(2)
with col1:
    start = st.date_input("시작일", value=date(as_of.year, 1, 1), key="is_start")
with col2:
    end = st.date_input("종료일", value=as_of, key="is_end")

is_ = income_statement(conn, start=start, end=end)

col1, col2, col3 = st.columns(3)
col1.metric("총 수익", krw(is_["total_income"]))
col2.metric("총 비용", krw(is_["total_expense"]))
col3.metric("순이익", krw(is_["net_profit"]))

income_df = pd.DataFrame(is_["income"], columns=["수익", "금액"])
expense_df = pd.DataFrame(is_["expense"], columns=["비용", "금액"])

c1, c2 = st.columns(2)
with c1:
    st.dataframe(income_df, width="stretch", hide_index=True)
with c2:
    st.dataframe(expense_df, width="stretch", hide_index=True)

st.divider()

st.subheader("월별 현금 변화(Cashflow proxy)")
year = st.number_input("연도", min_value=2000, max_value=2100, value=as_of.year, step=1)
cf = monthly_cashflow(conn, year=int(year))
cf_df = pd.DataFrame(cf)

if len(cf_df) == 0:
    st.info("현금/예금 계정이 없거나 거래가 없다.")
else:
    st.dataframe(cf_df, width="stretch", hide_index=True)
