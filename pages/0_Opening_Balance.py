import json
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlmodel import Session, desc, select

from core.db import engine
from core.models import Account, JournalEntry, JournalLine
from core.services.account_service import create_user_account
from core.services.ledger_service import (
    create_opening_balance_entry,
    delete_opening_balance_entry,
    get_account_by_name,
    has_opening_balance_entry,
    list_accounts,
    list_posting_accounts,
)
from ui.utils import get_currency_config

st.set_page_config(page_title="Day0 Setup", page_icon="🧭", layout="wide")

# DB Session
session = Session(engine)

DRAFT_PATH = Path("data/day0_draft.json")


def load_draft():
    if not DRAFT_PATH.exists():
        st.error("임시 저장된 데이터가 없습니다.")
        return

    try:
        with open(DRAFT_PATH, encoding="utf-8") as f:
            data = json.load(f)

        st.session_state.asset_rows = data.get("asset_rows", 2)
        st.session_state.liab_rows = data.get("liab_rows", 2)

        # Restore Assets
        for item in data.get("assets", []):
            idx = item["index"]
            # Find the account tuple that matches the ID
            acc_id = item["account_id"]
            matched = next((a for a in asset_accounts if a[0] == acc_id), None)
            if matched:
                st.session_state[f"asset_account_{idx}"] = matched
            st.session_state[f"asset_amount_{idx}"] = item["amount"]

        # Restore Liabilities
        for item in data.get("liabilities", []):
            idx = item["index"]
            # Find the account tuple that matches the ID
            acc_id = item["account_id"]
            matched = next((a for a in liab_accounts if a[0] == acc_id), None)
            if matched:
                st.session_state[f"liab_account_{idx}"] = matched
            st.session_state[f"liab_amount_{idx}"] = item["amount"]

        st.toast("임시 저장된 데이터를 불러왔습니다.")
        st.rerun()
    except Exception as e:
        st.error(f"임시 저장 불러오기 실패: {e}")


def save_draft():
    data = {
        "timestamp": datetime.now().isoformat(),
        "asset_rows": st.session_state.asset_rows,
        "liab_rows": st.session_state.liab_rows,
        "assets": [],
        "liabilities": [],
    }

    # Save Assets
    for i in range(st.session_state.asset_rows):
        account = st.session_state.get(f"asset_account_{i}")
        amount = st.session_state.get(f"asset_amount_{i}", 0.0)
        if account:
            data["assets"].append(
                {"index": i, "account_id": account[0], "amount": float(amount)}
            )

    # Save Liabilities
    for i in range(st.session_state.liab_rows):
        account = st.session_state.get(f"liab_account_{i}")
        amount = st.session_state.get(f"liab_amount_{i}", 0.0)
        if account:
            data["liabilities"].append(
                {"index": i, "account_id": account[0], "amount": float(amount)}
            )

    try:
        DRAFT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DRAFT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        st.toast("임시 저장되었습니다.")
    except Exception as e:
        st.error(f"임시 저장 실패: {e}")


st.title("Day0 기초 잔액 설정")

if DRAFT_PATH.exists():
    try:
        with open(DRAFT_PATH, encoding="utf-8") as f:
            meta = json.load(f)
            ts = meta.get("timestamp", "")[:16].replace("T", " ")
        st.info(f"💾 임시 저장된 데이터가 있습니다. ({ts})")
        if st.button("임시 저장 불러오기"):
            load_draft()
    except Exception:
        pass

st.caption(
    "과거 거래 복원 없이 오늘 기준 기초자산/부채를 입력해 OPENING_BALANCE 전표를 생성합니다."
)

accounts = list_accounts(session, active_only=True)
posting_accounts = list_posting_accounts(session, active_only=True)
asset_accounts = [
    (a["id"], a["name"]) for a in posting_accounts if a["type"] == "ASSET"
]
liab_accounts = [
    (a["id"], a["name"]) for a in posting_accounts if a["type"] == "LIABILITY"
]

