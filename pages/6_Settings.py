import pandas as pd
import streamlit as st

from core.db import Session
from core.services.account_service import (
    HOUSEHOLD_GROUP_LABELS,
    HOUSEHOLD_GROUP_PARENTS,
    create_user_account,
    delete_user_account,
    get_account,
    get_parents_for_household_group,
    update_user_account,
)
from core.services.fx_service import get_latest_rate, save_rate
from core.services.settings_service import (
    get_av_api_key,
    get_base_currency,
    set_av_api_key,
    set_base_currency,
)

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")

st.title("설정")
st.caption("시스템 전역 설정")

# --- App Settings Section ---
with Session() as session:
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
            with Session() as session:
                set_base_currency(session, new_base)
            st.success(f"기준 통화가 {new_base}로 변경되었습니다.")
            st.rerun()

    st.markdown("---")
    with Session() as session:
        current_key = get_av_api_key(session) or ""
    new_key = st.text_input(
        "Alpha Vantage API Key",
        value=current_key,
        type="password",
        help="주식 시장가 실시간 업데이트를 위해 필요합니다.",
    )
    if new_key != current_key:
        if st.button("API 키 저장"):
            with Session() as session:
                set_av_api_key(session, new_key)
            st.success("API 키가 저장되었습니다.")
            st.rerun()

st.divider()


