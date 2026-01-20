from datetime import date

import pandas as pd
import streamlit as st

from core.db import Session
from core.services.ledger_service import (
    balance_sheet,
    income_statement,
    monthly_cashflow,
)
from core.services.settings_service import get_base_currency
from ui.utils import format_currency, get_currency_config, get_pandas_style_fmt

st.set_page_config(page_title="Reports", page_icon="📈", layout="wide")

st.title("리포트")

st.subheader("재무상태표(BS)")
as_of = st.date_input("기준일", value=date.today())
display_currency = st.session_state.get("display_currency", "KRW")

with Session() as session:
    bs = balance_sheet(session, as_of=as_of, display_currency=display_currency)

if bs.get("missing_rates"):
    missing_pairs = ", ".join(f"{base}/{quote}" for base, quote in bs["missing_rates"])
    st.warning(f"환율이 없어 일부 값은 장부 기준으로 표시됩니다: {missing_pairs}")

curr_cfg = get_currency_config(display_currency)
fmt_disp = get_pandas_style_fmt(display_currency)


def _prep_bs_df(items):
    data = []
    for i in items:
        data.append(
            {
                "계정": i["name"],
                "통화": i["currency"],
                "평가가치(표시)": i["display_value"],
            }
        )
    return pd.DataFrame(data)


assets_df = _prep_bs_df(bs["assets"])
liab_df = _prep_bs_df(bs["liabilities"])
eq_df = _prep_bs_df(bs["equity"])

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        f"총 자산 ({display_currency})",
        format_currency(bs["total_assets_disp"], display_currency),
    )
with col2:
    st.metric(
        f"총 부채 ({display_currency})",
        format_currency(bs["total_liabilities_disp"], display_currency),
    )
with col3:
    st.metric(
        f"순자산 ({display_currency})",
        format_currency(bs["net_worth_disp"], display_currency),
    )

c1, c2, c3 = st.columns(3)
with c1:
    st.dataframe(
        assets_df.style.format({"평가가치(표시)": fmt_disp}),
        width="stretch",
        hide_index=True,
        column_config={"평가가치(표시)": st.column_config.NumberColumn()},
    )
with c2:
    st.dataframe(
        liab_df.style.format({"평가가치(표시)": fmt_disp}),
        width="stretch",
        hide_index=True,
        column_config={"평가가치(표시)": st.column_config.NumberColumn()},
    )
with c3:
    st.dataframe(
        eq_df.style.format({"평가가치(표시)": fmt_disp}),
        width="stretch",
        hide_index=True,
        column_config={"평가가치(표시)": st.column_config.NumberColumn()},
    )

st.divider()

st.subheader("손익계산서(IS)")
col1, col2 = st.columns(2)
with col1:
    start = st.date_input("시작일", value=date(as_of.year, 1, 1), key="is_start")
with col2:
    end = st.date_input("종료일", value=as_of, key="is_end")

with Session() as session:
    is_ = income_statement(session, start=start, end=end)
    base_currency = get_base_currency(session)
base_cfg = get_currency_config(base_currency)
fmt_base = get_pandas_style_fmt(base_currency)

col1, col2, col3 = st.columns(3)
col1.metric("총 수익", format_currency(is_["total_income"], base_currency))
col2.metric("총 비용", format_currency(is_["total_expense"], base_currency))
col3.metric("순이익", format_currency(is_["net_profit"], base_currency))

income_df = pd.DataFrame(is_["income"], columns=["수익", "금액"])
expense_df = pd.DataFrame(is_["expense"], columns=["비용", "금액"])

c1, c2 = st.columns(2)
with c1:
    st.dataframe(
        income_df,
        width="stretch",
        hide_index=True,
        column_config={
            "금액": st.column_config.NumberColumn(format=base_cfg["format"])
        },
    )
with c2:
    st.dataframe(
        expense_df,
        width="stretch",
        hide_index=True,
        column_config={
            "금액": st.column_config.NumberColumn(format=base_cfg["format"])
        },
    )

st.divider()

st.subheader("월별 현금 변화(Cashflow proxy)")
year = st.number_input("연도", min_value=2000, max_value=2100, value=as_of.year, step=1)
with Session() as session:
    cf = monthly_cashflow(session, year=int(year))
cf_df = pd.DataFrame(cf)

if len(cf_df) == 0:
    st.info("현금/예금 계정이 없거나 거래가 없다.")
else:
    st.dataframe(
        cf_df.style.format({"net_change": fmt_base, "ending_balance": fmt_base}),
        width="stretch",
        hide_index=True,
        column_config={
            "month": "월",
            "net_change": st.column_config.NumberColumn("순유입"),
            "ending_balance": st.column_config.NumberColumn("기말잔액"),
        },
    )
