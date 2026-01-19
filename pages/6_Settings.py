from __future__ import annotations

import re
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Literal

import pandas as pd
import streamlit as st

try:
    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
    from st_aggrid.shared import DataReturnMode, GridUpdateMode
except Exception:  # noqa: BLE001
    AgGrid = None  # type: ignore[assignment]
    GridOptionsBuilder = None  # type: ignore[assignment]
    JsCode = None  # type: ignore[assignment]

from core.db import apply_migrations, fetch_df, get_connection
from core.services.account_service import (
    create_user_account,
    delete_user_account,
    update_user_account,
)

Action = Literal["—", "편집", "하위계정추가", "삭제"]

NO_ACTION: Action = "—"
ACTIONS: list[Action] = [NO_ACTION, "편집", "하위계정추가", "삭제"]

_AGGRID_THEME = "streamlit"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_streamlit_theme_tokens() -> dict[str, str]:
    """Parse .streamlit/config.toml and return theme tokens.

    Falls back to built-in defaults if the file is missing or malformed.
    """

    defaults: dict[str, str] = {
        "backgroundColor": "rgb(24, 28, 54)",
        "secondaryBackgroundColor": "rgb(24, 28, 54)",
        "textColor": "rgb(231, 231, 240)",
        "primaryColor": "rgb(85, 85, 222)",
        "borderColor": "rgb(59, 80, 106)",
        "dataframeHeaderBackgroundColor": "rgb(31, 37, 70)",
        "sidebarBackgroundColor": "rgb(9, 16, 44)",
    }

    config_path = _repo_root() / ".streamlit" / "config.toml"
    if not config_path.exists():
        return defaults

    try:
        with config_path.open("rb") as f:
            parsed = tomllib.load(f)
    except Exception:  # noqa: BLE001
        return defaults

    theme = parsed.get("theme")
    if not isinstance(theme, dict):
        return defaults

    tokens = dict(defaults)
    for key in [
        "backgroundColor",
        "secondaryBackgroundColor",
        "textColor",
        "primaryColor",
        "borderColor",
        "dataframeHeaderBackgroundColor",
    ]:
        value = theme.get(key)
        if isinstance(value, str) and value:
            tokens[key] = value

    sidebar = theme.get("sidebar")
    if isinstance(sidebar, dict):
        sbg = sidebar.get("backgroundColor")
        if isinstance(sbg, str) and sbg:
            tokens["sidebarBackgroundColor"] = sbg

    return tokens


_RGB_RE = re.compile(r"^rgb\((\s*\d+\s*),(\s*\d+\s*),(\s*\d+\s*)\)$")


def _with_alpha(color: str, alpha: float) -> str:
    match = _RGB_RE.match(color.strip())
    if not match:
        return color
    r, g, b = match.groups()
    return f"rgba({r.strip()}, {g.strip()}, {b.strip()}, {alpha})"


def _build_aggrid_custom_css(tokens: dict[str, str]) -> dict[str, dict[str, str]]:
    bg = tokens["backgroundColor"]
    header_bg = tokens["dataframeHeaderBackgroundColor"]
    text = tokens["textColor"]
    border = tokens["borderColor"]
    primary = tokens["primaryColor"]
    menu_bg = tokens["sidebarBackgroundColor"]

    hover_bg = _with_alpha(primary, 0.15)

    return {
        ".ag-theme-streamlit .ag-root-wrapper": {
            "background-color": bg,
            "color": text,
            "border": f"1px solid {border}",
        },
        ".ag-theme-streamlit .ag-header": {
            "background-color": header_bg,
            "color": text,
            "border-bottom": f"1px solid {border}",
        },
        ".ag-theme-streamlit .ag-row": {
            "background-color": bg,
            "border-color": border,
        },
        ".ag-theme-streamlit .ag-row-hover": {
            "background-color": hover_bg,
        },
        ".ag-theme-streamlit .ag-cell": {
            "border-color": border,
        },
        ".ag-theme-streamlit .ag-checkbox-input-wrapper": {
            "border": f"1px solid {border}",
        },
        ".ag-theme-streamlit .ag-checkbox-input-wrapper::after": {
            "color": text,
        },
        ".ag-theme-streamlit .ag-menu": {
            "background-color": menu_bg,
            "color": text,
            "border": f"1px solid {border}",
        },
    }


