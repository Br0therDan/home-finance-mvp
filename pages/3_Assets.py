from datetime import date

import pandas as pd
import streamlit as st
from sqlmodel import Session

try:
    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
    from st_aggrid.shared import DataReturnMode, GridUpdateMode
except ImportError:
    AgGrid = None
    GridOptionsBuilder = None
    JsCode = None
    DataReturnMode = None
    GridUpdateMode = None

from core.db import engine
from core.services.asset_service import (
    delete_asset,
    list_assets,
    update_asset,
)
from core.services.asset_transaction_service import dispose_asset, purchase_asset
from core.services.ledger_service import account_balances, list_posting_accounts
from core.services.settings_service import get_base_currency
from core.services.valuation_service import ValuationService

NO_ACTION = "-"
EDIT_ACTION = "✏️ 편집"
DELETE_ACTION = "🗑️ 삭제"
DISPOSE_ACTION = "💸 매각(처분)"

st.set_page_config(page_title="Assets", page_icon="🏠", layout="wide")

session = Session(engine)

# ========== UI: Header & Purchase ==========

# Pre-fetch accounts for dialogs and selection
accounts = list_posting_accounts(session, active_only=True)
asset_accounts = [(a["id"], a["name"]) for a in accounts if a["type"] == "ASSET"]

if len(asset_accounts) == 0:
    st.info("자산 하위(Posting) 계정이 없습니다. 설정에서 하위 계정을 먼저 생성하세요.")

# ========== Logic: Reconciliation ==========
assets = list_assets(session)
ledger_balances = account_balances(session)

# Group assets by linked_account_id
asset_inventory_value = {}
for a in assets:
    lid = int(a["linked_account_id"])
    asset_inventory_value[lid] = asset_inventory_value.get(lid, 0.0) + float(
        a["acquisition_cost"]
    )

# Compare with Ledger
reconcile_items = []
total_diff = 0.0
has_mismatch = False

for acid, name in asset_accounts:
    lid = int(acid)
    inventory_val = asset_inventory_value.get(lid, 0.0)
    ledger_val = float(ledger_balances.get(lid, 0.0))

    # Ledger balance for Asset account is Debit - Credit.
    # Usually Positive.

    diff = ledger_val - inventory_val
    if abs(diff) > 1.0:  # Tolerance 1 KRW
        reconcile_items.append(
            {
                "account": name,
                "ledger": ledger_val,
                "inventory": inventory_val,
                "diff": diff,
            }
        )
        total_diff += abs(diff)
        has_mismatch = True

with st.container():
    c1, c2 = st.columns([0.8, 0.2])
    with c1:
        st.title("자산대장")
        st.caption("유/무형 자산을 등록하고 평가(valuation) 이력을 관리한다.")
    with c2:
        if st.button("➕ 자산 매입 (Purchase)", type="primary"):
            st.session_state["show_purchase_dialog"] = True

# ========== UI: Reconciliation Dashboard ==========
if has_mismatch:
    st.error(
        f"⚠️ **데이터 불일치 감지**: 원장(Ledger)과 자산대장(Inventory) 간에 **{len(reconcile_items)}건**의 차이가 있습니다."
    )
    with st.expander("대사 내역 (Reconciliation Details)", expanded=True):
        rec_df = pd.DataFrame(reconcile_items)
        st.dataframe(
            rec_df,
            column_config={
                "ledger": st.column_config.NumberColumn("원장 잔액", format="%.0f"),
                "inventory": st.column_config.NumberColumn(
                    "자산대장 총액", format="%.0f"
                ),
                "diff": st.column_config.NumberColumn(
                    "차액 (Ledger - Inv)", format="%.0f"
                ),
            },
            hide_index=True,
            use_container_width=True,
        )
else:
    st.success(
        "✅ **Data Healthy**: 모든 자산 계정의 원장 잔액과 자산대장 총액이 일치합니다."
    )


if "show_purchase_dialog" not in st.session_state:
    st.session_state["show_purchase_dialog"] = False


