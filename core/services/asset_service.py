from __future__ import annotations

from datetime import date

from sqlalchemy import func
from sqlmodel import Session, select

from core.models import (
    Account,
    Asset,
    AssetValuation,
    InvestmentEvent,
    InvestmentLot,
    InvestmentProfile,
)

INVESTMENT_EVENT_LEDGER_MAPPING: dict[str, list[str]] = {
    "BUY": [
        "Dr Investment Asset (linked_account_id) for trade notional",
        "Dr Investment Fees (fee_account_id) for fees/commissions",
        "Cr Cash/Settlement Account (cash_account_id)",
    ],
    "SELL": [
        "Dr Cash/Settlement Account (cash_account_id) for proceeds",
        "Cr Investment Asset (linked_account_id) for cost basis relieved",
        "Cr/Dr Realized Gain/Loss (income/expense account) for difference",
        "Dr Investment Fees (fee_account_id) for fees/commissions",
    ],
    "DIVIDEND": [
        "Dr Cash/Settlement Account (cash_account_id)",
        "Cr Dividend Income (income_account_id)",
    ],
}


def create_asset(
    session: Session,
    name: str,
    asset_class: str,
    linked_account_id: int,
    acquisition_date: date,
    acquisition_cost: float,
    note: str = "",
) -> int:
    asset = Asset(
        name=name,
        asset_class=asset_class,
        linked_account_id=linked_account_id,
        acquisition_date=acquisition_date,
        acquisition_cost=float(acquisition_cost),
        note=note,
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset.id


def create_investment_profile(
    session: Session,
    asset_id: int,
    ticker: str,
    trading_currency: str,
    exchange: str | None = None,
    security_type: str | None = None,
    isin: str | None = None,
    broker: str | None = None,
) -> int:
    asset = session.get(Asset, asset_id)
    if not asset:
        raise ValueError("Asset not found")

    profile = InvestmentProfile(
        asset_id=asset_id,
        ticker=ticker.strip(),
        exchange=exchange.strip() if exchange else None,
        trading_currency=trading_currency.strip(),
        security_type=security_type.strip() if security_type else None,
        isin=isin.strip() if isin else None,
        broker=broker.strip() if broker else None,
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile.id


def add_investment_lot(
    session: Session,
    asset_id: int,
    lot_date: date,
    quantity: float,
    unit_price_native: float,
    currency: str,
    fees_native: float = 0.0,
    fx_rate: float | None = None,
) -> int:
    asset = session.get(Asset, asset_id)
    if not asset:
        raise ValueError("Asset not found")

    lot = InvestmentLot(
        asset_id=asset_id,
        lot_date=lot_date,
        quantity=float(quantity),
        remaining_quantity=float(quantity),
        unit_price_native=float(unit_price_native),
        fees_native=float(fees_native),
        currency=currency.strip(),
        fx_rate=fx_rate,
    )
    session.add(lot)
    session.commit()
    session.refresh(lot)
    return lot.id


def record_investment_event(
    session: Session,
    asset_id: int,
    event_type: str,
    event_date: date,
    currency: str,
    quantity: float | None = None,
    price_per_unit_native: float | None = None,
    gross_amount_native: float | None = None,
    fees_native: float = 0.0,
    fx_rate: float | None = None,
    cash_account_id: int | None = None,
    income_account_id: int | None = None,
    fee_account_id: int | None = None,
    journal_entry_id: int | None = None,
    note: str | None = None,
) -> int:
    asset = session.get(Asset, asset_id)
    if not asset:
        raise ValueError("Asset not found")

    event = InvestmentEvent(
        asset_id=asset_id,
        event_type=event_type.strip().upper(),
        event_date=event_date,
        quantity=float(quantity) if quantity is not None else None,
        price_per_unit_native=float(price_per_unit_native)
        if price_per_unit_native is not None
        else None,
        gross_amount_native=float(gross_amount_native)
        if gross_amount_native is not None
        else None,
        fees_native=float(fees_native),
        currency=currency.strip(),
        fx_rate=fx_rate,
        cash_account_id=cash_account_id,
        income_account_id=income_account_id,
        fee_account_id=fee_account_id,
        journal_entry_id=journal_entry_id,
        note=note,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event.id


def get_investment_performance(session: Session, asset_id: int) -> dict | None:
    latest_valuation = session.exec(
        select(AssetValuation)
        .where(AssetValuation.asset_id == asset_id)
        .order_by(AssetValuation.as_of_date.desc(), AssetValuation.id.desc())
    ).first()
    if not latest_valuation:
        return None

    cost_basis_expr = (
        InvestmentLot.quantity * InvestmentLot.unit_price_native
        + InvestmentLot.fees_native
    )
    cost_basis_native = session.exec(
        select(func.coalesce(func.sum(cost_basis_expr), 0.0)).where(
            InvestmentLot.asset_id == asset_id
        )
    ).one()
    unrealized_pl_native = latest_valuation.value_native - float(cost_basis_native)

    return {
        "asset_id": asset_id,
        "as_of_date": latest_valuation.as_of_date,
        "currency": latest_valuation.currency,
        "market_value_native": latest_valuation.value_native,
        "cost_basis_native": float(cost_basis_native),
        "unrealized_pl_native": unrealized_pl_native,
        "valuation_method": latest_valuation.method,
        "valuation_fx_rate": latest_valuation.fx_rate,
    }


def list_assets(session: Session) -> list[dict]:
    # Select Asset and Account name
    statement = (
        select(Asset, Account.name)
        .join(Account)
        .where(Asset.disposal_date.is_(None))
        .order_by(Asset.acquisition_date.desc(), Asset.id.desc())
    )
    results = session.exec(statement).all()

    # Return dicts to match UI expectations
    output = []
    for asset, acc_name in results:
        data = asset.model_dump()
        data["linked_account"] = acc_name
        output.append(data)
    return output


def update_asset(
    session: Session,
    asset_id: int,
    name: str,
    asset_class: str,
    linked_account_id: int,
    acquisition_date: date,
    acquisition_cost: float,
    note: str,
) -> None:
    asset = session.get(Asset, asset_id)
    if not asset:
        raise ValueError("Asset not found")

    asset.name = name.strip()
    asset.asset_class = asset_class
    asset.linked_account_id = linked_account_id
    asset.acquisition_date = acquisition_date
    asset.acquisition_cost = float(acquisition_cost)
    asset.note = note

    session.add(asset)
    session.commit()


def delete_asset(session: Session, asset_id: int) -> None:
    asset = session.get(Asset, asset_id)
    if asset:
        session.delete(asset)
        session.commit()