def _aggrid_custom_css() -> dict[str, dict[str, str]]:
    return _build_aggrid_custom_css(_load_streamlit_theme_tokens())


st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")

conn = get_connection()
apply_migrations(conn)

st.title("설정")
st.caption("시스템 전역 설정 및 계정과목(CoA) 관리")

# --- App Settings Section ---
from core.services.settings_service import get_base_currency, set_base_currency

current_base = get_base_currency(conn)

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
            set_base_currency(conn, new_base)
            st.success(f"기준 통화가 {new_base}로 변경되었습니다.")
            st.rerun()

st.divider()

# --- Market Data Section ---
from core.services.market_data_service import MarketDataService

md_service = MarketDataService(conn)

with st.expander("📊 외부 시장 데이터 (Market Data)", expanded=True):
    st.subheader("💱 수동 환율 입력")
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    with c1:
        fx_quote = st.selectbox(
            "외화", ["USD", "JPY", "EUR", "CNY"], key="market_fx_quote"
        )
    with c2:
        latest_fx = md_service.get_latest_fx(current_base, fx_quote)
        fx_rate_val = latest_fx["rate"] if latest_fx else 1350.0
        new_fx_rate = st.number_input(
            f"환율 ({current_base}/{fx_quote})",
            min_value=0.0,
            value=float(fx_rate_val),
            step=0.1,
        )
    with c3:
        as_of_date = st.date_input("기준일", datetime.now(), key="fx_as_of")
    with c4:
        st.write("")
        st.write("")
        if st.button("FX 저장", use_container_width=True):
            md_service.save_manual_fx_rate(
                current_base, fx_quote, new_fx_rate, as_of_date.isoformat()
            )
            st.success(f"{fx_quote} 환율 저장 완료")
            st.rerun()

    st.divider()

    st.subheader("📈 주식/ETF 가격 동기화 (Alpha Vantage)")
    last_price_sync = md_service.get_last_sync_log("price")
    if last_price_sync:
        st.caption(
            f"마지막 동기화: {last_price_sync['started_at']} ({last_price_sync['status']})"
        )

    sc1, sc2, sc3 = st.columns([2, 4, 1])
    with sc1:
        market_choice = st.selectbox("시장", ["US"], index=0)
    with sc2:
        symbols_str = st.text_input(
            "심볼 (쉼표로 구분)", placeholder="AAPL, MSFT, TSLA"
        )
    with sc3:
        st.write("")
        st.write("")
        if st.button("지금 동기화", use_container_width=True):
            if not symbols_str:
                st.error("심볼을 입력해주세요.")
            else:
                try:
                    symbols = [
                        s.strip().upper() for s in symbols_str.split(",") if s.strip()
                    ]
                    with st.spinner("Alpha Vantage에서 데이터를 가져오는 중..."):
                        md_service.sync_prices(symbols, market_choice)
                    st.success(f"{len(symbols)}개 심볼 동기화 완료")
                    st.rerun()
                except Exception as e:
                    st.error(f"동기화 실패: {str(e)}")

    # Show latest prices table
    latest_prices_df = fetch_df(
        conn,
        "SELECT symbol, market, price, currency, as_of FROM market_prices ORDER BY symbol ASC, as_of DESC",
    )
    if not latest_prices_df.empty:
        # Keep only latest for each symbol
        latest_prices_df = latest_prices_df.sort_values(
            "as_of", ascending=False
        ).drop_duplicates("symbol")
        st.dataframe(latest_prices_df, use_container_width=True, hide_index=True)

