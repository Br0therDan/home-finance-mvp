from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st
from sqlmodel import Session

from core.db import engine
from core.services.asset_service import (
    list_assets,
    reconcile_asset_valuations_with_ledger,
)
from core.services.fx_service import get_latest_rate
from core.services.ledger_service import balance_sheet, income_statement
from core.services.valuation_service import ValuationService
from ui.utils import format_currency, get_currency_config, get_pandas_style_fmt

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

session = Session(engine)

st.title("대시보드")

as_of = st.date_input("기준일", value=date.today())
display_currency = st.session_state.get("display_currency", "KRW")
curr_cfg = get_currency_config(display_currency)

bs = balance_sheet(session, as_of=as_of, display_currency=display_currency)
if bs.get("missing_rates"):
    missing_pairs = ", ".join(f"{base}/{quote}" for base, quote in bs["missing_rates"])
    st.warning(f"환율이 없어 일부 값은 장부 기준으로 표시됩니다: {missing_pairs}")

base_cur = bs.get("base_currency", "KRW")
fmt_base = get_pandas_style_fmt(base_cur)

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
        if rate is None:
            st.warning(
                f"{bs['base_currency']}/{manual_val['currency']} 환율이 없어 평가값을 제외했습니다."
            )
        else:
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
reconciliation = reconcile_asset_valuations_with_ledger(session, as_of=as_of)
recon_items = reconciliation["items"]
has_recon_delta = any(abs(item["delta_base"]) > 1e-6 for item in recon_items)

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    f"총 자산 (장부, {display_currency})",
    format_currency(bs["total_assets_disp"], display_currency),
)
col2.metric(
    f"총 자산 (평가, {display_currency})",
    format_currency(valuation_disp_total, display_currency),
    delta=format_currency(
        valuation_disp_total - bs["total_assets_disp"], display_currency
    ),
)
col3.metric(
    f"총 부채 ({display_currency})",
    format_currency(bs["total_liabilities_disp"], display_currency),
)
col4.metric(
    f"순자산 (평가, {display_currency})",
    format_currency(
        valuation_disp_total - bs["total_liabilities_disp"], display_currency
    ),
)

with st.expander("🔍 장부 vs 평가 상세 (KRW 기준)", expanded=False):
    # Base currency hardcoded to KRW mostly, or check bs['base_currency']
    c1, c2, c3 = st.columns(3)
    c1.metric("총 자산 (Book Value)", format_currency(total_book_value_base, base_cur))
    c2.metric("총 자산 (Valuation)", format_currency(valuation_base_total, base_cur))
    c3.metric(
        "미실현 손익 (Unrealized PnL)",
        format_currency(unrealized_pnl_base, base_cur),
        delta=format_currency(unrealized_pnl_base, base_cur),
    )

if reconciliation.get("missing_rates"):
    missing_pairs = ", ".join(
        f"{base}/{quote}" for base, quote in reconciliation["missing_rates"]
    )
    st.warning(f"자산 평가 환율이 없어 일부 자산이 제외되었습니다: {missing_pairs}")

if has_recon_delta:
    st.warning(
        "자산 평가 합계와 장부 자산 계정이 불일치합니다. 아래에서 상세를 확인하세요."
    )

with st.expander("🧾 자산 평가 ↔ 장부 계정 대사", expanded=has_recon_delta):
    if recon_items:
        recon_df = pd.DataFrame(
            [
                {
                    "계정": item["account_name"],
                    "장부금액(Base)": item["book_value_base"],
                    "평가금액(Base)": item["valuation_value_base"],
                    "차이(Base)": item["delta_base"],
                    "자산 수": item["asset_count"],
                    "평가 입력 수": item["valued_asset_count"],
                }
                for item in recon_items
            ]
        )
        st.dataframe(
            recon_df.style.format(
                {
                    "장부금액(Base)": fmt_base,
                    "평가금액(Base)": fmt_base,
                    "차이(Base)": fmt_base,
                }
            ),
            width="stretch",
            hide_index=True,
            column_config={
                "장부금액(Base)": st.column_config.NumberColumn(),
                "평가금액(Base)": st.column_config.NumberColumn(),
                "차이(Base)": st.column_config.NumberColumn(),
            },
        )
        st.caption(
            "평가 입력이 없는 자산은 평가 합계에 포함되지 않습니다. "
            "장부 잔액은 연결된 자산 계정 기준입니다."
        )
    else:
        st.info("등록된 자산이 없습니다.")

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

# Style format strings
fmt_disp = get_pandas_style_fmt(display_currency)


def _apply_style(df):
    return df.style.format(
        {
            "잔액(현지)": "{:,.2f}",  # Mixed currency default
            "평가가치(표시)": fmt_disp,
            "장부금액(Base)": fmt_base,
        }
    )


# Base CFG
base_cfg = get_currency_config(bs.get("base_currency", "KRW"))

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"**자산 ({display_currency})**")
    st.dataframe(
        _apply_style(assets_df),
        width="stretch",
        hide_index=True,
        column_config={
            "잔액(현지)": st.column_config.NumberColumn(),
            "평가가치(표시)": st.column_config.NumberColumn(),
            "장부금액(Base)": st.column_config.NumberColumn(),
        },
    )
with c2:
    st.markdown(f"**부채 ({display_currency})**")
    st.dataframe(
        _apply_style(liab_df),
        width="stretch",
        hide_index=True,
        column_config={
            "잔액(현지)": st.column_config.NumberColumn(),
            "평가가치(표시)": st.column_config.NumberColumn(),
            "장부금액(Base)": st.column_config.NumberColumn(),
        },
    )
with c3:
    st.markdown(f"**자본 ({display_currency})**")
    st.dataframe(
        _apply_style(eq_df),
        width="stretch",
        hide_index=True,
        column_config={
            "잔액(현지)": st.column_config.NumberColumn(),
            "평가가치(표시)": st.column_config.NumberColumn(),
            "장부금액(Base)": st.column_config.NumberColumn(),
        },
    )

st.divider()

st.subheader("이번 달 손익(IS)")
start = date(as_of.year, as_of.month, 1)
end = as_of
is_ = income_statement(session, start=start, end=end)
# IS in base currency
base_currency = "KRW"
fmt_is = get_pandas_style_fmt(base_currency)

col1, col2, col3 = st.columns(3)
col1.metric("총 수익", format_currency(is_["total_income"], base_currency))
col2.metric("총 비용", format_currency(is_["total_expense"], base_currency))
col3.metric("순이익", format_currency(is_["net_profit"], base_currency))

income_df = pd.DataFrame(is_["income"], columns=["계정", "금액"])
expense_df = pd.DataFrame(is_["expense"], columns=["계정", "금액"])

c1, c2 = st.columns(2)
with c1:
    st.markdown("**수익(Income)**")
    st.dataframe(
        income_df.style.format({"금액": fmt_is}),
        width="stretch",
        hide_index=True,
        column_config={"금액": st.column_config.NumberColumn()},
    )
with c2:
    st.markdown("**비용(Expense)**")
    st.dataframe(
        expense_df.style.format({"금액": fmt_is}),
        width="stretch",
        hide_index=True,
        column_config={"금액": st.column_config.NumberColumn()},
    )
