from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class JournalLine:
    account_id: int
    debit: float = 0.0
    credit: float = 0.0
    memo: str = ""
    # Multi-currency fields
    native_amount: float | None = None
    native_currency: str | None = None
    fx_rate: float | None = None


@dataclass
class JournalEntryInput:
    entry_date: date
    description: str
    source: str
    lines: list[JournalLine]