if AgGrid is None:
    st.error("AgGrid UI가 설치되어 있지 않습니다. `uv sync`를 실행해 주세요.")
    st.stop()


def _load_accounts_df() -> pd.DataFrame:
    return fetch_df(
        conn,
        """
        SELECT a.id, a.name, a.type, a.parent_id, a.is_active, a.is_system, a.level, a.allow_posting,
               p.name AS parent_name
        FROM accounts a
        LEFT JOIN accounts p ON p.id = a.parent_id
        ORDER BY a.type, a.level, a.name
        """,
    )


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
    return f"coa_selected_{type_}_L{level}_{parent_part}"


def _grid_key(level: int, type_: str, parent_ids: list[int] | None) -> str:
    parent_part = "root" if not parent_ids else "_".join(map(str, parent_ids))
    return f"coa_grid_{type_}_L{level}_{parent_part}"


def _reset_grid(level: int, type_: str, parent_ids: list[int] | None) -> None:
    st.session_state.pop(_grid_key(level, type_, parent_ids), None)


def _get_selected_ids(
    *,
    level: int,
    type_: str,
    parent_ids: list[int] | None,
    all_ids: list[int],
) -> list[int]:
    key = _selection_key(level, type_, parent_ids)
    if key not in st.session_state:
        st.session_state[key] = list(all_ids)
    raw = st.session_state.get(key)
    if not isinstance(raw, list):
        return []
    return [int(v) for v in raw]


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

    if level > 1:
        indent = "  " * (level - 1)
        display["계정명"] = level_df["name"].apply(lambda x: f"{indent}↳ {x}")
    else:
        display["계정명"] = level_df["name"].astype(str)

    if include_parent:
        display["상위계정"] = level_df["parent_name"].fillna("").astype(str)

    display["전표허용"] = level_df["전표허용"].astype(str)
    if include_active:
        display["활성"] = level_df["활성"].astype(str)
    display["⋯"] = NO_ACTION
    return display


