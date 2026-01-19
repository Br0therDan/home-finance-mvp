from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st
from sqlmodel import Session

from core.db import engine
from core.services.asset_service import list_assets
from core.services.fx_service import get_latest_rate
from core.services.ledger_service import balance_sheet, income_statement
from core.services.valuation_service import ValuationService
from core.ui.formatting import fmt, krw

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

session = Session(engine)

st.title("대시보드")

as_of = st.date_input("기준일", value=date.today())
display_currency = st.session_state.get("display_currency", "KRW")

bs = balance_sheet(session, as_of=as_of, display_currency=display_currency)

# --- Valuation Calculation ---
val_service = ValuationService(session)
latest_vals = val_service.get_valuations_for_dashboard()
valuation_total_disp = 0.0

# Calculate total valuation (Fallback to Book Value if no manual valuation)
# Better approach: sum manual valuations + sum book values of other assets
total_book_value_base = bs["total_assets_base"]

# Get total valuation in Base Currency (KRW)
valuation_base_total = 0.0
# Assets from 'assets' table

all_registered_assets = list_assets(session)
registered_linked_ids = {
    int(a["linked_account_id"]): a["id"] for a in all_registered_assets
}

for acc in bs["assets"]:
    acc_id = int(acc["id"])
    asset_id = registered_linked_ids.get(acc_id)
    manual_val = latest_vals.get(asset_id) if asset_id else None

    if manual_val:
        # Convert manual valuation to Base Currency
        rate = get_latest_rate(session, bs["base_currency"], manual_val["currency"])
        valuation_base_total += manual_val["value_native"] * rate
    else:
        # Fallback to book value
        valuation_base_total += acc["book_value_base"]

valuation_disp_total = valuation_base_total * (
    bs["total_assets_disp"] / bs["total_assets_base"]
    if bs["total_assets_base"] != 0
    else 1.0
)
unrealized_pnl_base = valuation_base_total - total_book_value_base

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    f"총 자산 (장부, {display_currency})",
    fmt(bs["total_assets_disp"], display_currency),
)
col2.metric(
    f"총 자산 (평가, {display_currency})",
    fmt(valuation_disp_total, display_currency),
    delta=fmt(valuation_disp_total - bs["total_assets_disp"], display_currency),
)
col3.metric(
    f"총 부채 ({display_currency})", fmt(bs["total_liabilities_disp"], display_currency)
)
col4.metric(
    f"순자산 (평가, {display_currency})",
    fmt(valuation_disp_total - bs["total_liabilities_disp"], display_currency),
)

with st.expander("🔍 장부 vs 평가 상세 (KRW 기준)", expanded=False):
    c1, c2, c3 = st.columns(3)
    c1.metric("총 자산 (Book Value)", krw(total_book_value_base))
    c2.metric("총 자산 (Valuation)", krw(valuation_base_total))
    c3.metric(
        "미실현 손익 (Unrealized PnL)",
        krw(unrealized_pnl_base),
        delta=krw(unrealized_pnl_base),
    )

st.divider()

st.subheader("재무상태표(BS) 요약")


def _prep_df(items):
    data = []
    for i in items:
        data.append(
            {
                "계정": i["name"],
                "통화": i["currency"],
                "잔액(현지)": i["native_balance"],
                "평가가치(표시)": i["display_value"],
                "장부금액(Base)": i["book_value_base"],
            }
        )
    return pd.DataFrame(data)


assets_df = _prep_df(bs["assets"])
liab_df = _prep_df(bs["liabilities"])
eq_df = _prep_df(bs["equity"])

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"**자산 ({display_currency})**")
    st.dataframe(
        assets_df,
        width="stretch",
        hide_index=True,
        column_config={
            "잔액(현지)": st.column_config.NumberColumn(format="%.2f"),
            "평가가치(표시)": st.column_config.NumberColumn(format="%.0f"),
            "장부금액(Base)": st.column_config.NumberColumn(format="%.0f"),
        },
    )
with c2:
    st.markdown(f"**부채 ({display_currency})**")
    st.dataframe(
        liab_df,
        width="stretch",
        hide_index=True,
        column_config={
            "잔액(현지)": st.column_config.NumberColumn(format="%.2f"),
            "평가가치(표시)": st.column_config.NumberColumn(format="%.0f"),
            "장부금액(Base)": st.column_config.NumberColumn(format="%.0f"),
        },
    )
with c3:
    st.markdown(f"**자본 ({display_currency})**")
    st.dataframe(
        eq_df,
        width="stretch",
        hide_index=True,
        column_config={
            "잔액(현지)": st.column_config.NumberColumn(format="%.2f"),
            "평가가치(표시)": st.column_config.NumberColumn(format="%.0f"),
            "장부금액(Base)": st.column_config.NumberColumn(format="%.0f"),
        },
    )

st.divider()

st.subheader("이번 달 손익(IS)")
start = date(as_of.year, as_of.month, 1)
end = as_of
is_ = income_statement(session, start=start, end=end)

col1, col2, col3 = st.columns(3)
col1.metric("총 수익", krw(is_["total_income"]))
col2.metric("총 비용", krw(is_["total_expense"]))
col3.metric("순이익", krw(is_["net_profit"]))

income_df = pd.DataFrame(is_["income"], columns=["계정", "금액"])
expense_df = pd.DataFrame(is_["expense"], columns=["계정", "금액"])

c1, c2 = st.columns(2)
with c1:
    st.markdown("**수익(Income)**")
    st.dataframe(
        income_df,
        width="stretch",
        hide_index=True,
        column_config={"금액": st.column_config.NumberColumn(format="%.0f")},
    )
with c2:
    st.markdown("**비용(Expense)**")
    st.dataframe(
        expense_df,
        width="stretch",
        hide_index=True,
        column_config={"금액": st.column_config.NumberColumn(format="%.0f")},
    )
