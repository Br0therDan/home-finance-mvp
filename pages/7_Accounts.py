from __future__ import annotations

import io

import pandas as pd
import streamlit as st
from sqlmodel import Session, func, select

from core.db import engine
from core.models import Account
from core.services.account_service import (
    create_user_account,
    delete_user_account,
    update_user_account,
)

st.set_page_config(page_title="Accounts", page_icon="🗂️", layout="wide")

session = Session(engine)

st.title("계정과목 관리 (CoA)")
st.caption("시스템(Level 1) 및 사용자 정의 계정을 관리합니다.")


def _load_accounts_df() -> pd.DataFrame:
    sql = """
        SELECT a.id, a.name, a.type, a.parent_id, a.is_active, a.is_system, a.level, a.allow_posting, a.currency,
               p.name AS parent_name
        FROM accounts a
        LEFT JOIN accounts p ON p.id = a.parent_id
        ORDER BY a.type, a.level, a.name
    """
    return pd.read_sql(sql, session.connection())


def _format_section(section: pd.DataFrame) -> pd.DataFrame:
    section = section.copy()
    section["활성"] = section["is_active"].apply(lambda x: "O" if int(x) == 1 else "X")
    section["전표허용"] = section["allow_posting"].apply(
        lambda x: "허용" if int(x) == 1 else "차단"
    )
    return section


def _level_slice(
    section: pd.DataFrame,
    *,
    level: int,
    parent_ids: list[int] | None,
) -> pd.DataFrame:
    df = section[section["level"] == level]
    if parent_ids is not None:
        df = df[df["parent_id"].isin(parent_ids)]
    return df.copy()


def _selection_key(level: int, type_: str, parent_ids: list[int] | None) -> str:
    parent_part = "root" if not parent_ids else "_".join(map(str, parent_ids))
    return f"coa_selection_{type_}_L{level}_{parent_part}"


def _get_selected_ids(
    *,
    level: int,
    type_: str,
    parent_ids: list[int] | None,
) -> list[int]:
    key = _selection_key(level, type_, parent_ids)
    return st.session_state.get(key, [])


def _display_df(
    level_df: pd.DataFrame,
    *,
    level: int,
    include_parent: bool,
    include_active: bool = True,
) -> pd.DataFrame:
    display = pd.DataFrame()

    display["id"] = level_df["id"].astype(int)
    display["계정ID"] = level_df["id"].astype(int)
    display["계정명"] = level_df["name"].astype(str)

    if include_parent:
        display["상위계정"] = level_df["parent_name"].fillna("").astype(str)

    display["통화"] = level_df["currency"].fillna("KRW").astype(str)
    if include_active:
        display["활성"] = level_df["활성"].astype(str)
    return display


def _render_account_table(
    *,
    df: pd.DataFrame,
    level: int,
    type_: str,
    parent_ids: list[int] | None,
    height: int,
) -> list[int]:
    if df.empty:
        return []

    key = _selection_key(level, type_, parent_ids)
    all_ids = df["id"].tolist()
    current_selected = st.session_state.get(key, [])

    # Use st.dataframe with on_select='rerun' for stable native selection
    event = st.dataframe(
        df,
        key=f"df_{key}",
        on_select="rerun",
        selection_mode="single-row",
        hide_index=True,
        height=height,
        use_container_width=True,
        column_config={
            "id": None,
            "계정ID": st.column_config.NumberColumn("ID", format="%d", width="small"),
            "계정명": st.column_config.TextColumn("계정명", width="medium"),
            "상위계정": st.column_config.TextColumn("상위계정", width="small"),
            "활성": st.column_config.TextColumn("활성", width="small"),
            "통화": st.column_config.TextColumn("통화", width="small"),
        },
    )

    new_indices = event.get("selection", {}).get("rows", [])
    new_selected_ids = [all_ids[i] for i in new_indices]

    if new_selected_ids != current_selected:
        st.session_state[key] = new_selected_ids

    return new_selected_ids


@st.dialog("계정 추가")
def _dialog_create_child(type_: str, parent_id: int) -> None:
    st.caption("상위 계정은 시스템(Level 1) 집계 계정이어야 합니다.")

    with st.form("add_account_form"):
        name = st.text_input("계정명")
        is_active = st.checkbox("활성", value=True)
        currency = st.selectbox("통화", ["KRW", "USD", "JPY", "EUR"])

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("생성", type="primary")
        with col2:
            cancel = st.form_submit_button("닫기")

    if submitted:
        if not name.strip():
            st.error("계정명을 입력해 주세요.")
            return
        try:
            create_user_account(
                session,
                name=name,
                type_=type_,
                parent_id=int(parent_id),
                is_active=bool(is_active),
                currency=currency,
            )
            st.toast("계정이 생성되었습니다.")
            st.rerun()
        except Exception as e:  # noqa: BLE001
            st.error(str(e))

    if cancel:
        st.rerun()


