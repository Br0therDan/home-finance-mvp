from __future__ import annotations

from datetime import date
from sqlmodel import Session, select, func
from core.models import JournalEntry, JournalLine, Account, JournalEntryInput


def _validate_entry(lines: list[JournalLine]) -> None:
    if not lines or len(lines) < 2:
        raise ValueError("A journal entry must have at least 2 lines.")

    total_debit = sum(max(0.0, float(line.debit)) for line in lines)
    total_credit = sum(max(0.0, float(line.credit)) for line in lines)

    if round(total_debit, 2) != round(total_credit, 2):
        raise ValueError(
            f"Unbalanced entry: debit={total_debit:.2f}, credit={total_credit:.2f}"
        )

    for line in lines:
        if line.debit < 0 or line.credit < 0:
            raise ValueError("Debit/Credit cannot be negative.")
        if line.debit > 0 and line.credit > 0:
            raise ValueError("A single line cannot have both debit and credit.")
        if line.debit == 0 and line.credit == 0:
            raise ValueError("A line must have a debit or credit amount.")


def _validate_posting_accounts(session: Session, lines: list[JournalLine]) -> None:
    account_ids = list({int(line.account_id) for line in lines})
    if not account_ids:
        raise ValueError("At least one journal line is required.")

    statement = select(Account.id, Account.allow_posting).where(
        Account.id.in_(account_ids)
    )
    rows = session.exec(statement).all()
    allow_map = {r[0]: r[1] for r in rows}

    for account_id in account_ids:
        if account_id not in allow_map:
            raise ValueError("Account not found.")
        if not allow_map[account_id]:
            raise ValueError(
                "상위(집계) 계정에는 직접 분개할 수 없습니다. 하위 계정을 선택하세요."
            )


def create_journal_entry(session: Session, entry_in: JournalEntryInput) -> int:
    _validate_entry(entry_in.lines)
    _validate_posting_accounts(session, entry_in.lines)

    # Create Entry
    db_entry = JournalEntry(
        entry_date=entry_in.entry_date,
        description=entry_in.description,
        source=entry_in.source,
    )
    session.add(db_entry)
    session.flush()  # Get ID

    for line in entry_in.lines:
        db_line = JournalLine(
            entry_id=db_entry.id,
            account_id=line.account_id,
            debit=float(line.debit),
            credit=float(line.credit),
            memo=line.memo,
            native_amount=line.native_amount,
            native_currency=line.native_currency,
            fx_rate=line.fx_rate,
        )
        session.add(db_line)

    session.commit()
    session.refresh(db_entry)
    return db_entry.id


def list_accounts(session: Session, active_only: bool = True) -> list[dict]:
    statement = select(Account)
    if active_only:
        statement = statement.where(Account.is_active)
    statement = statement.order_by(Account.type, Account.name)

    results = session.exec(statement).all()
    # Return dicts
    return [r.model_dump() for r in results]


def list_posting_accounts(session: Session, active_only: bool = True) -> list[dict]:
    statement = select(Account).where(Account.allow_posting)
    if active_only:
        statement = statement.where(Account.is_active)
    statement = statement.order_by(Account.type, Account.name)

    results = session.exec(statement).all()
    return [r.model_dump() for r in results]


def get_account(session: Session, account_id: int):
    acc = session.get(Account, account_id)
    return acc.model_dump() if acc else None


def get_account_by_name(session: Session, name: str, type_: str | None = None):
    statement = select(Account).where(Account.name == name)
    if type_:
        statement = statement.where(Account.type == type_)

    acc = session.exec(statement).first()
    return acc.model_dump() if acc else None


def has_opening_balance_entry(session: Session) -> bool:
    statement = select(func.count(JournalEntry.id)).where(
        JournalEntry.source == "opening_balance"
    )
    cnt = session.exec(statement).one()
    return cnt > 0


def delete_opening_balance_entry(session: Session) -> None:
    statement = select(JournalEntry).where(JournalEntry.source == "opening_balance")
    entries = session.exec(statement).all()
    for e in entries:
        session.delete(e)
    session.commit()