@st.dialog("자산 매입 (Purchase Asset)")
def _dialog_purchase_asset(asset_accounts: list, liab_accounts: list):
    st.caption("자산 등록과 동시에 매입 분개(Ledger)를 자동 생성합니다.")

    with st.form("purchase_form"):
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
            "자산 계정 (Linked Account)",
            options=asset_accounts,
            format_func=lambda x: x[1],
        )
        pay_method = st.selectbox(
            "결제 계정 (Payment Account)",
            options=asset_accounts
            + liab_accounts,  # Pay with Cash/Bank or Card(Liability)
            format_func=lambda x: x[1],
        )

        acq_date = st.date_input("매입일 (취득일)", value=date.today())
        acq_cost = st.number_input(
            "매입 금액 (Cost)", min_value=0.0, value=0.0, step=10000.0
        )
        note = st.text_area("메모", value="")

        if st.form_submit_button("매입 확정"):
            if not name.strip():
                st.error("자산명을 입력하세요.")
            elif acq_cost <= 0:
                st.error("매입 금액은 0보다 커야 합니다.")
            else:
                try:
                    aid = purchase_asset(
                        session,
                        name=name.strip(),
                        asset_class=asset_class,
                        asset_sub_account_id=int(linked[0]),
                        payment_account_id=int(pay_method[0]),
                        acquisition_date=acq_date,
                        acquisition_cost=acq_cost,
                        note=note,
                    )
                    st.success(f"매입 완료: 자산 #{aid} 등록 및 전표 생성됨.")
                    st.session_state["show_purchase_dialog"] = False
                    st.rerun()
                except Exception as e:
                    st.error(f"오류 발생: {e}")


if st.session_state["show_purchase_dialog"]:
    # Prepare payment accounts (Asset + Liability)
    liab_list = [(a["id"], a["name"]) for a in accounts if a["type"] == "LIABILITY"]
    _dialog_purchase_asset(asset_accounts, liab_list)

st.divider()

# assets and ledger_balances are already fetched above for reconciliation

val_service = ValuationService(session)
latest_vals = val_service.get_valuations_for_dashboard()