@st.dialog("계정 편집")
def _dialog_edit(
    account_id: int, current_name: str, current_active: bool, current_currency: str
) -> None:
    with st.form("edit_account_form"):
        name = st.text_input("계정명", value=current_name)
        is_active = st.checkbox("활성", value=current_active)
        currency = st.selectbox(
            "기본 통화",
            ["KRW", "USD", "JPY", "EUR"],
            index=(
                ["KRW", "USD", "JPY", "EUR"].index(current_currency)
                if current_currency in ["KRW", "USD", "JPY", "EUR"]
                else 0
            ),
        )

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("저장", type="primary")
        with col2:
            cancel = st.form_submit_button("닫기")

    if submitted:
        try:
            update_user_account(
                session,
                int(account_id),
                name=name,
                is_active=bool(is_active),
                currency=currency,
            )
            st.toast("수정되었습니다.")
            st.rerun()
        except Exception as e:  # noqa: BLE001
            st.error(str(e))

    if cancel:
        st.rerun()


@st.dialog("계정 삭제")
def _dialog_delete(account_id: int, account_name: str) -> None:
    st.warning("삭제는 되돌릴 수 없습니다.")
    st.write(f"대상: {account_name} (ID={account_id})")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("삭제", type="primary"):
            try:
                delete_user_account(session, int(account_id))
                st.toast("삭제되었습니다.")
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(str(e))
    with col2:
        if st.button("닫기"):
            st.rerun()


def _render_action_bar(
    level: int, type_: str, section: pd.DataFrame, selected_ids: list[int]
) -> None:
    if not selected_ids:
        st.caption("항목을 선택하면 작업 버튼이 활성화됩니다.")
        return

    acc_id = selected_ids[0]
    acc_row = section[section["id"] == acc_id].iloc[0]

    # Use the account's actual type, as the section might be mixed-type
    row_type = str(acc_row["type"])

    cols = st.columns([1, 1, 1, 2])

    with cols[0]:
        if st.button("✏️ 편집", key=f"edit_{row_type}_{level}_{acc_id}"):
            _dialog_edit(
                int(acc_row["id"]),
                current_name=str(acc_row["name"]),
                current_active=bool(int(acc_row["is_active"]) == 1),
                current_currency=str(acc_row.get("currency", "KRW")),
            )

    with cols[1]:
        if st.button("🗑️ 삭제", key=f"del_{row_type}_{level}_{acc_id}"):
            _dialog_delete(int(acc_row["id"]), account_name=str(acc_row["name"]))

    with cols[2]:
        # Always allow adding children if it's L1
        if level == 1:
            if st.button("➕ 하위추가", key=f"add_{row_type}_{level}_{acc_id}"):
                _dialog_create_child(type_=row_type, parent_id=int(acc_row["id"]))


def _generate_excel_template() -> bytes:
    """Generate a sample Excel template for CoA import."""
    data = [
        {
            "id": 1001,
            "name": "현금",
            "type": "ASSET",
            "level": 1,
            "parent_id": None,
            "is_active": 1,
            "currency": "KRW",
        },
        {
            "id": 100101,
            "name": "현금(소액)",
            "type": "ASSET",
            "level": 2,
            "parent_id": 1001,
            "is_active": 1,
            "currency": "KRW",
        },
    ]
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="CoA_Template")
    return output.getvalue()


