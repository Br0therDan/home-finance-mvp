from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from core.db import apply_migrations, get_connection
from core.services.asset_service import (
    add_valuation,
    create_asset,
    latest_valuation,
    list_assets,
    valuation_history,
)
from core.services.ledger_service import account_balances, list_posting_accounts

st.set_page_config(page_title="Assets", page_icon="🏠", layout="wide")

conn = get_connection()
apply_migrations(conn)

st.title("자산대장")
st.caption("유/무형 자산을 등록하고 평가(valuation) 이력을 관리한다.")

accounts = list_posting_accounts(conn, active_only=True)
asset_accounts = [(a["id"], a["name"]) for a in accounts if a["type"] == "ASSET"]

if len(asset_accounts) == 0:
    st.info("자산 하위(Posting) 계정이 없습니다. 설정에서 하위 계정을 먼저 생성하세요.")

with st.expander("자산 등록", expanded=True):
    with st.form("asset_form", clear_on_submit=True):
        name = st.text_input("자산명", value="")
        asset_class = st.selectbox(
            "자산 분류",
            [
                "CASH",
                "BANK",
                "STOCK",
                "CRYPTO",
                "REAL_ESTATE",
                "VEHICLE",
                "EQUIPMENT",
                "INTANGIBLE",
                "OTHER",
            ],
        )
        linked = st.selectbox(
            "연결 계정(회계 반영용)", options=asset_accounts, format_func=lambda x: x[1]
        )
        acq_date = st.date_input("취득일", value=date.today())
        acq_cost = st.number_input(
            "취득가(원가)", min_value=0.0, value=0.0, step=10000.0
        )
        note = st.text_area("메모", value="")

        submitted = st.form_submit_button("등록")
        if submitted:
            if not name.strip():
                st.error("자산명을 입력해라.")
            else:
                try:
                    aid = create_asset(
                        conn,
                        name=name.strip(),
                        asset_class=asset_class,
                        linked_account_id=int(linked[0]),
                        acquisition_date=acq_date,
                        acquisition_cost=float(acq_cost),
                        note=note,
                    )
                    st.success(f"자산 등록 완료: #{aid}")
                except Exception as e:
                    st.error(str(e))

st.divider()

assets = list_assets(conn)
ledger_balances = account_balances(conn)
rows = []
for a in assets:
    lv = latest_valuation(conn, int(a["id"]))
    linked_account_id = int(a["linked_account_id"])
    is_ledger_based = linked_account_id in ledger_balances
    rows.append(
        {
            "id": int(a["id"]),
            "자산명": a["name"],
            "분류": a["asset_class"],
            "취득일": a["acquisition_date"],
            "취득가": float(a["acquisition_cost"]),
            "최근평가": float(lv["value"]) if lv else None,
            "평가일": lv["valuation_date"] if lv else None,
            "연결계정": a["linked_account"],
            "구분": "원장기반" if is_ledger_based else "인벤토리",
            "원장잔액": float(ledger_balances.get(linked_account_id, 0.0)),
        }
    )

df = pd.DataFrame(rows)

st.subheader("자산 목록")
st.dataframe(df, width="stretch", hide_index=True)
st.caption(
    "구분: 원장기반은 해당 계정에 분개가 존재하는 자산, 인벤토리는 원장 반영이 없는 자산."
)

st.divider()

st.subheader("평가(Valuation) 추가")
if len(df) == 0:
    st.info("등록된 자산이 없다.")
else:
    selected_id = st.selectbox("자산 선택", options=df["id"].tolist())
    with st.form("val_form", clear_on_submit=True):
        v_date = st.date_input("평가일", value=date.today())
        value = st.number_input("평가금액", min_value=0.0, value=0.0, step=10000.0)
        method = st.selectbox("평가 방식", ["manual", "market", "depreciation"])
        submitted = st.form_submit_button("저장")

        if submitted:
            if selected_id is None:
                st.error("자산을 선택해 주세요.")
            else:
                try:
                    aid = (
                        int(selected_id)
                        if not isinstance(selected_id, int)
                        else selected_id
                    )
                    vid = add_valuation(
                        conn, aid, v_date=v_date, value=float(value), method=method
                    )
                    st.success(f"평가 저장 완료: #{vid}")
                except Exception as e:
                    st.error(str(e))

    st.markdown("**평가 이력**")
    if selected_id is None:
        hist = []
    else:
        aid = int(selected_id) if not isinstance(selected_id, int) else selected_id
        hist = valuation_history(conn, int(aid))
    hist_df = pd.DataFrame(
        [
            {
                "평가일": r["valuation_date"],
                "금액": float(r["value"]),
                "방식": r["method"],
            }
            for r in hist
        ]
    )
    st.dataframe(hist_df, width="stretch", hide_index=True)