rows = []
for a in assets:
    lv = latest_vals.get(int(a["id"]))
    linked_account_id = int(a["linked_account_id"])
    is_ledger_based = linked_account_id in ledger_balances

    # Prepare display strings immediately
    if lv:
        current_val_str = f"{lv['value_native']:,.0f} {lv['currency']}"
        val_date_str = lv["as_of_date"]
        val_native = float(lv["value_native"])
    else:
        current_val_str = "-"
        val_date_str = "-"
        val_native = None

    rows.append(
        {
            "id": int(a["id"]),
            "자산명": a["name"],
            "분류": a["asset_class"],
            "취득일": a["acquisition_date"],
            "취득가": float(a["acquisition_cost"]),
            "최근평가": val_native,
            "평가일": val_date_str,
            "최신평가액": current_val_str,
            "평가기준일": val_date_str,
            "연결계정": a["linked_account"],
            "연결계정ID": linked_account_id,
            "메모": a["note"],
            "구분": "원장기반" if is_ledger_based else "인벤토리",
            "원장잔액": float(ledger_balances.get(linked_account_id, 0.0)),
            "⋯": NO_ACTION,
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
        new_date = st.date_input(
            "취득일", value=date.fromisoformat(str(asset["취득일"]))
        )
        new_cost = st.number_input(
            "취득가", min_value=0.0, value=float(asset["취득가"]), step=10000.0
        )
        new_note = st.text_area("메모", value=asset["메모"])

        if st.form_submit_button("저장"):
            try:
                update_asset(
                    session,
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
            delete_asset(session, asset["id"])
            st.success("삭제되었습니다.")
            st.rerun()
        except Exception as e:
            st.error(f"삭제 실패: {e}")


@st.dialog("자산 매각 (Disposal)")
def _dialog_dispose_asset(asset: dict, all_accounts: list):
    st.caption("자산을 매각 처리하고 처분 손익을 자동으로 계산합니다.")

    # Filter accounts
    deposit_accounts = [
        (a["id"], a["name"]) for a in all_accounts if a["type"] == "ASSET"
    ]
    pl_accounts = [
        (a["id"], a["name"]) for a in all_accounts if a["type"] in ("INCOME", "EXPENSE")
    ]

    with st.form("dispose_form"):
        st.write(f"대상 자산: **{asset['자산명']}**")
        st.write(f"장부 가액(취득가): {asset['취득가']:,.0f} KRW")

        sale_date = st.date_input("처분일(매각일)", value=date.today())
        sale_price = st.number_input(
            "매각 금액(실수령액)",
            min_value=0.0,
            value=float(asset["취득가"]),
            step=10000.0,
        )

        deposit_acc = st.selectbox(
            "입금 계좌", options=deposit_accounts, format_func=lambda x: x[1]
        )
        gl_acc = st.selectbox(
            "처분 손익 계정 (Gain/Loss)",
            options=pl_accounts,
            format_func=lambda x: x[1],
            help="차액 발생 시 이 계정으로 처리됩니다.",
        )

        # Preview Gain/Loss
        gain_loss = sale_price - float(asset["취득가"])
        if gain_loss > 0:
            st.info(f"예상 처분 이익: {gain_loss:,.0f} KRW")
        elif gain_loss < 0:
            st.error(f"예상 처분 손실: {abs(gain_loss):,.0f} KRW")
        else:
            st.write("처분 손익 없음")

        if st.form_submit_button("매각 확정"):
            try:
                dispose_asset(
                    session,
                    asset_id=asset["id"],
                    asset_name=asset["자산명"],
                    linked_account_id=int(asset["연결계정ID"]),
                    disposal_date=sale_date,
                    sale_price=sale_price,
                    deposit_account_id=int(deposit_acc["id"]),
                    gain_loss_account_id=int(gl_acc["id"]),
                    book_value=float(asset["취득가"]),
                )
                st.success("매각 처리가 완료되었습니다.")
                st.rerun()
            except Exception as e:
                st.error(f"매각 실패: {e}")


def _handle_asset_action(df: pd.DataFrame, asset_accounts: list):
    # Action handling using AgGrid selection logic (placeholder since we use selectbox column)
    # But since AgGrid is community, we use the "Action" column strategy
    pass


st.subheader("자산 목록")
base_currency = get_base_currency(session)

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
            cellEditorParams={
                "values": [NO_ACTION, EDIT_ACTION, DELETE_ACTION, DISPOSE_ACTION]
            },
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
                elif action == DISPOSE_ACTION:
                    _dialog_dispose_asset(original_row, accounts)

st.divider()

st.subheader("📝 자산 평가 (Valuation)")
asset_options = {int(r["id"]): f"{r['name']} ({r['asset_class']})" for r in assets}

if not asset_options:
    st.info("등록된 자산이 없습니다.")
else:
    # Select asset OUTSIDE the form to trigger reactivity for history
    sel_asset_id = st.selectbox(
        "자산 선택",
        options=list(asset_options.keys()),
        format_func=lambda x: asset_options[x],
    )

    with st.form("manual_val_form", clear_on_submit=True):
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

    # History Section
    if sel_asset_id:
        st.markdown("---")
        st.markdown("**📊 평가 이력 (History)**")
        history = val_service.get_valuation_history(sel_asset_id)
        if history:
            hist_df = pd.DataFrame(
                [
                    {
                        "평가일": h["as_of_date"],
                        "금액": h["value_native"],
                        "통화": h["currency"],
                        "메모": h["note"] or "",
                        "수정일": h["updated_at"],
                    }
                    for h in history
                ]
            )
            st.dataframe(
                hist_df,
                use_container_width=True,
                hide_index=True,
                column_config={"금액": st.column_config.NumberColumn(format="%.0f")},
            )
        else:
            st.caption("평가 이력이 없습니다.")
