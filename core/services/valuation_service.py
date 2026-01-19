from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, desc, select

from core.models import AssetValuation


class ValuationService:
    def __init__(self, session: Session):
        self._session = session

    def upsert_asset_valuation(
        self,
        asset_id: int,
        as_of_date: str,  # Keeping str signature for compatibility, but converting
        value_native: float,
        currency: str,
        note: str | None = None,
    ) -> int:
        # Check if exists
        statement = select(AssetValuation).where(
            AssetValuation.asset_id == asset_id, AssetValuation.as_of_date == as_of_date
        )
        existing = self._session.exec(statement).first()

        if existing:
            existing.value_native = float(value_native)
            existing.currency = currency.upper()
            existing.note = note
            existing.updated_at = datetime.now()
            self._session.add(existing)
            self._session.commit()
            self._session.refresh(existing)
            return existing.id
        else:
            new_val = AssetValuation(
                asset_id=asset_id,
                as_of_date=as_of_date,
                value_native=float(value_native),
                currency=currency.upper(),
                note=note,
                updated_at=datetime.now(),
            )
            self._session.add(new_val)
            self._session.commit()
            self._session.refresh(new_val)
            return new_val.id

    def get_valuation_history(self, asset_id: int) -> list[dict]:
        statement = (
            select(AssetValuation)
            .where(AssetValuation.asset_id == asset_id)
            .order_by(desc(AssetValuation.as_of_date), desc(AssetValuation.updated_at))
        )
        results = self._session.exec(statement).all()
        return [r.model_dump() for r in results]

    def list_latest_valuations(self) -> list[dict]:
        # Complex group by. Using raw SQL or window functions might be easier.
        # Logic: Select * where (asset_id, as_of_date) is max for that asset.
        from sqlalchemy import text

        sql = """
            SELECT v.*, a.name as asset_name
            FROM asset_valuations v
            JOIN assets a ON a.id = v.asset_id
            WHERE v.id IN (
                SELECT id FROM asset_valuations
                GROUP BY asset_id
                HAVING MAX(as_of_date)
            )
        """
        results = self._session.exec(text(sql)).fetchall()
        # ResultProxy to dict
        return [
            {
                "id": r.id,
                "asset_id": r.asset_id,
                "as_of_date": r.as_of_date,
                "value_native": r.value_native,
                "currency": r.currency,
                "asset_name": r.asset_name,
            }
            for r in results
        ]

    def get_valuations_for_dashboard(self) -> dict[int, dict]:
        latest = self.list_latest_valuations()
        return {r["asset_id"]: r for r in latest}
