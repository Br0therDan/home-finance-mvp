from __future__ import annotations

import pandas as pd
import streamlit as st

from core.db import apply_migrations, fetch_df, get_connection

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")

conn = get_connection()
apply_migrations(conn)

st.title("설정")
st.caption("계정과목(CoA) 관리 - MVP 수준")

st.subheader("계정과목 목록")
df = fetch_df(
    conn,
    """
    SELECT id, name, type, parent_id, is_active
    FROM accounts
    ORDER BY type, name
    """,
)

display_df = df.rename(
    columns={
        "id": "계정ID",
        "name": "계정명",
        "type": "계정유형",
        "parent_id": "상위계정ID",
        "is_active": "활성",
    }
)
st.dataframe(display_df, width="stretch", hide_index=True)

st.divider()

st.subheader("계정과목 추가")
with st.form("add_account", clear_on_submit=True):
    name = st.text_input("계정명")
    type_ = st.selectbox(
        "계정 타입", ["ASSET", "LIABILITY", "EQUITY", "INCOME", "EXPENSE"]
    )
    parent_id = st.number_input("상위 계정 ID(없으면 0)", min_value=0, value=0, step=1)
    is_active = st.checkbox("활성", value=True)

    submitted = st.form_submit_button("추가")
    if submitted:
        if not name.strip():
            st.error("계정명을 입력해라.")
        else:
            with conn:
                conn.execute(
                    """
                    INSERT INTO accounts(name, type, parent_id, is_active)
                    VALUES (?, ?, NULLIF(?, 0), ?)
                    """,
                    (name.strip(), type_, int(parent_id), 1 if is_active else 0),
                )
            st.success("추가 완료")
