import streamlit as st
from sqlmodel import Session

from core.db import engine
from core.services.fx_service import get_latest_rate, save_rate
from core.services.settings_service import get_base_currency, set_base_currency

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
