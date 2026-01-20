from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, select

from core.models import FxRate


def get_latest_rate(
    session: Session, base_cur: str, target_cur: str
) -> float | None:
    if base_cur == target_cur:
        return 1.0

    statement = (
        select(FxRate)
        .where(
            FxRate.base_currency == base_cur,
            FxRate.quote_currency == target_cur,
        )
        .order_by(FxRate.as_of.desc(), FxRate.id.desc())
    )
    rate_row = session.exec(statement).first()
    return rate_row.rate if rate_row else None


def save_rate(
    session: Session,
    base: str,
    quote: str,
    rate: float,
    as_of: datetime | None = None,
) -> FxRate:
    timestamp = as_of or datetime.now()

    if as_of is None:
        statement = (
            select(FxRate)
            .where(FxRate.base_currency == base, FxRate.quote_currency == quote)
            .order_by(FxRate.as_of.desc(), FxRate.id.desc())
        )
    else:
        statement = select(FxRate).where(
            FxRate.base_currency == base,
            FxRate.quote_currency == quote,
            FxRate.as_of == timestamp,
        )

    rate_row = session.exec(statement).first()
    if rate_row:
        rate_row.rate = rate
        rate_row.as_of = timestamp
    else:
        rate_row = FxRate(
            base_currency=base,
            quote_currency=quote,
            rate=rate,
            as_of=timestamp,
        )
        session.add(rate_row)

    session.commit()
    session.refresh(rate_row)
    return rate_row
