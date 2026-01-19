from __future__ import annotations

import sqlite3


def list_system_accounts_by_type(conn: sqlite3.Connection, type_: str):
    rows = conn.execute(
        """
        SELECT id, name, type, level, is_system, allow_posting
        FROM accounts
        WHERE type = ? AND is_system = 1 AND level = 1
        ORDER BY name
        """,
        (type_,),
    ).fetchall()
    return [
        {
            "id": int(r["id"]),
            "name": r["name"],
            "type": r["type"],
            "level": int(r["level"]),
            "is_system": int(r["is_system"]),
            "allow_posting": int(r["allow_posting"]),
        }
        for r in rows
    ]


def create_user_account(
    conn: sqlite3.Connection,
    name: str,
    type_: str,
    parent_id: int,
    is_active: bool = True,
    currency: str | None = None,
) -> int:
    parent = conn.execute(
        """
        SELECT id, name, type, level, is_system, allow_posting
        FROM accounts
        WHERE id = ?
        """,
        (parent_id,),
    ).fetchone()

    if parent is None:
        raise ValueError("상위 계정을 선택해야 합니다.")
    if parent["type"] != type_:
        raise ValueError("상위 계정의 타입과 동일해야 합니다.")
    if int(parent["is_system"]) != 1 or int(parent["level"]) != 1:
        raise ValueError("상위 계정은 시스템(Level 1) 계정이어야 합니다.")
    if int(parent["allow_posting"]) != 0:
        raise ValueError("상위(집계) 계정만 선택할 수 있습니다.")

    level = int(parent["level"]) + 1

    with conn:
        cur = conn.execute(
            """
            INSERT INTO accounts(name, type, parent_id, is_active, is_system, level, allow_posting, currency)
            VALUES (?, ?, ?, ?, 0, ?, 1, ?)
            """,
            (
                name.strip(),
                type_,
                int(parent_id),
                1 if is_active else 0,
                level,
                currency.upper() if currency else "KRW",
            ),
        )
        lastrowid = cur.lastrowid
        if lastrowid is None:
            raise RuntimeError("Failed to create account, no lastrowid returned.")
        return int(lastrowid)


def update_user_account(
    conn: sqlite3.Connection,
    account_id: int,
    name: str,
    is_active: bool,
) -> None:
    row = conn.execute(
        """
        SELECT id, is_system, allow_posting
        FROM accounts
        WHERE id = ?
        """,
        (account_id,),
    ).fetchone()

    if row is None:
        raise ValueError("계정을 찾을 수 없습니다.")
    if int(row["is_system"]) == 1:
        raise ValueError("시스템 계정은 수정할 수 없습니다.")
    if int(row["allow_posting"]) != 1:
        raise ValueError("집계 계정은 수정할 수 없습니다.")

    with conn:
        conn.execute(
            """
            UPDATE accounts
            SET name = ?, is_active = ?
            WHERE id = ?
            """,
            (name.strip(), 1 if is_active else 0, int(account_id)),
        )


def delete_user_account(conn: sqlite3.Connection, account_id: int) -> None:
    row = conn.execute(
        """
        SELECT id, is_system, allow_posting
        FROM accounts
        WHERE id = ?
        """,
        (account_id,),
    ).fetchone()

    if row is None:
        raise ValueError("계정을 찾을 수 없습니다.")
    if int(row["is_system"]) == 1:
        raise ValueError("시스템 계정은 삭제할 수 없습니다.")
    if int(row["allow_posting"]) != 1:
        raise ValueError("집계 계정은 삭제할 수 없습니다.")

    child = conn.execute(
        "SELECT COUNT(1) AS cnt FROM accounts WHERE parent_id = ?",
        (account_id,),
    ).fetchone()
    if int(child["cnt"] or 0) > 0:
        raise ValueError("하위 계정이 있어 삭제할 수 없습니다.")

    used = conn.execute(
        "SELECT COUNT(1) AS cnt FROM journal_lines WHERE account_id = ?",
        (account_id,),
    ).fetchone()
    if int(used["cnt"] or 0) > 0:
        raise ValueError("전표에 사용된 계정은 삭제할 수 없습니다.")

    with conn:
        conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
