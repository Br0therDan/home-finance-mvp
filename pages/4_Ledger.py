import pandas as pd
import streamlit as st
from datetime import date
from core.db import Session
from core.services.ledger_service import trial_balance
from core.services.settings_service import get_base_currency
from ui.utils import get_currency_config, get_pandas_style_fmt

st.set_page_config(page_title="Ledger", page_icon="📚", layout="wide")

st.title("원장 / 시산표")

c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    start = st.date_input("시작일", value=date(date.today().year, 1, 1))
with c2:
    end = st.date_input("종료일", value=date.today())

st.subheader("전표 목록")

sql_entries = """
    SELECT id, entry_date, description, source
    FROM journal_entries
    WHERE entry_date >= ? AND entry_date <= ?
    ORDER BY entry_date DESC, id DESC
"""
with Session() as session:
    entries = pd.read_sql(
        sql_entries, session, params=(start.isoformat(), end.isoformat())
    )

if not entries.empty:
    display_entries = entries.rename(
        columns={
            "id": "전표ID",
            "entry_date": "날짜",
            "description": "설명",
            "source": "출처",
        }
    )
    st.dataframe(display_entries, width="stretch", hide_index=True)

sql_lines = """
    SELECT je.entry_date, je.id AS entry_id, je.description,
           a.name AS account, a.type,
           jl.debit, jl.credit, jl.memo
    FROM journal_lines jl
    JOIN journal_entries je ON je.id = jl.entry_id
    JOIN accounts a ON a.id = jl.account_id
    WHERE je.entry_date >= ? AND je.entry_date <= ?
    ORDER BY je.entry_date DESC, je.id DESC
"""
with Session() as session:
    lines = pd.read_sql(sql_lines, session, params=(start.isoformat(), end.isoformat()))

if not lines.empty:
    display_lines = lines.rename(
        columns={
            "entry_date": "날짜",
            "entry_id": "전표ID",
            "description": "설명",
            "account": "계정",
            "type": "계정유형",
            "debit": "차변",
            "credit": "대변",
            "memo": "메모",
        }
    )

    with Session() as session:
        base_cur = get_base_currency(session)
    base_cfg = get_currency_config(base_cur)
    fmt_base = get_pandas_style_fmt(base_cur)

    st.dataframe(
        display_lines.style.format({"차변": fmt_base, "대변": fmt_base}),
        width="stretch",
        hide_index=True,
        column_config={
            "차변": st.column_config.NumberColumn(),
            "대변": st.column_config.NumberColumn(),
        },
    )

st.divider()

st.subheader("시산표(Trial Balance) - 기준일")
as_of = st.date_input("시산표 기준일", value=end)

with Session() as session:
    tb = trial_balance(session, as_of=as_of)
tb_df = pd.DataFrame(tb)

# show only non-zero by default
show_zero = st.checkbox("0 잔액 계정도 표시", value=False)
if not tb_df.empty and not show_zero:
    tb_df = tb_df[(tb_df["debit"].abs() > 1e-9) | (tb_df["credit"].abs() > 1e-9)]

if not tb_df.empty:
    tb_display = tb_df.rename(
        columns={"account": "계정", "type": "유형", "debit": "차변", "credit": "대변"}
    )
    # Get fmt_base again if it wasn't defined in this branch
    with Session() as session:
        base_cur = get_base_currency(session)
    fmt_base = get_pandas_style_fmt(base_cur)

    st.dataframe(
        tb_display[["계정", "유형", "차변", "대변"]].style.format(
            {"차변": fmt_base, "대변": fmt_base}
        ),
        width="stretch",
        hide_index=True,
        column_config={
            "차변": st.column_config.NumberColumn(),
            "대변": st.column_config.NumberColumn(),
        },
    )
else:
    st.info("표시할 시산표 데이터가 없습니다.")

st.caption("debit/credit은 raw_balance를 기준으로 양/음수 분리 표시한 값이다.")