@st.dialog("계정 추가")
def _dialog_add_account(group_key: str, group_label: str):
    st.subheader(f"[{group_label}] 계정 추가")
    with Session() as session:
        parents = get_parents_for_household_group(session, group_key)

    if not parents:
        st.error("이 그룹에 설정된 상위 계정 분류가 없습니다.")
        return

    with st.form("add_acc_form"):
        name = st.text_input("계정 이름 (예: OO은행, OO카드)")
        parent_id = st.selectbox(
            "상위 분류",
            options=[p["id"] for p in parents],
            format_func=lambda x: next(p["name"] for p in parents if p["id"] == x),
        )
        currency = st.selectbox("통화", ["KRW", "USD", "JPY", "EUR"])

        col1, col2 = st.columns(2)
        if col1.form_submit_button("저장", type="primary"):
            if not name.strip():
                st.error("이름을 입력하세요.")
            else:
                try:
                    with Session() as session:
                        parent_acc = get_account(session, parent_id)
                        create_user_account(
                            session,
                            name=name,
                            type_=parent_acc["type"],
                            parent_id=parent_id,
                            currency=currency,
                        )
                        session.commit()
                    st.success("추가되었습니다.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        if col2.form_submit_button("취소"):
            st.rerun()


@st.dialog("계정 수정")
def _dialog_edit_account(acc: dict):
    st.subheader("계정 수정")
    with st.form("edit_acc_form"):
        name = st.text_input("계정 이름", value=acc["name"])
        is_active = st.checkbox("활성 상태", value=bool(acc["is_active"]))
        currency = st.selectbox(
            "통화",
            ["KRW", "USD", "JPY", "EUR"],
            index=(
                ["KRW", "USD", "JPY", "EUR"].index(acc["currency"])
                if acc["currency"] in ["KRW", "USD", "JPY", "EUR"]
                else 0
            ),
        )

        col1, col2 = st.columns(2)
        if col1.form_submit_button("저장", type="primary"):
            try:
                with Session() as session:
                    update_user_account(
                        session,
                        acc["id"],
                        name=name,
                        is_active=is_active,
                        currency=currency,
                    )
                    session.commit()
                st.success("수정되었습니다.")
                st.rerun()
            except Exception as e:
                st.error(str(e))
        if col2.form_submit_button("취소"):
            st.rerun()


@st.dialog("계정 삭제")
def _dialog_delete_account(acc: dict):
    st.subheader("계정 삭제")
    st.warning(
        f"'{acc['name']}' 계정을 삭제하시겠습니까? 전표가 있는 경우 삭제할 수 없습니다."
    )
    col1, col2 = st.columns(2)
    if col1.button("삭제", type="primary"):
        try:
            with Session() as session:
                delete_user_account(session, acc["id"])
                session.commit()
            st.success("삭제되었습니다.")
            st.rerun()
        except Exception as e:
            st.error(str(e))
    if col2.button("취소"):
        st.rerun()


@st.dialog("하위 계정 추가")
def _dialog_add_account_hierarchical(parent: dict | None, type_hint: str = "ASSET"):
    title = f"[{parent['name']}]의 하위 계정 추가" if parent else "최상위(L1) 계정 추가"
    st.subheader(title)
    with st.form("add_sub_acc_form"):
        name = st.text_input("계정 이름")
        if not parent:
            type_ = st.selectbox(
                "계정 유형",
                ["ASSET", "LIABILITY", "EQUITY", "INCOME", "EXPENSE"],
                index=["ASSET", "LIABILITY", "EQUITY", "INCOME", "EXPENSE"].index(
                    type_hint
                ),
            )
        else:
            type_ = parent["type"]

        currency = st.selectbox(
            "통화",
            ["KRW", "USD", "JPY", "EUR"],
            index=(
                ["KRW", "USD", "JPY", "EUR"].index(parent.get("currency", "KRW"))
                if parent
                else 0
            ),
        )

        col1, col2 = st.columns(2)
        if col1.form_submit_button("저장", type="primary"):
            if not name.strip():
                st.error("이름을 입력하세요.")
            else:
                try:
                    with Session() as session:
                        create_user_account(
                            session,
                            name=name,
                            type_=type_,
                            parent_id=parent["id"] if parent else None,
                            currency=currency,
                        )
                        session.commit()
                    st.success("추가되었습니다.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        if col2.form_submit_button("취소"):
            st.rerun()


# --- Household Account Management Section ---
st.divider()
st.subheader("🏠 계정 관리 (Household Account Management)")
st.caption(
    "생활 친화 그룹 -> 대분류 -> 상세 계정 순으로 관리합니다. 모든 계정에 대해 CRUD가 가능합니다."
)

with Session() as session:
    # Fetch all accounts once for efficiency
    all_accounts_rows = session.execute(
        "SELECT * FROM accounts ORDER BY type, level, name"
    ).fetchall()
    all_accounts = [dict(r) for r in all_accounts_rows]
    account_lookup = {a["id"]: a for a in all_accounts}

# 1. Household Groups Column
groups_list = [{"id": k, "label": v} for k, v in HOUSEHOLD_GROUP_LABELS.items()]
groups_df = pd.DataFrame(groups_list)

# 2. Layout
col_g, col_p, col_c = st.columns([1, 1, 1.5])

# --- Col 1: Groups ---
with col_g:
    st.write("**1. 생활 그룹**")
    group_event = st.dataframe(
        groups_df[["label"]],
        key="group_sel_df",
        on_select="rerun",
        selection_mode="single-row",
        hide_index=True,
        width="stretch",
        height=400,
    )
    selected_group_indices = group_event.get("selection", {}).get("rows", [])
    selected_group_key = (
        groups_list[selected_group_indices[0]]["id"] if selected_group_indices else None
    )

# --- Col 2: Parents (L1) ---
with col_p:
    st.write("**2. 대분류 (Level 1)**")
    if selected_group_key:
        parent_names = HOUSEHOLD_GROUP_PARENTS.get(selected_group_key, [])
        l1_accounts = [
            a for a in all_accounts if a["level"] == 1 and a["name"] in parent_names
        ]
    else:
        l1_accounts = [a for a in all_accounts if a["level"] == 1]

    if l1_accounts:
        l1_df = pd.DataFrame(l1_accounts)
        l1_event = st.dataframe(
            l1_df[["name"]],
            key="l1_sel_df",
            on_select="rerun",
            selection_mode="single-row",
            hide_index=True,
            width="stretch",
            height=400,
        )
        selected_l1_indices = l1_event.get("selection", {}).get("rows", [])
        selected_l1_id = (
            l1_accounts[selected_l1_indices[0]]["id"] if selected_l1_indices else None
        )
    else:
        st.info("그룹을 선택하세요.")
        selected_l1_id = None

# --- Col 3: Children (L2, L3) ---
with col_c:
    st.write("**3. 상세 계정 (Level 2, 3)**")
    if selected_l1_id:
        # Recursive helper to get descendants
        def get_descendants(pid, depth=1):
            children = [a for a in all_accounts if a["parent_id"] == pid]
            results = []
            for c in children:
                c_copy = c.copy()
                c_copy["depth"] = depth
                results.append(c_copy)
                results.extend(get_descendants(c["id"], depth + 1))
            return results

        l2or3_accounts = get_descendants(selected_l1_id)
        if l2or3_accounts:
            l23_df = pd.DataFrame(l2or3_accounts)
            l23_df["display_name"] = l23_df.apply(
                lambda x: "  " * x["depth"] + str(x["name"]), axis=1
            )

            l23_event = st.dataframe(
                l23_df[["display_name", "currency"]],
                key="l23_sel_df",
                on_select="rerun",
                selection_mode="single-row",
                hide_index=True,
                width="stretch",
                height=400,
                column_config={"display_name": "계정명", "currency": "통화"},
            )
            selected_l23_indices = l23_event.get("selection", {}).get("rows", [])
            selected_acc = (
                l2or3_accounts[selected_l23_indices[0]]
                if selected_l23_indices
                else None
            )
        else:
            st.info("하위 계정이 없습니다.")
            selected_acc = None
    else:
        st.info("대분류를 선택하세요.")
        selected_acc = None

# 3. Action Buttons (Centralized logic)
st.markdown("---")
# Determine which account is targeted. Specifity: Child > Parent
target_acc = selected_acc or (
    account_lookup[selected_l1_id] if selected_l1_id else None
)

btn_cols = st.columns([1, 1, 1, 1, 3])
with btn_cols[0]:
    if st.button("➕ 최상위 추가", key="add_L1_btn"):
        _dialog_add_account_hierarchical(None)

with btn_cols[1]:
    if target_acc:
        if st.button("➕ 하위 추가", key="add_sub_btn"):
            _dialog_add_account_hierarchical(target_acc)

with btn_cols[2]:
    if target_acc:
        if st.button("✏️ 편집", key="edit_acc_btn"):
            _dialog_edit_account(target_acc)

with btn_cols[3]:
    if target_acc:
        if st.button("🗑️ 삭제", key="del_acc_btn", type="primary"):
            _dialog_delete_account(target_acc)

st.divider()

# --- FX Rates Management Section ---
with st.expander("💱 수동 환율 관리 (Manual FX Rates)", expanded=True):
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        quote_cur = st.selectbox(
            "외화 (Quote Currency)", ["USD", "JPY", "EUR", "CNY"], key="fx_quote"
        )
    with col2:
        with Session() as session:
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
            with Session() as session:
                save_rate(session, current_base, quote_cur, new_rate)
            st.success("환율이 저장되었습니다.")
            st.rerun()