def _render_aggrid(
    *,
    df: pd.DataFrame,
    level: int,
    type_: str,
    parent_ids: list[int] | None,
    selected_ids: list[int],
    allow_actions: bool,
    height: int,
) -> tuple[list[int], str | None, int | None]:
    if df.empty:
        return [], None, None

    selected_set = {int(v) for v in selected_ids}

    builder = GridOptionsBuilder.from_dataframe(df)
    builder.configure_default_column(resizable=True, sortable=True, filter=True)
    builder.configure_column("id", hide=True)

    # 체크박스가 안 보이는 케이스를 방지하기 위해, 특정 컬럼에 checkboxSelection을 명시합니다.
    checkbox_col = "계정명" if "계정명" in df.columns else df.columns[0]
    builder.configure_column(
        checkbox_col,
        checkboxSelection=True,
        headerCheckboxSelection=True,
        headerCheckboxSelectionFilteredOnly=False,
        pinned="left",
        width=260 if checkbox_col == "계정명" else None,
    )

    builder.configure_selection(
        selection_mode="multiple",
        use_checkbox=False,
        header_checkbox=False,
        pre_selected_rows=[
            idx
            for idx, account_id in enumerate(df["id"].tolist())
            if int(account_id) in selected_set
        ],
    )

    # streamlit-aggrid 버전에 따라 configure_selection이 받는 인자가 달라서,
    # 클릭 동작 관련 옵션은 gridOptions로 전달합니다.
    builder.configure_grid_options(
        suppressRowClickSelection=True,
        rowMultiSelectWithClick=True,
    )

    if "⋯" in df.columns:
        builder.configure_column(
            "⋯",
            header_name="액션",
            editable=False,
            hide=True,
        )

        # NOTE: 우클릭 컨텍스트 메뉴가 동작하지 않는 환경용 대안(드롭다운 액션 컬럼).
        #       현재는 UX 단순화를 위해 숨김 처리하고, 코드는 보존합니다.
        # builder.configure_column(
        #     "⋯",
        #     header_name="액션",
        #     editable=allow_actions,
        #     hide=False,
        #     cellEditor="agSelectCellEditor" if allow_actions else None,
        #     cellEditorParams={"values": ACTIONS} if allow_actions else None,
        #     pinned="right",
        #     width=120,
        # )

        if allow_actions and JsCode is not None:
            ctx_menu_js = JsCode(
                """
function(params) {
    const base = [
        {
            name: '편집',
            action: function() { params.node.setDataValue('⋯', '편집'); },
        },
        {
            name: '하위계정추가',
            action: function() { params.node.setDataValue('⋯', '하위계정추가'); },
        },
        'separator',
        {
            name: '삭제',
            action: function() { params.node.setDataValue('⋯', '삭제'); },
        },
    ];

    // 선택을 같이 맞춰줌(우클릭 직후에도 선택 체크박스가 보이게)
    if (params && params.node) {
        params.node.setSelected(true, true);
    }

    return base;
}
"""
            )
            builder.configure_grid_options(getContextMenuItems=ctx_menu_js)

    if not callable(AgGrid):
        # Fallback when AgGrid is unavailable or not callable
        st.dataframe(df)
        return [], None, None

    try:
        grid_response = AgGrid(
            df,
            gridOptions=builder.build(),
            height=height,
            key=_grid_key(level, type_, parent_ids),
            data_return_mode=DataReturnMode.AS_INPUT,
            update_mode=GridUpdateMode.VALUE_CHANGED | GridUpdateMode.SELECTION_CHANGED,
            allow_unsafe_jscode=allow_actions,
            enable_enterprise_modules=False,
            theme=_AGGRID_THEME,
            custom_css=_aggrid_custom_css(),
        )

        # NOTE: Enterprise 모듈을 사용하지 않는 정책이지만, 일부 환경에서 컨텍스트 메뉴가
        #       비활성화되는 경우가 있어 옵션으로 남겨둡니다.
        # grid_response = AgGrid(
        #     df,
        #     gridOptions=builder.build(),
        #     height=height,
        #     key=_grid_key(level, type_, parent_ids),
        #     data_return_mode=DataReturnMode.AS_INPUT,
        #     update_mode=GridUpdateMode.VALUE_CHANGED | GridUpdateMode.SELECTION_CHANGED,
        #     allow_unsafe_jscode=allow_actions,
        #     enable_enterprise_modules=allow_actions,
        #     theme=_AGGRID_THEME,
        #     custom_css=_aggrid_custom_css(),
        # )
    except Exception as e:  # noqa: BLE001
        st.error(f"AgGrid 실행 오류: {e}")
        st.dataframe(df)
        return [], None, None

    selected_rows_raw = grid_response.get("selected_rows")
    if selected_rows_raw is None:
        selected_rows_list: list[dict] = []
    elif isinstance(selected_rows_raw, pd.DataFrame):
        selected_rows_list = selected_rows_raw.to_dict(orient="records")
    elif isinstance(selected_rows_raw, list):
        selected_rows_list = selected_rows_raw
    else:
        selected_rows_list = []

    new_selected_ids = []
    for row in selected_rows_list:
        idv = row.get("id")
        if idv is None:
            continue
        try:
            new_selected_ids.append(int(idv))
        except (TypeError, ValueError):
            try:
                new_selected_ids.append(int(str(idv)))
            except (TypeError, ValueError):
                continue

    action: str | None = None
    action_id: int | None = None

    edited_df = grid_response.get("data")
    if (
        allow_actions
        and isinstance(edited_df, pd.DataFrame)
        and "⋯" in edited_df.columns
    ):
        changed = edited_df.loc[edited_df["⋯"].astype(str) != NO_ACTION]
        if not changed.empty:
            action = str(changed.iloc[0]["⋯"])
            action_id = int(changed.iloc[0]["id"])

    return new_selected_ids, action, action_id


