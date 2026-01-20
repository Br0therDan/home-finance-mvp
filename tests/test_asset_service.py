from datetime import date
from core.services.asset_service import (
    add_investment_lot,
    create_asset,
    create_investment_profile,
    delete_asset,
    get_investment_performance,
    list_assets,
    record_investment_event,
    update_asset,
)
from core.services.valuation_service import upsert_asset_valuation


def test_asset_crud_and_investment_performance(conn) -> None:
    conn.execute(
        """INSERT INTO accounts (id, name, type, parent_id, is_active, is_system, level, allow_posting, currency)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (1300, "투자자산", "ASSET", None, 1, 0, 2, 1, "KRW"),
    )
    conn.commit()

    asset_id = create_asset(
        conn=conn,
        name="테스트 자산",
        asset_class="STOCK",
        linked_account_id=1300,
        acquisition_date=date(2024, 1, 1),
        acquisition_cost=1000.0,
        note="초기 취득",
    )

    profile_id = create_investment_profile(
        conn=conn,
        asset_id=asset_id,
        ticker="TEST",
        trading_currency="USD",
        exchange="NYSE",
        security_type="STOCK",
        isin="TESTISIN",
        broker="BROKER",
    )
    assert profile_id > 0

    lot_id = add_investment_lot(
        conn=conn,
        asset_id=asset_id,
        lot_date=date(2024, 1, 2),
        quantity=10,
        unit_price_native=100.0,
        currency="USD",
        fees_native=5.0,
        fx_rate=1000.0,
    )
    assert lot_id > 0

    event_id = record_investment_event(
        conn=conn,
        asset_id=asset_id,
        event_type="BUY",
        event_date=date(2024, 1, 2),
        currency="USD",
        quantity=10,
        price_per_unit_native=100.0,
        gross_amount_native=1000.0,
        fees_native=5.0,
        note="매수",
    )
    assert event_id > 0

    upsert_asset_valuation(
        conn=conn,
        asset_id=asset_id,
        as_of_date=date(2024, 1, 31),
        value_native=1200.0,
        currency="USD",
    )

    performance = get_investment_performance(conn, asset_id=asset_id)
    assert performance is not None
    assert performance["market_value_native"] == 1200.0
    assert performance["cost_basis_native"] == 1005.0
    assert performance["unrealized_pl_native"] == 195.0

    assets = list_assets(conn)
    assert assets[0]["linked_account"] == "투자자산"

    update_asset(
        conn=conn,
        asset_id=asset_id,
        name="테스트 자산 (수정)",
        asset_class="STOCK",
        linked_account_id=1300,
        acquisition_date=date(2024, 1, 1),
        acquisition_cost=1000.0,
        asset_type="STOCK",
        depreciation_method="NONE",
        useful_life_years=None,
        salvage_value=0.0,
        note="수정",
    )

    delete_asset(conn, asset_id=asset_id)
    assert list_assets(conn) == []