def create_opening_balance_entry(
    session: Session,
    entry_date: date,
    description: str,
    asset_lines: list[JournalLine],
    liability_lines: list[JournalLine],
) -> int:
    if has_opening_balance_entry(session):
        raise ValueError("OPENING_BALANCE entry already exists.")

    lines: list[JournalLine] = []

    for line in asset_lines:
        if line.debit < 0 or line.credit < 0:
            raise ValueError("Negative amount")
        if line.debit > 0:
            lines.append(
                JournalLine(
                    account_id=line.account_id,
                    debit=line.debit,
                    credit=0.0,
                    memo=line.memo,
                )
            )

    for line in liability_lines:
        if line.debit < 0 or line.credit < 0:
            raise ValueError("Negative amount")
        if line.credit > 0:
            lines.append(
                JournalLine(
                    account_id=line.account_id,
                    debit=0.0,
                    credit=line.credit,
                    memo=line.memo,
                )
            )

    if not lines:
        raise ValueError("At least one opening balance line is required.")

    total_debit = sum(line.debit for line in lines)
    total_credit = sum(line.credit for line in lines)

    equity = get_account_by_name(session, "기초순자산(Opening Equity)", "EQUITY")
    if equity is None:
        equity = get_account_by_name(session, "기초순자산", "EQUITY")
    if equity is None:
        equity = get_account_by_name(session, "기초자본(Opening Balance)", "EQUITY")
    if equity is None:
        raise ValueError("Opening equity account not found.")

    gap = total_debit - total_credit
    if abs(gap) > 1e-9:
        if gap > 0:
            lines.append(
                JournalLine(
                    account_id=equity["id"], debit=0.0, credit=gap, memo=description
                )
            )
        else:
            lines.append(
                JournalLine(
                    account_id=equity["id"], debit=-gap, credit=0.0, memo=description
                )
            )

    entry_input = JournalEntryInput(
        entry_date=entry_date,
        description=description,
        source="opening_balance",
        lines=lines,
    )
    return create_journal_entry(session, entry_input)


def account_balances(session: Session, as_of: date | None = None) -> dict[int, float]:
    statement = select(
        JournalLine.account_id,
        func.sum(JournalLine.debit - JournalLine.credit).label("balance"),
    ).join(JournalEntry)
    if as_of:
        statement = statement.where(JournalEntry.entry_date <= as_of)
    statement = statement.group_by(JournalLine.account_id)

    rows = session.exec(statement).all()
    return {r[0]: (r[1] or 0.0) for r in rows}


def account_balances_multi(
    session: Session, as_of: date | None = None
) -> dict[int, dict[str, float]]:
    where_clause = ""
    params = {}
    if as_of:
        where_clause = "WHERE je.entry_date <= :as_of"
        params = {"as_of": as_of}

    sql = f"""
        SELECT 
            jl.account_id,
            SUM(jl.debit - jl.credit) AS base_balance,
            SUM(
                CASE 
                    WHEN jl.native_amount IS NOT NULL THEN (
                        CASE WHEN jl.debit > 0 THEN jl.native_amount ELSE -jl.native_amount END
                    )
                    ELSE (jl.debit - jl.credit)
                END
            ) AS native_balance
        FROM journal_lines jl
        JOIN journal_entries je ON je.id = jl.entry_id
        {where_clause}
        GROUP BY jl.account_id
    """

    from sqlalchemy import text

    result = session.exec(text(sql), params=params).fetchall()

    return {
        r[0]: {"base": float(r[1] or 0.0), "native": float(r[2] or 0.0)} for r in result
    }


def trial_balance(session: Session, as_of: date | None = None):
    bal = account_balances(session, as_of=as_of)
    accounts = list_accounts(session, active_only=False)  # list of dicts

    results = []
    for a in accounts:
        b = float(bal.get(int(a["id"]), 0.0))
        results.append(
            {
                "account_id": int(a["id"]),
                "account": a["name"],
                "type": a["type"],
                "debit": b if b > 0 else 0.0,
                "credit": -b if b < 0 else 0.0,
                "raw_balance": b,
            }
        )
    return results


def balance_sheet(
    session: Session,
    as_of: date | None = None,
    display_currency: str | None = None,
):
    from core.services.fx_service import get_latest_rate
    from core.services.settings_service import get_base_currency

    base_cur = get_base_currency(session)
    quote_cur = display_currency or base_cur

    bal_multi = account_balances_multi(session, as_of=as_of)
    accounts = list_accounts(session, active_only=True)

    acc_currencies = {
        int(a["id"]): a.get("currency", base_cur) or base_cur for a in accounts
    }

    assets = []
    liabilities = []
    equity = []
    missing_rates: set[tuple[str, str]] = set()

    for a in accounts:
        aid = int(a["id"])
        t = a["type"]
        b_data = bal_multi.get(aid, {"base": 0.0, "native": 0.0})
        base_val = b_data["base"]
        native_val = b_data["native"]
        native_cur = acc_currencies.get(aid, base_cur)

        book_val = base_val

        if native_cur == base_cur:
            current_val_base = base_val
        else:
            current_rate = get_latest_rate(session, base_cur, native_cur)
            if current_rate is None:
                missing_rates.add((base_cur, native_cur))
                current_val_base = base_val
            else:
                current_val_base = native_val * current_rate

        if quote_cur == base_cur:
            disp_val = current_val_base
        else:
            krw_quote_rate = get_latest_rate(session, base_cur, quote_cur)
            if krw_quote_rate is None or krw_quote_rate == 0:
                missing_rates.add((base_cur, quote_cur))
                disp_val = current_val_base
            else:
                disp_val = current_val_base / krw_quote_rate

        item = {
            "id": aid,
            "name": a["name"],
            "currency": native_cur,
            "native_balance": native_val,
            "book_value_base": book_val,
            "current_value_base": current_val_base,
            "display_value": disp_val,
        }

        if t == "ASSET":
            if abs(base_val) > 1e-9 or abs(native_val) > 1e-9:
                assets.append(item)
        elif t == "LIABILITY":
            item.update(
                {k: -v for k, v in item.items() if isinstance(v, float)}
            )  # Flip signs
            if abs(base_val) > 1e-9 or abs(native_val) > 1e-9:
                liabilities.append(item)
        elif t == "EQUITY":
            item.update({k: -v for k, v in item.items() if isinstance(v, float)})
            if abs(base_val) > 1e-9 or abs(native_val) > 1e-9:
                equity.append(item)

    total_assets_base = sum(i["current_value_base"] for i in assets)
    total_liab_base = sum(i["current_value_base"] for i in liabilities)
    total_eq_base = sum(i["book_value_base"] for i in equity)

    total_assets_disp = sum(i["display_value"] for i in assets)
    total_liab_disp = sum(i["display_value"] for i in liabilities)
    total_eq_disp = sum(i["display_value"] for i in equity)

    return {
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "total_assets_base": total_assets_base,
        "total_liabilities_base": total_liab_base,
        "total_equity_base": total_eq_base,
        "total_assets_disp": total_assets_disp,
        "total_liabilities_disp": total_liab_disp,
        "total_equity_disp": total_eq_disp,
        "net_worth_base": total_assets_base - total_liab_base,
        "net_worth_disp": total_assets_disp - total_liab_disp,
        "display_currency": quote_cur,
        "base_currency": base_cur,
        "missing_rates": sorted(missing_rates),
    }