@st.dialog("계정 추가")
def _dialog_create_child(type_: str, parent_id: int) -> None:
    st.caption("상위 계정은 시스템(Level 1) 집계 계정이어야 합니다.")

    name = st.text_input("계정명")
    is_active = st.checkbox("활성", value=True)
    st.selectbox("통화", ["KRW", "USD", "JPY", "EUR"], key="new_acc_currency")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("생성", type="primary"):
            try:
                create_user_account(
                    conn,
                    name=name,
                    type_=type_,
                    parent_id=int(parent_id),
                    is_active=bool(is_active),
                    currency=st.session_state.get("new_acc_currency", "KRW"),
                )
                st.success("계정을 생성했습니다.")
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(str(e))
    with col2:
        if st.button("닫기"):
            st.rerun()


@st.dialog("계정 편집")
def _dialog_edit(account_id: int, current_name: str, current_active: bool) -> None:
    name = st.text_input("계정명", value=current_name)
    is_active = st.checkbox("활성", value=current_active)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("저장", type="primary"):
            try:
                update_user_account(
                    conn, int(account_id), name=name, is_active=bool(is_active)
                )
                st.success("저장했습니다.")
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(str(e))
    with col2:
        if st.button("닫기"):
            st.rerun()


@st.dialog("계정 삭제")
def _dialog_delete(account_id: int, account_name: str) -> None:
    st.warning("삭제는 되돌릴 수 없습니다.")
    st.write(f"대상: {account_name} (ID={account_id})")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("삭제", type="primary"):
            try:
                delete_user_account(conn, int(account_id))
                st.success("삭제했습니다.")
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(str(e))
    with col2:
        if st.button("닫기"):
            st.rerun()


def _handle_action(action: Action, account_row: dict, type_: str) -> None:
    if action == NO_ACTION:
        return

    is_system = int(account_row.get("is_system", 0)) == 1
    allow_posting = int(account_row.get("allow_posting", 0)) == 1
    level = int(account_row.get("level", 0))

    if action in {"편집", "삭제"} and is_system:
        st.warning("시스템(Level 1) 계정은 수정/삭제할 수 없습니다.")
        return

    if action == "편집":
        _dialog_edit(
            int(account_row["id"]),
            current_name=str(account_row["name"]),
            current_active=bool(int(account_row["is_active"]) == 1),
        )
        return

    if action == "삭제":
        _dialog_delete(int(account_row["id"]), account_name=str(account_row["name"]))
        return

    if action == "하위계정추가":
        if not is_system or level != 1 or allow_posting:
            st.info(
                "현재 MVP에서는 시스템(Level 1) 집계 계정 아래(L2)만 생성할 수 있습니다."
            )
            return
        _dialog_create_child(type_=type_, parent_id=int(account_row["id"]))


st.subheader("계정과목(CoA)")
st.caption(
    "- System(Level 1)은 읽기 전용이며 직접 분개 불가\n- 사용자 계정(leaf)만 전표 허용"
)

accounts_df = _load_accounts_df()

TYPE_ORDER = ["ASSET", "LIABILITY", "EQUITY", "INCOME", "EXPENSE"]
selected_type = st.selectbox("계정 유형(L0)", TYPE_ORDER)

section = accounts_df[accounts_df["type"] == selected_type].copy()
section = _format_section(section)

cols = st.columns(3)