if len(asset_accounts) == 0:
    st.warning(
        "⚠️ 등록된 자산/부채(Posting) 계정이 없습니다. 기초 설정을 위해 기본 계정을 생성하시겠습니까?"
    )
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("네, 기본 계정 생성 (현금, 통장, 카드)", type="primary"):
            try:
                # 1. Cash (Parent: 1001 현금)
                create_user_account(session, "현금 (기본)", "ASSET", 1001)
                # 2. Checking (Parent: 1002 보통예금)
                create_user_account(session, "급여통장", "ASSET", 1002)
                # 3. Credit Card (Parent: 2001 카드미지급금)
                create_user_account(session, "신용카드 (기본)", "LIABILITY", 2001)

                session.commit()
                st.success("기본 계정이 생성되었습니다! 새로고침합니다...")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"계정 생성 실패: {e}")

    st.info("또는 '설정 > 계정 관리' 메뉴에서 직접 계정을 생성할 수 있습니다.")
    st.stop()

opening_equity = get_account_by_name(session, "기초순자산(Opening Equity)", "EQUITY")
if opening_equity is None:
    opening_equity = get_account_by_name(session, "기초순자산", "EQUITY")
if opening_equity is None:
    opening_equity = get_account_by_name(session, "기초자본(Opening Balance)", "EQUITY")

if opening_equity is None:
    # Auto-create if missing (Self-healing)
    try:
        # 1. Ensure L1 Equity exists (ID 3001 as per seed)
        l1_equity = session.get(Account, 3001)
        if not l1_equity:
            l1_equity = Account(
                id=3001,
                name="자본/순자산",
                type="EQUITY",
                level=1,
                is_system=True,
                allow_posting=False,
                is_active=True,
                currency="KRW",
            )
            session.add(l1_equity)
            session.commit()  # Commit to ensure parent exists for FK

        # 2. Create L2 Opening Equity (ID 300101)
        opening_equity = Account(
            id=300101,
            name="기초순자산(Opening Equity)",
            type="EQUITY",
            level=2,
            parent_id=3001,
            is_system=True,
            allow_posting=True,
            is_active=True,
            currency="KRW",
        )
        session.add(opening_equity)
        session.commit()
        session.refresh(opening_equity)
        opening_equity = opening_equity.model_dump()
        st.toast("기초순자산 계정(300101)이 복구되었습니다.")

    except Exception as e:
        st.error(f"기초순자산(EQUITY) 계정이 없으며 자동 생성에 실패했습니다: {e}")
        st.stop()

# Ensure the equity account is active
if not opening_equity.get("is_active", True):
    st.warning(
        f"계정 '{opening_equity['name']}'이 비활성화 상태입니다. 기초 잔액 설정(Day0)을 진행하려면 이 계정이 활성화되어야 합니다."
    )
    if st.button("계정 활성화하기"):
        from core.services.account_service import update_account

        update_account(session, opening_equity["id"], is_active=True)
        st.success(f"계정 '{opening_equity['name']}'이 활성화되었습니다.")
        st.rerun()
    st.stop()

if has_opening_balance_entry(session):
    st.warning(
        "이미 OPENING_BALANCE 전표가 존재합니다. 재생성은 기본적으로 차단됩니다."
    )

    existing = session.exec(
        select(JournalEntry)
        .where(JournalEntry.source == "opening_balance")
        .order_by(desc(JournalEntry.id))
    ).first()

    if existing:
        st.write(
            f"전표ID: {existing.id} / 날짜: {existing.entry_date} / 설명: {existing.description}"
        )
        # Using ORM join
        stmt = (
            select(
                Account.name,
                Account.type,
                JournalLine.debit,
                JournalLine.credit,
                JournalLine.memo,
            )
            .join(Account, Account.id == JournalLine.account_id)
            .where(JournalLine.entry_id == existing.id)
            .order_by(Account.type, Account.name)
        )

        lines = session.exec(stmt).all()

        df = pd.DataFrame(lines, columns=["계정", "유형", "차변", "대변", "메모"])
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "차변": st.column_config.NumberColumn(format="%.0f"),
                "대변": st.column_config.NumberColumn(format="%.0f"),
            },
        )

    st.divider()
    st.subheader("⚠️ 초기화 후 재입력")
    st.info("기초 잔액을 수정하려면 기존 전표를 삭제하고 다시 입력해야 합니다.")
    if st.button("기존 기초 잔액 전표 삭제 및 초기화"):
        delete_opening_balance_entry(session)
        st.success("초기화되었습니다. 페이지를 새로고침합니다.")
        st.rerun()

    st.stop()

