from datetime import date
import pandas as pd
import streamlit as st

try:
    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
    from st_aggrid.shared import DataReturnMode, GridUpdateMode
except ImportError:
    AgGrid = None
    GridOptionsBuilder = None
    JsCode = None
    DataReturnMode = None
    GridUpdateMode = None

from core.db import apply_migrations, get_connection
from core.services.asset_service import (
    add_valuation,
    create_asset,
    latest_valuation,
    list_assets,
    update_asset,
    delete_asset,
    valuation_history,
)
from core.services.ledger_service import account_balances, list_posting_accounts
from core.services.valuation_service import ValuationService
from core.services.settings_service import get_base_currency

NO_ACTION = "-"
EDIT_ACTION = "✏️ 편집"
DELETE_ACTION = "🗑️ 삭제"

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
            "연결계정ID": linked_account_id,
            "메모": a["note"],
            "구분": "원장기반" if is_ledger_based else "인벤토리",
            "원장잔액": float(ledger_balances.get(linked_account_id, 0.0)),
        }
    )


@st.dialog("자산 수정")
def _dialog_edit_asset(asset: dict, asset_accounts: list):
    with st.form("edit_asset_form"):
        new_name = st.text_input("자산명", value=asset["자산명"])
        new_class = st.selectbox(
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
            index=[
                "CASH",
                "BANK",
                "STOCK",
                "CRYPTO",
                "REAL_ESTATE",
                "VEHICLE",
                "EQUIPMENT",
                "INTANGIBLE",
                "OTHER",
            ].index(asset["분류"]),
        )
        # Find index of current linked account
        acc_ids = [acc[0] for acc in asset_accounts]
        try:
            acc_idx = acc_ids.index(asset["연결계정ID"])
        except ValueError:
            acc_idx = 0

        new_linked = st.selectbox(
            "연결 계정",
            options=asset_accounts,
            format_func=lambda x: x[1],
            index=acc_idx,
        )
        new_date = st.date_input("취득일", value=date.fromisoformat(asset["취득일"]))
        new_cost = st.number_input(
            "취득가", min_value=0.0, value=float(asset["취득가"]), step=10000.0
        )
        new_note = st.text_area("메모", value=asset["메모"])

        if st.form_submit_button("저장"):
            try:
                update_asset(
                    conn,
                    asset_id=asset["id"],
                    name=new_name,
                    asset_class=new_class,
                    linked_account_id=new_linked[0],
                    acquisition_date=new_date,
                    acquisition_cost=new_cost,
                    note=new_note,
                )
                st.success("수정되었습니다.")
                st.rerun()
            except Exception as e:
                st.error(f"수정 실패: {e}")


@st.dialog("자산 삭제")
def _dialog_delete_asset(asset: dict):
    st.warning("⚠️ 자산을 삭제하면 모든 평가 이력도 함께 삭제됩니다.")
    st.write(f"대상: **{asset['자산명']}**")
    if st.button("영구 삭제", type="primary"):
        try:
            delete_asset(conn, asset["id"])
            st.success("삭제되었습니다.")
            st.rerun()
        except Exception as e:
            st.error(f"삭제 실패: {e}")


def _handle_asset_action(df: pd.DataFrame, asset_accounts: list):
    # Action handling using AgGrid selection logic (placeholder since we use selectbox column)
    # But since AgGrid is community, we use the "Action" column strategy
    pass


st.subheader("자산 목록")
val_service = ValuationService(conn)
latest_vals = val_service.get_valuations_for_dashboard()
base_currency = get_base_currency(conn)

# Add valuation info and Action column
for row in rows:
    v = latest_vals.get(row["id"])
    if v:
        row["최신평가액"] = f"{v['value_native']:,.0f} {v['currency']}"
        row["평가기준일"] = v["as_of_date"]
    else:
        row["최신평가액"] = "-"
        row["평가기준일"] = "-"
    row["⋯"] = NO_ACTION

df = pd.DataFrame(rows)

if not rows:
    st.info("등록된 자산이 없습니다. 아래에서 자산을 먼저 등록해 주세요.")
