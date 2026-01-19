from __future__ import annotations

from datetime import date
from sqlmodel import Session, select
from core.models import Asset, Account


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
