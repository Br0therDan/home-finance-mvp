from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class JournalLine:
    account_id: int
    debit: float = 0.0
    credit: float = 0.0
    memo: str = ""


@dataclass
class JournalEntryInput:
    entry_date: date
    description: str
    source: str
    lines: list[JournalLine]