if "asset_rows" not in st.session_state:
    st.session_state.asset_rows = 2
if "liab_rows" not in st.session_state:
    st.session_state.liab_rows = 2

st.subheader("입력")

with st.form("opening_balance_form"):
    col1, col2 = st.columns(2)
    with col1:
        entry_date = st.date_input("기준일(Day0)", value=date.today())
    with col2:
        description = st.text_input("설명", value="OPENING_BALANCE")

    st.markdown("#### 자산(ASSET) 입력")
    for i in range(st.session_state.asset_rows):
        a1, a2 = st.columns([3, 2])
        with a1:
            st.selectbox(
                f"자산 계정 #{i + 1}",
                options=asset_accounts,
                format_func=lambda x: x[1],
                key=f"asset_account_{i}",
            )
            # Detect currency of selected account
            sel_acc_tuple = st.session_state.get(f"asset_account_{i}")
            # Tuple is (id, name). We need to find the dict to get currency. (optimization: lookup map)
            # Since asset_accounts is list of tuples, we check the full 'posting_accounts' list
            selected_currency = "KRW"
            if sel_acc_tuple:
                acc_info = next(
                    (a for a in posting_accounts if a["id"] == sel_acc_tuple[0]), None
                )
                if acc_info:
                    selected_currency = acc_info.get("currency", "KRW")

            curr_cfg = get_currency_config(selected_currency)

        with a2:
            is_int = curr_cfg["precision"] == 0
            safe_step = int(curr_cfg["step"]) if is_int else float(curr_cfg["step"])
            safe_val = (
                int(st.session_state.get(f"asset_amount_{i}", 0))
                if is_int
                else float(st.session_state.get(f"asset_amount_{i}", 0.0))
            )

            st.number_input(
                f"금액 #{i + 1}",
                min_value=0 if is_int else 0.0,
                step=safe_step,
                format=curr_cfg["format"],
                value=safe_val,
                key=f"asset_amount_{i}",
            )

    if st.form_submit_button("자산 행 추가"):
        st.session_state.asset_rows += 1
        st.rerun()

    st.markdown("#### 부채(LIABILITY) 입력")
    for i in range(st.session_state.liab_rows):
        l1, l2 = st.columns([3, 2])
        with l1:
            st.selectbox(
                f"부채 계정 #{i + 1}",
                options=liab_accounts,
                format_func=lambda x: x[1],
                key=f"liab_account_{i}",
            )
            # Detect currency
            sel_acc_tuple = st.session_state.get(f"liab_account_{i}")
            selected_currency = "KRW"
            if sel_acc_tuple:
                acc_info = next(
                    (a for a in posting_accounts if a["id"] == sel_acc_tuple[0]), None
                )
                if acc_info:
                    selected_currency = acc_info.get("currency", "KRW")

            curr_cfg = get_currency_config(selected_currency)

        with l2:
            is_int = curr_cfg["precision"] == 0
            safe_step = int(curr_cfg["step"]) if is_int else float(curr_cfg["step"])
            safe_val = (
                int(st.session_state.get(f"liab_amount_{i}", 0))
                if is_int
                else float(st.session_state.get(f"liab_amount_{i}", 0.0))
            )

            st.number_input(
                f"금액 #{i + 1}",
                min_value=0 if is_int else 0.0,
                step=safe_step,
                format=curr_cfg["format"],
                value=safe_val,
                key=f"liab_amount_{i}",
            )

    if st.form_submit_button("부채 행 추가"):
        st.session_state.liab_rows += 1
        st.rerun()

    st.markdown("#### 전표 미리보기")
    account_name = {a["id"]: a["name"] for a in accounts}
    account_currency = {a["id"]: a.get("currency", "KRW") for a in accounts}

    asset_lines: list[JournalLine] = []
    for i in range(st.session_state.asset_rows):
        account = st.session_state.get(f"asset_account_{i}")
        amount = float(st.session_state.get(f"asset_amount_{i}", 0.0))
        if account and amount > 0:
            asset_lines.append(
                JournalLine(
                    account_id=int(account[0]), debit=amount, credit=0.0, memo="Day0"
                )
            )

    liability_lines: list[JournalLine] = []
    for i in range(st.session_state.liab_rows):
        account = st.session_state.get(f"liab_account_{i}")
        amount = float(st.session_state.get(f"liab_amount_{i}", 0.0))
        if account and amount > 0:
            liability_lines.append(
                JournalLine(
                    account_id=int(account[0]), debit=0.0, credit=amount, memo="Day0"
                )
            )

    preview_rows = []
    total_debit = 0.0
    total_credit = 0.0
    for line in asset_lines:
        curr = account_currency.get(line.account_id, "KRW")
        preview_rows.append(
            {
                "계정": account_name.get(line.account_id, str(line.account_id)),
                "차변": line.debit,
                "대변": 0.0,
                "구분": "자산",
                "통화": curr,
            }
        )
        total_debit += line.debit

    for line in liability_lines:
        curr = account_currency.get(line.account_id, "KRW")
        preview_rows.append(
            {
                "계정": account_name.get(line.account_id, str(line.account_id)),
                "차변": 0.0,
                "대변": line.credit,
                "구분": "부채",
                "통화": curr,
            }
        )
        total_credit += line.credit

    gap = total_debit - total_credit
    if abs(gap) > 1e-9:
        if gap > 0:
            preview_rows.append(
                {
                    "계정": "기초순자산",
                    "차변": 0.0,
                    "대변": gap,
                    "구분": "자본",
                    "통화": "KRW",
                }
            )
            total_credit += gap
        else:
            preview_rows.append(
                {
                    "계정": "기초순자산",
                    "차변": -gap,
                    "대변": 0.0,
                    "구분": "자본",
                    "통화": "KRW",
                }
            )
            total_debit += -gap

    if preview_rows:
        preview_df = pd.DataFrame(preview_rows)
        # Apply standard formatting for column config
        # Since it's a mixed table (different currencies potentially),
        # we can't force one currency symbol easily on the column unless we use just number format
        # or separate native amount. For Day0 (mostly KRW), let's stick to standard number format
        # but with comma.

        # We will use simple NumberColumn without specific currency symbol to avoid confusion if mixed,
        # OR we default to KRW style format.
        # User asked for: "Currency symbol based on account's base currency".
        # Streamlit column config applies to the WHOLE column. We can't vary format per row.
        # Solution: Use simple comma formatting (format="%.2f" or "%d" depending on majority?)
        # Better: Just use standard comma format.

        st.dataframe(
            preview_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "차변": st.column_config.NumberColumn(format="%.2f"),
                "대변": st.column_config.NumberColumn(format="%.2f"),
                # "통화" column added for clarity
            },
        )
        # Summary footer formatting
        from ui.utils import format_currency

        disp_debit = format_currency(
            total_debit, "KRW"
        )  # Day0 total usually in base currency
        disp_credit = format_currency(total_credit, "KRW")

        st.caption(f"합계: 차변 {disp_debit} / 대변 {disp_credit}")
    else:
        st.info("자산 또는 부채 라인을 입력하세요.")

    cols = st.columns([1, 1])
    with cols[0]:
        submitted = st.form_submit_button("OPENING_BALANCE 생성", type="primary")
    with cols[1]:
        draft = st.form_submit_button("임시 저장")

    if draft:
        save_draft()
        # Do not proceed to creation if saving draft

    if submitted:
        try:
            entry_id = create_opening_balance_entry(
                session,
                entry_date=entry_date,
                description=description or "OPENING_BALANCE",
                asset_lines=asset_lines,
                liability_lines=liability_lines,
            )
            st.success(f"OPENING_BALANCE 전표 생성 완료: #{entry_id}")
            # draft cleanup (optional, but good UX)
            if DRAFT_PATH.exists():
                DRAFT_PATH.unlink()
        except Exception as e:
            st.error(str(e))
