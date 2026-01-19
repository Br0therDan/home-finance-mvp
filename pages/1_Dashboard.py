from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from core.db import apply_migrations, get_connection
from core.services.ledger_service import balance_sheet, income_statement
from core.ui.formatting import krw

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

conn = get_connection()
apply_migrations(conn)

st.title("대시보드")

as_of = st.date_input("기준일", value=date.today())

bs = balance_sheet(conn, as_of=as_of)

col1, col2, col3, col4 = st.columns(4)
col1.metric("총 자산", krw(bs["total_assets"]))
col2.metric("총 부채", krw(bs["total_liabilities"]))
col3.metric("순자산", krw(bs["net_worth"]))
col4.metric("BS 불일치(점검)", krw(bs["balanced_gap"]))

st.divider()

st.subheader("재무상태표(BS) 요약")

assets_df = pd.DataFrame(bs["assets"], columns=["계정", "금액"])
liab_df = pd.DataFrame(bs["liabilities"], columns=["계정", "금액"])
eq_df = pd.DataFrame(bs["equity"], columns=["계정", "금액"])

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**자산**")
    st.dataframe(assets_df, width="stretch", hide_index=True)
with c2:
    st.markdown("**부채**")
    st.dataframe(liab_df, width="stretch", hide_index=True)
with c3:
    st.markdown("**자본**")
    st.dataframe(eq_df, width="stretch", hide_index=True)

st.divider()

st.subheader("이번 달 손익(IS)")
start = date(as_of.year, as_of.month, 1)
end = as_of
is_ = income_statement(conn, start=start, end=end)

col1, col2, col3 = st.columns(3)
col1.metric("총 수익", krw(is_["total_income"]))
col2.metric("총 비용", krw(is_["total_expense"]))
col3.metric("순이익", krw(is_["net_profit"]))

income_df = pd.DataFrame(is_["income"], columns=["계정", "금액"])
expense_df = pd.DataFrame(is_["expense"], columns=["계정", "금액"])

c1, c2 = st.columns(2)
with c1:
    st.markdown("**수익(Income)**")
    st.dataframe(income_df, width="stretch", hide_index=True)
with c2:
    st.markdown("**비용(Expense)**")
    st.dataframe(expense_df, width="stretch", hide_index=True)