def income_statement(session: Session, start: date, end: date):
    from sqlalchemy import text

    sql = """
        SELECT a.type AS type, a.name AS account,
               SUM(jl.debit - jl.credit) AS raw_balance
        FROM journal_lines jl
        JOIN journal_entries je ON je.id = jl.entry_id
        JOIN accounts a ON a.id = jl.account_id
        WHERE je.entry_date >= :start AND je.entry_date <= :end
          AND a.type IN ('INCOME', 'EXPENSE')
        GROUP BY a.type, a.name
        ORDER BY a.type, a.name
    """
    rows = session.exec(text(sql), params={"start": start, "end": end}).fetchall()

    income = []
    expense = []
    for r in rows:
        t = r[0]
        name = r[1]
        b = float(r[2] or 0.0)
        if t == "INCOME":
            income.append((name, -b))
        else:
            expense.append((name, b))

    total_income = sum(v for _, v in income)
    total_expense = sum(v for _, v in expense)
    return {
        "income": income,
        "expense": expense,
        "total_income": total_income,
        "total_expense": total_expense,
        "net_profit": total_income - total_expense,
    }


def monthly_cashflow(session: Session, year: int):
    """Return monthly cashflow for cash-equivalent accounts."""
    from sqlalchemy import text

    cash_name_patterns = [
        "%현금%",
        "%보통예금%",
        "%정기예금%",
        "%cash%",
        "%checking%",
        "%savings%",
    ]
    name_clauses = " OR ".join(
        f"LOWER(a.name) LIKE LOWER(:name_{idx})"
        for idx in range(len(cash_name_patterns))
    )
    params = {f"name_{idx}": pattern for idx, pattern in enumerate(cash_name_patterns)}
    params.update(
        {
            "start": f"{year}-01-01",
            "end": f"{year}-12-31",
        }
    )

    base_sql = f"""
        WITH cash_accounts AS (
            SELECT a.id
            FROM accounts a
            WHERE a.is_active = 1
              AND ({name_clauses})
        )
    """

    opening_sql = (
        base_sql
        + """
        SELECT COALESCE(SUM(jl.debit - jl.credit), 0) AS opening_balance
        FROM journal_lines jl
        JOIN journal_entries je ON je.id = jl.entry_id
        WHERE jl.account_id IN (SELECT id FROM cash_accounts)
          AND je.entry_date < :start
        """
    )

    monthly_sql = (
        base_sql
        + """
        SELECT strftime('%m', je.entry_date) AS month,
               SUM(jl.debit - jl.credit) AS net_change
        FROM journal_lines jl
        JOIN journal_entries je ON je.id = jl.entry_id
        WHERE jl.account_id IN (SELECT id FROM cash_accounts)
          AND je.entry_date >= :start
          AND je.entry_date <= :end
        GROUP BY strftime('%m', je.entry_date)
        ORDER BY strftime('%m', je.entry_date)
        """
    )

    opening_balance = float(
        session.exec(text(opening_sql), params=params).one()[0] or 0.0
    )
    rows = session.exec(text(monthly_sql), params=params).fetchall()
    monthly_map = {int(r[0]): float(r[1] or 0.0) for r in rows}

    results = []
    running_balance = opening_balance
    for month in range(1, 13):
        net_change = monthly_map.get(month, 0.0)
        running_balance += net_change
        results.append(
            {
                "month": month,
                "net_change": net_change,
                "ending_balance": running_balance,
            }
        )
    return results
