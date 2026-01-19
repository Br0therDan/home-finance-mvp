from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from core.db import apply_migrations, get_connection
from core.services.ledger_service import balance_sheet, income_statement
from core.ui.formatting import fmt, krw

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

conn = get_connection()
apply_migrations(conn)

st.title("대시보드")

as_of = st.date_input("기준일", value=date.today())
display_currency = st.session_state.get("display_currency", "KRW")

bs = balance_sheet(conn, as_of=as_of, display_currency=display_currency)

col1, col2, col3 = st.columns(3)
col1.metric(
    f"총 자산 ({display_currency})", fmt(bs["total_assets_disp"], display_currency)
)
col2.metric(
    f"총 부채 ({display_currency})", fmt(bs["total_liabilities_disp"], display_currency)
)
col3.metric(f"순자산 ({display_currency})", fmt(bs["net_worth_disp"], display_currency))

with st.expander("🔍 장부 금액 (KRW 기준) 상세", expanded=False):
    c1, c2, c3 = st.columns(3)
    c1.metric("총 자산 (Book, KRW)", krw(bs["total_assets_base"]))
    c2.metric("총 부채 (Book, KRW)", krw(bs["total_liabilities_base"]))
    c3.metric("순자산 (Book, KRW)", krw(bs["net_worth_base"]))

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
    st.dataframe(assets_df, width="stretch", hide_index=True)
with c2:
    st.markdown(f"**부채 ({display_currency})**")
    st.dataframe(liab_df, width="stretch", hide_index=True)
with c3:
    st.markdown(f"**자본 ({display_currency})**")
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

st.divider()

# --- Market Data Watchlist ---
st.subheader("📊 시장 데이터 요약")
from core.services.market_data_service import MarketDataService

md_service = MarketDataService(conn)

sync_log = md_service.get_last_sync_log("price")
if sync_log:
    st.caption(
        f"가격 데이터 마지막 갱신: {sync_log['started_at']} ({sync_log['status']})"
    )

latest_prices = fetch_df(
    conn,
    "SELECT symbol, market, price, currency, as_of FROM market_prices ORDER BY symbol ASC, as_of DESC",
)
if not latest_prices.empty:
    watchlist = latest_prices.sort_values("as_of", ascending=False).drop_duplicates(
        "symbol"
    )
    st.dataframe(watchlist, use_container_width=True, hide_index=True)
else:
    st.info("동기화된 가격 데이터가 없습니다. 설정 페이지에서 동기화를 진행해주세요.")
