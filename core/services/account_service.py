from __future__ import annotations
import sqlite3
from typing import List, Dict, Optional

from core.models import Account, Asset, JournalLine

HOUSEHOLD_GROUP_LABELS = {
    "Cash": "현금 (Cash)",
    "Bank": "은행 (Bank)",
    "Credit Card": "신용카드 (Credit Card)",
    "Investment": "투자 (Investment)",
    "Home": "주거/주택 (Home)",
    "Vehicle": "차량 (Vehicle)",
    "Household Expenses": "생활비 (Household Expenses)",
    "Income": "수입 (Income)",
    "Other": "기타 (Other)",
}

HOUSEHOLD_L1_GROUP_MAP = {
    "현금": "Cash",
    "보통예금": "Bank",
    "정기예금": "Bank",
    "증권/투자자산": "Investment",
    "부동산": "Home",
    "전세보증금(임차)": "Home",
    "차량/운송수단": "Vehicle",
    "카드미지급금": "Credit Card",
    "주택담보대출": "Home",
    "전세보증금(임대)": "Home",
}


def _resolve_l1_account_name(
    account: Dict, account_lookup: Dict[int, Dict]
) -> str | None:
    current = account
    while current.get("parent_id"):
        parent = account_lookup.get(int(current["parent_id"]))
        if parent is None:
            break
        current = parent
    return current["name"] if current else None


def _household_group_for(account_type: str, l1_name: str | None) -> str:
    if account_type == "INCOME":
        return "Income"
    if account_type == "EXPENSE":
        return "Household Expenses"
    if l1_name and l1_name in HOUSEHOLD_L1_GROUP_MAP:
        return HOUSEHOLD_L1_GROUP_MAP[l1_name]
    return "Other"


def list_household_accounts(
    conn: sqlite3.Connection,
    active_only: bool = True,
    include_system: bool = False,
) -> list[dict]:
    # Fetch all accounts for lookup
    all_accounts_rows = conn.execute("SELECT * FROM accounts").fetchall()
    account_lookup = {row["id"]: dict(row) for row in all_accounts_rows}

    query = "SELECT * FROM accounts WHERE allow_posting = 1"
    params = []
    if active_only:
        query += " AND is_active = 1"
    if not include_system:
        query += " AND is_system = 0"

    query += " ORDER BY type, name"

    rows = conn.execute(query, params).fetchall()

    results = []
    for row in rows:
        account = dict(row)
        l1_name = _resolve_l1_account_name(account, account_lookup)
        group_key = _household_group_for(account["type"], l1_name)

        # Add derived fields
        account["l1_name"] = l1_name
        account["household_group"] = group_key
        account["household_group_label"] = HOUSEHOLD_GROUP_LABELS[group_key]
        results.append(account)
    return results


def list_household_account_groups(
    conn: sqlite3.Connection,
    active_only: bool = True,
    include_system: bool = False,
) -> list[dict]:
    accounts = list_household_accounts(
        conn, active_only=active_only, include_system=include_system
    )
    grouped: dict[str, list[dict]] = {key: [] for key in HOUSEHOLD_GROUP_LABELS}
    for account in accounts:
        grouped[account["household_group"]].append(account)
    return [
        {
            "group": group_key,
            "label": HOUSEHOLD_GROUP_LABELS[group_key],
            "accounts": grouped[group_key],
        }
        for group_key in HOUSEHOLD_GROUP_LABELS
    ]


def list_system_accounts_by_type(conn: sqlite3.Connection, type_: str) -> list[dict]:
    rows = conn.execute(
        "SELECT id, name, type, level, is_system, allow_posting FROM accounts WHERE type = ? AND is_system = 1 AND level = 1 ORDER BY name",
        (type_,),
    ).fetchall()

    return [dict(r) for r in rows]


def get_account(conn: sqlite3.Connection, account_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    return dict(row) if row else None


def create_user_account(
    conn: sqlite3.Connection,
    name: str,
    type_: str,
    parent_id: int,
    is_active: bool = True,
    currency: str | None = None,
) -> int:
    parent = get_account(conn, parent_id)

    if parent is None:
        raise ValueError("상위 계정을 선택해야 합니다.")
    if parent["type"] != type_:
        raise ValueError("상위 계정의 타입과 동일해야 합니다.")

    # Auto-manage: Parent becomes aggregate (allow_posting=0) if it was a leaf
    if parent["allow_posting"]:
        conn.execute(
            "UPDATE accounts SET allow_posting = 0 WHERE id = ?", (parent["id"],)
        )

    level = parent["level"] + 1

    # Calculate next 6-digit ID (parent_id * 100 + sequence)
    parent_id_int = parent["id"]
    range_min = parent_id_int * 100 + 1
    range_max = parent_id_int * 100 + 99

    # Max ID query
    row = conn.execute(
        "SELECT MAX(id) FROM accounts WHERE id >= ? AND id <= ?", (range_min, range_max)
    ).fetchone()
    max_id = row[0] if row else None

    new_id = max_id + 1 if max_id else range_min

    if new_id > range_max:
        raise ValueError(
            f"해당 분류({parent['name']})의 하위 계정 한도(99개)를 초과했습니다."
        )

    conn.execute(
        """INSERT INTO accounts (id, name, type, parent_id, is_active, is_system, level, allow_posting, currency)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            new_id,
            name.strip(),
            type_,
            parent_id_int,
            1 if is_active else 0,
            0,
            level,
            1,
            currency.upper() if currency else "KRW",
        ),
    )

    return new_id


def update_user_account(
    conn: sqlite3.Connection,
    account_id: int,
    name: str,
    is_active: bool,
    currency: str | None = None,
) -> None:
    account = get_account(conn, account_id)
    if account is None:
        raise ValueError("계정을 찾을 수 없습니다.")

    conn.execute(
        "UPDATE accounts SET name = ?, is_active = ?, currency = ? WHERE id = ?",
        (
            name.strip(),
            1 if is_active else 0,
            currency.upper() if currency else account["currency"],
            account_id,
        ),
    )


def delete_user_account(conn: sqlite3.Connection, account_id: int) -> None:
    account = get_account(conn, account_id)
    if account is None:
        raise ValueError("계정을 찾을 수 없습니다.")

    # Check children
    child_row = conn.execute(
        "SELECT COUNT(id) FROM accounts WHERE parent_id = ?", (account_id,)
    ).fetchone()
    if child_row[0] > 0:
        raise ValueError("하위 계정이 있어 삭제할 수 없습니다.")

    # Check journal lines
    line_row = conn.execute(
        "SELECT COUNT(id) FROM journal_lines WHERE account_id = ?", (account_id,)
    ).fetchone()
    if line_row[0] > 0:
        raise ValueError("전표에 사용된 계정은 삭제할 수 없습니다.")

    # Check linked assets
    asset_row = conn.execute(
        "SELECT name FROM assets WHERE linked_account_id = ?", (account_id,)
    ).fetchone()
    if asset_row:
        raise ValueError(
            f"이 계정은 자산 '{asset_row['name']}'에 연결되어 있어 삭제할 수 없습니다. 자산을 먼저 삭제하세요."
        )

    conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
