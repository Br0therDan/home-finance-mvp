import streamlit as st
from sqlmodel import Session

from core.db import engine
from core.services.account_service import list_household_account_groups
from core.services.fx_service import get_latest_rate, save_rate
from core.services.settings_service import (
    get_base_currency,
    set_base_currency,
    get_av_api_key,
    set_av_api_key,
)

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")

session = Session(engine)

st.title("설정")
st.caption("시스템 전역 설정")

# --- App Settings Section ---
current_base = get_base_currency(session)

with st.expander("🌐 전역 설정 (Global Settings)", expanded=True):
    new_base = st.selectbox(
        "기준 통화 (Base Currency)",
        options=["KRW", "USD", "JPY", "EUR"],
        index=(
            ["KRW", "USD", "JPY", "EUR"].index(current_base)
            if current_base in ["KRW", "USD", "JPY", "EUR"]
            else 0
        ),
        help="모든 장부의 기본 집계 기준이 되는 통화입니다. 변경 시 주의하세요.",
    )
    if new_base != current_base:
        if st.button("기준 통화 업데이트"):
            set_base_currency(session, new_base)
            st.success(f"기준 통화가 {new_base}로 변경되었습니다.")
            st.rerun()

    st.markdown("---")
    current_key = get_av_api_key(session) or ""
    new_key = st.text_input(
        "Alpha Vantage API Key",
        value=current_key,
        type="password",
        help="주식 시장가 실시간 업데이트를 위해 필요합니다.",
    )
    if new_key != current_key:
        if st.button("API 키 저장"):
            set_av_api_key(session, new_key)
            st.success("API 키가 저장되었습니다.")
            st.rerun()

st.divider()

# --- Household Account Groups Section ---
with st.expander("🏠 계정 그룹 (Household View)", expanded=True):
    st.caption(
        "시스템(L1) 계정은 숨기고, 실제 사용 계정을 생활 친화 그룹으로 묶어 보여줍니다."
    )
    grouped_accounts = list_household_account_groups(session, active_only=True)
    rows = []
    for group in grouped_accounts:
        for account in group["accounts"]:
            rows.append(
                {
                    "그룹": group["label"],
                    "계정": account["name"],
                    "상위 분류": account.get("l1_name") or "-",
                    "유형": account["type"],
                    "통화": account["currency"],
                }
            )
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("표시할 계정이 없습니다. 계정을 먼저 추가하세요.")

st.divider()

# --- FX Rates Management Section ---
with st.expander("💱 수동 환율 관리 (Manual FX Rates)", expanded=True):
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        quote_cur = st.selectbox(
            "외화 (Quote Currency)", ["USD", "JPY", "EUR", "CNY"], key="fx_quote"
        )
    with col2:
        current_rate = get_latest_rate(session, current_base, quote_cur)
        if current_rate is None:
            st.warning("등록된 환율이 없습니다. 값을 입력해 저장하세요.")
            current_rate = 0.0
        new_rate = st.number_input(
            f"환율 ({current_base}/{quote_cur})",
            min_value=0.0,
            value=current_rate,
            step=1.0,
        )
    with col3:
        st.write(" ")
        st.write(" ")
        if st.button("환율 저장"):
            save_rate(session, current_base, quote_cur, new_rate)
            st.success("환율이 저장되었습니다.")
            st.rerun()