else:
    if AgGrid is None:
        st.warning("AgGrid가 설치되지 않아 편집/삭제 기능을 제한적으로 제공합니다.")
        cols_to_show = [
            "자산명",
            "분류",
            "취득일",
            "취득가",
            "최신평가액",
            "평가기준일",
            "연결계정",
            "구분",
            "원장잔액",
        ]
        st.dataframe(
            df[cols_to_show],
            width="stretch",
            hide_index=True,
            column_config={
                "취득가": st.column_config.NumberColumn(format="%.0f"),
                "원장잔액": st.column_config.NumberColumn(format="%.0f"),
            },
        )
    else:
        cols_to_show = [
            "id",
            "자산명",
            "분류",
            "취득일",
            "취득가",
            "최신평가액",
            "평가기준일",
            "연결계정",
            "구분",
            "원장잔액",
            "⋯",
        ]
        grid_df = df[cols_to_show].copy()

        gb = GridOptionsBuilder.from_dataframe(grid_df)
        gb.configure_default_column(resizable=True, sortable=True, filter=True)
        gb.configure_column("id", hide=True)
        gb.configure_column("취득가", valueFormatter="x.toLocaleString()")
        gb.configure_column("원장잔액", valueFormatter="x.toLocaleString()")

        # Action column with dropdown
        gb.configure_column(
            "⋯",
            editable=True,
            cellEditor="agSelectCellEditor",
            cellEditorParams={"values": [NO_ACTION, EDIT_ACTION, DELETE_ACTION]},
            width=100,
            pinned="right",
        )

        grid_options = gb.build()
        grid_response = AgGrid(
            grid_df,
            gridOptions=grid_options,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            update_mode=GridUpdateMode.VALUE_CHANGED,
            theme="balham",
            height=300,
            width="100%",
        )

        # Handle Action from value change
        updated_df = pd.DataFrame(grid_response["data"])
        if not updated_df.empty and "⋯" in updated_df.columns:
            action_row = updated_df[updated_df["⋯"] != NO_ACTION]
            if not action_row.empty:
                selected_asset = action_row.iloc[0].to_dict()
                action = selected_asset["⋯"]

                # Find original row to get all hidden data (memo, account id)
                original_row = df[df["id"] == selected_asset["id"]].iloc[0].to_dict()

                if action == EDIT_ACTION:
                    _dialog_edit_asset(original_row, asset_accounts)
                elif action == DELETE_ACTION:
                    _dialog_delete_asset(original_row)

st.divider()

st.subheader("📝 수기 평가(Manual Valuation) 입력")
asset_options = {int(r["id"]): f"{r['name']} ({r['asset_class']})" for r in assets}
if not asset_options:
    st.info("등록된 자산이 없습니다.")
else:
    with st.form("manual_val_form", clear_on_submit=True):
        sel_asset_id = st.selectbox(
            "자산 선택",
            options=list(asset_options.keys()),
            format_func=lambda x: asset_options[x],
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            val_date = st.date_input("평가 기준일", value=date.today())
        with c2:
            val_amount = st.number_input("평가 총액", min_value=0.0, step=10000.0)
        with c3:
            val_currency = st.selectbox(
                "통화",
                ["KRW", "USD", "JPY", "EUR"],
                index=(
                    ["KRW", "USD", "JPY", "EUR"].index(base_currency)
                    if base_currency in ["KRW", "USD", "JPY", "EUR"]
                    else 0
                ),
            )

        val_note = st.text_input("메모 (선택사항)")

        if st.form_submit_button("평가 저장"):
            try:
                val_service.upsert_asset_valuation(
                    asset_id=sel_asset_id,
                    as_of_date=val_date.isoformat(),
                    value_native=val_amount,
                    currency=val_currency,
                    note=val_note,
                )
                st.success("평가값이 저장되었습니다.")
                st.rerun()
            except Exception as e:
                st.error(f"저장 실패: {e}")

st.divider()

st.subheader("원장 기반 평가(Valuation) 추가 (기존)")
if not rows:
    st.info("등록된 자산이 없습니다.")
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
    st.dataframe(
        hist_df,
        width="stretch",
        hide_index=True,
        column_config={"금액": st.column_config.NumberColumn(format="%.0f")},
    )