@st.dialog("Excel 계정 가져오기")
def _dialog_excel_import():
    st.caption("Excel 파일을 업로드하여 계정을 일괄 추가하거나 업데이트합니다.")

    col_up, col_dl = st.columns([3, 1])
    with col_up:
        uploaded = st.file_uploader("CoA Excel 파일 (.xlsx)", type=["xlsx"])
        if uploaded:
            if st.button("가져오기 & 업데이트", type="primary"):
                _process_excel_impot(uploaded)
    with col_dl:
        st.write("")  # spacer
        st.write("")
        st.download_button(
            label="📄 템플릿",
            data=_generate_excel_template(),
            file_name="coa_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


def _process_excel_impot(file):
    try:
        df = pd.read_excel(file)

        # Clean column names (strip spaces)
        df.columns = df.columns.astype(str).str.strip()

        # Expected columns: id, name, type, parent_id, is_active (opt), currency (opt)
        # 'id' is OPTIONAL now for creation (will be auto-calc), but required for update if name matches?
        # Typically for override, ID should be key. If ID is missing, assume creation under parent_id.

        required = ["name", "type"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            st.error(f"필수 컬럼 누락: {missing}")
            return

        # Helper to safely get int or None
        def safe_int(val):
            if pd.isna(val) or val == "":
                return None
            try:
                return int(float(val))
            except (ValueError, TypeError):
                return None

        count_created = 0
        count_updated = 0

        for _, row in df.iterrows():
            row_id = safe_int(row.get("id"))
            name = str(row["name"]).strip()
            type_ = str(row["type"]).strip()
            parent_id = safe_int(row.get("parent_id"))

            # 1. Try to find existing account
            existing = None
            if row_id:
                existing = session.get(Account, row_id)

            # If valid ID provided and exists -> Update
            if existing:
                existing.name = name
                existing.type = type_
                if parent_id:
                    existing.parent_id = parent_id

                # Optional fields
                if "is_active" in row and not pd.isna(row["is_active"]):
                    existing.is_active = bool(int(row["is_active"]))
                if "currency" in row and not pd.isna(row["currency"]):
                    existing.currency = str(row["currency"]).upper()

                session.add(existing)
                count_updated += 1

            # If no ID or ID not found -> Create
            else:
                # Creation requires parent_id for L2+
                # Exception: L1 account creation via Excel? Allowed if parent_id is missing/None

                # If ID is missing, we must generate one.
                # Logic copied/adapted from create_user_account for auto-ID
                if not row_id:
                    if not parent_id:
                        # L1 New Account
                        # Must find max L1 ID for this type? Or just simple increment?
                        # For MVP, simpler to restrict auto-creation to L2 (requires parent) or require ID for L1.
                        st.error(
                            f"[Skip] {name}: ID가 없는 L1 계정 생성은 현재 지원하지 않습니다. ID를 지정해주세요."
                        )
                        continue

                    parent = session.get(Account, parent_id)
                    if not parent:
                        st.error(
                            f"[Skip] {name}: 상위 계정 ID({parent_id})를 찾을 수 없습니다."
                        )
                        continue

                    # Calculate new ID
                    parent_id_int = parent.id
                    range_min = parent_id_int * 100 + 1
                    range_max = parent_id_int * 100 + 99

                    # Determine next ID
                    # Check DB for max in range
                    statement = select(func.max(Account.id)).where(
                        Account.id >= range_min, Account.id <= range_max
                    )
                    max_id_db = session.exec(statement).one()

                    new_id = max_id_db + 1 if max_id_db else range_min

                    # ALSO Check current session NEW objects to prevent collision in bulk insert
                    # (Simple approach: commit per row or scan new_objects. For now, we commit at end, so we might have collision if we don't increment local tracker.
                    # BUT session.exec won't see uncommitted adds unless we flush? or maybe it does?
                    # Safer: flush per create or just query well.
                    # Let's simple-track? Or just flush.)
                    session.flush()  # Flush to make the newly added account visible to next select logic if needed. However, commit is final.
                    # Actually, if we use session.exec below again for the next row, we need the previous one to be 'visible' to the transaction.
                    # Flushing makes it visible to the transaction.

                    # Re-check to be safe after other potential inserts?
                    # The logic above queries DB. Flush sends invalidator.

                    if new_id > range_max:
                        st.error(f"[Skip] {name}: 하위 계정 한도 초과")
                        continue

                    row_id = new_id

                # Create New
                new_acc = Account(
                    id=row_id,
                    name=name,
                    type=type_,
                    parent_id=parent_id,
                    is_active=True,
                    is_system=False,
                    level=1 if not parent_id else 2,  # simplified level logic
                    allow_posting=True,
                    currency="KRW",
                )

                # Update specific fields if present
                if "is_active" in row and not pd.isna(row["is_active"]):
                    new_acc.is_active = bool(int(row["is_active"]))
                if "currency" in row and not pd.isna(row["currency"]):
                    new_acc.currency = str(row["currency"]).upper()

                # Auto-manage parent posting logic
                if parent_id:
                    parent_acc = session.get(Account, parent_id)
                    if parent_acc and parent_acc.allow_posting:
                        parent_acc.allow_posting = False
                        session.add(parent_acc)

                session.add(new_acc)
                session.flush()  # Ensure ID is taken
                count_created += 1

        session.commit()
        st.success(f"완료: 생성 {count_created}건, 업데이트 {count_updated}건")
        st.rerun()

    except Exception as e:
        session.rollback()
        st.error(f"Excel 처리 실패: {e}")


# MAIN UI
col_title, col_btn = st.columns([1, 4])
with col_title:
    st.subheader("계정 목록")
with col_btn:
    # Right-aligned button
    st.markdown(
        """
        <style>
        div[data-testid="column"] { display: flex; align-items: center; } 
        </style>
        """,
        unsafe_allow_html=True,
    )
    if st.button("📥 Excel 계정 가져오기"):
        _dialog_excel_import()

st.caption("시스템(Level 1) 및 사용자 정의 계정을 관리합니다.")

accounts_df = _load_accounts_df()
accounts_df = _format_section(accounts_df)
TYPE_ORDER = ["ASSET", "LIABILITY", "EQUITY", "INCOME", "EXPENSE"]


# 3-Column Filter Layout
st.markdown("---")
cols = st.columns([0.2, 0.4, 0.4])

# --- Col 1: Type Selection ---
with cols[0]:
    st.markdown("### 1. 계정 유형")
    type_df = pd.DataFrame({"유형": TYPE_ORDER})

    # Use st.dataframe for multi-select
    type_event = st.dataframe(
        type_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        key="sel_type",
        height=300,
    )
    selected_type_indices = type_event.get("selection", {}).get("rows", [])
    if selected_type_indices:
        selected_types = [TYPE_ORDER[i] for i in selected_type_indices]
    else:
        # If nothing selected, treat as ALL selected
        selected_types = TYPE_ORDER

# --- Col 2: L1 Selection ---
with cols[1]:
    st.markdown("### 2. 대분류 (L1)")

    # Filter by selected types
    l1_all = accounts_df[
        (accounts_df["level"] == 1) & (accounts_df["type"].isin(selected_types))
    ].copy()

    if l1_all.empty:
        st.info("선택된 유형에 해당하는 계정이 없습니다.")
        selected_l1_ids = []
    else:
        l1_display = _display_df(
            l1_all, level=1, include_parent=False, include_active=False
        )

        # We handle selection entirely via st.dataframe
        # Key needs to depend on selected_types to reset effectively if filter changes heavily
        # But we want simple behavior.

        # IMPORTANT: _render_account_table assumes single-select mainly, but we want multi-row for filtering
        # We'll adapt it or just inline the call for specific behavior here.
        # Let's use the helper but change mode to multi-row?
        # The helper function hardcodes single-row. Let's create a specialized inline call here.

        current_selection_key = f"sel_l1_{len(selected_types)}"
        l1_event = st.dataframe(
            l1_display,
            key=current_selection_key,
            on_select="rerun",
            selection_mode="multi-row",
            hide_index=True,
            use_container_width=True,
            height=500,
            column_config={
                "id": None,
                "계정ID": st.column_config.NumberColumn(
                    "ID", format="%d", width="small"
                ),
                "계정명": st.column_config.TextColumn("계정명", width="medium"),
            },
        )
        l1_indices = l1_event.get("selection", {}).get("rows", [])

        if l1_indices:
            selected_l1_ids = [l1_display.iloc[i]["id"] for i in l1_indices]
        else:
            # If nothing selected in L1, show ALL children of the visible L1s?
            # Or show None?
            # User request: "Default: All".
            selected_l1_ids = l1_display["id"].tolist()

        # Action Bar for L1 (Edit/Delete)
        # Only show if EXACTLY ONE row is selected manually?
        # Or if "selected_l1_ids" has length 1?
        # Note: If default is "All" (implicit), then len > 1 usually.
        # Strict rule: Explicit selection of 1 row is needed for actions.
        # We can detect explicit selection by checking l1_indices, not selected_l1_ids (which defaults to all).
        if len(l1_indices) == 1:
            _render_action_bar(
                1, "MIXED", l1_all, [selected_l1_ids[0]] if len(l1_indices) == 1 else []
            )
        elif len(l1_indices) > 1:
            st.caption(f"{len(l1_indices)}개 선택됨")

# --- Col 3: L2 Selection ---
with cols[2]:
    st.markdown("### 3. 상세 (L2)")

    if not selected_l1_ids:
        st.info("표시할 하위 계정이 없습니다.")
    else:
        l2_all = accounts_df[
            (accounts_df["level"] == 2)
            & (accounts_df["parent_id"].isin(selected_l1_ids))
        ].copy()

        if l2_all.empty:
            st.info("하위 계정이 없습니다.")
        else:
            l2_display = _display_df(l2_all, level=2, include_parent=True)

            l2_event = st.dataframe(
                l2_display,
                key=f"sel_l2_{len(selected_l1_ids)}",
                on_select="rerun",
                selection_mode="single-row",
                hide_index=True,
                use_container_width=True,
                height=500,
                column_config={
                    "id": None,
                    "계정ID": st.column_config.NumberColumn(
                        "ID", format="%d", width="small"
                    ),
                    "계정명": st.column_config.TextColumn("계정명", width="medium"),
                    "상위계정": st.column_config.TextColumn("상위계정", width="small"),
                },
            )

            l2_indices = l2_event.get("selection", {}).get("rows", [])
            if l2_indices:
                sel_id = l2_display.iloc[l2_indices[0]]["id"]
                _render_action_bar(2, "MIXED", l2_all, [sel_id])