with cols[0]:
    st.markdown("**L1 (System)**")
    st.caption("행을 우클릭하면 액션 메뉴가 뜹니다.")

    l1_df = _level_slice(section, level=1, parent_ids=None)
    if len(l1_df) == 0:
        st.info("L1 계정이 없습니다. 마이그레이션/seed를 확인하세요.")
        selected_l1_ids: list[int] = []
    else:
        l1_ids = l1_df["id"].astype(int).tolist()
        l1_sel_key = _selection_key(1, selected_type, None)

        l1_selected_ids = _get_selected_ids(
            level=1,
            type_=selected_type,
            parent_ids=None,
            all_ids=l1_ids,
        )

        l1_display = _display_df(
            l1_df,
            level=1,
            include_parent=False,
            include_active=False,
        )

        selected_l1_ids, action, action_id = _render_aggrid(
            df=l1_display,
            level=1,
            type_=selected_type,
            parent_ids=None,
            selected_ids=l1_selected_ids,
            allow_actions=True,
            height=420,
        )
        st.session_state[l1_sel_key] = selected_l1_ids

        if action and action_id is not None and action != NO_ACTION:
            account = section[section["id"] == int(action_id)].iloc[0].to_dict()

            last_key = f"coa_last_action_{selected_type}_L1"
            marker = (int(action_id), str(action))
            if st.session_state.get(last_key) != marker:
                st.session_state[last_key] = marker
                _reset_grid(1, selected_type, None)
                _handle_action(action, account, selected_type)

with cols[1]:
    st.markdown("**L2 (User)**")
    st.caption("행을 우클릭하면 액션 메뉴가 뜹니다.")

    if not selected_l1_ids:
        st.info("L1을 선택하면 하위(L2)가 표시됩니다.")
        selected_l2_ids: list[int] = []
    else:
        l2_df = _level_slice(section, level=2, parent_ids=selected_l1_ids)
        if len(l2_df) == 0:
            st.info("하위(L2) 계정이 없습니다.")
            selected_l2_ids = []
        else:
            l2_ids = l2_df["id"].astype(int).tolist()
            l2_sel_key = _selection_key(2, selected_type, selected_l1_ids)

            l2_selected_ids = _get_selected_ids(
                level=2,
                type_=selected_type,
                parent_ids=selected_l1_ids,
                all_ids=l2_ids,
            )

            l2_display = _display_df(
                l2_df,
                level=2,
                include_parent=True,
            )

            selected_l2_ids, action, action_id = _render_aggrid(
                df=l2_display,
                level=2,
                type_=selected_type,
                parent_ids=selected_l1_ids,
                selected_ids=l2_selected_ids,
                allow_actions=True,
                height=420,
            )
            st.session_state[l2_sel_key] = selected_l2_ids

            if action and action_id is not None and action != NO_ACTION:
                account = section[section["id"] == int(action_id)].iloc[0].to_dict()

                last_key = f"coa_last_action_{selected_type}_L2_{'_'.join(map(str, selected_l1_ids))}"
                marker = (int(action_id), str(action))
                if st.session_state.get(last_key) != marker:
                    st.session_state[last_key] = marker
                    _reset_grid(2, selected_type, selected_l1_ids)
                    _handle_action(action, account, selected_type)

with cols[2]:
    st.markdown("**L3 (Read-only)**")
    st.caption("현재 MVP는 L2 생성/관리 중심")

    if not selected_l2_ids:
        st.info("L2를 선택하면 하위(L3)가 표시됩니다.")
    else:
        l3_df = _level_slice(section, level=3, parent_ids=selected_l2_ids)
        if len(l3_df) == 0:
            st.info("하위(L3) 계정이 없습니다.")
        else:
            l3_ids = l3_df["id"].astype(int).tolist()
            l3_sel_key = _selection_key(3, selected_type, selected_l2_ids)

            l3_selected_ids = _get_selected_ids(
                level=3,
                type_=selected_type,
                parent_ids=selected_l2_ids,
                all_ids=l3_ids,
            )

            l3_display = _display_df(
                l3_df,
                level=3,
                include_parent=True,
            )

            selected_l3_ids, _, _ = _render_aggrid(
                df=l3_display,
                level=3,
                type_=selected_type,
                parent_ids=selected_l2_ids,
                selected_ids=l3_selected_ids,
                allow_actions=False,
                height=420,
            )
            st.session_state[l3_sel_key] = selected_l3_ids
