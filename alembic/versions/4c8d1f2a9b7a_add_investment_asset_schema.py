"""add_investment_asset_schema

Revision ID: 4c8d1f2a9b7a
Revises: 9f44f1c4c8b9
Create Date: 2026-01-21 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4c8d1f2a9b7a"
down_revision: str | Sequence[str] | None = "9f44f1c4c8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "investment_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("ticker", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("exchange", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "trading_currency", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("security_type", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("isin", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("broker", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id"),
    )
    op.create_index(
        op.f("ix_investment_profiles_asset_id"),
        "investment_profiles",
        ["asset_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_investment_profiles_exchange"),
        "investment_profiles",
        ["exchange"],
        unique=False,
    )
    op.create_index(
        op.f("ix_investment_profiles_isin"),
        "investment_profiles",
        ["isin"],
        unique=False,
    )
    op.create_index(
        op.f("ix_investment_profiles_ticker"),
        "investment_profiles",
        ["ticker"],
        unique=False,
    )

    op.create_table(
        "investment_lots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("lot_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("remaining_quantity", sa.Float(), nullable=False),
        sa.Column("unit_price_native", sa.Float(), nullable=False),
        sa.Column("fees_native", sa.Float(), nullable=False),
        sa.Column("currency", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("fx_rate", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_investment_lots_asset_id"),
        "investment_lots",
        ["asset_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_investment_lots_created_at"),
        "investment_lots",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_investment_lots_lot_date"),
        "investment_lots",
        ["lot_date"],
        unique=False,
    )

    op.create_table(
        "investment_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("price_per_unit_native", sa.Float(), nullable=True),
        sa.Column("gross_amount_native", sa.Float(), nullable=True),
        sa.Column("fees_native", sa.Float(), nullable=False),
        sa.Column("currency", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("fx_rate", sa.Float(), nullable=True),
        sa.Column("cash_account_id", sa.Integer(), nullable=True),
        sa.Column("income_account_id", sa.Integer(), nullable=True),
        sa.Column("fee_account_id", sa.Integer(), nullable=True),
        sa.Column("journal_entry_id", sa.Integer(), nullable=True),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
        ),
        sa.ForeignKeyConstraint(
            ["cash_account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["fee_account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["income_account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entries.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_investment_events_asset_id"),
        "investment_events",
        ["asset_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_investment_events_created_at"),
        "investment_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_investment_events_event_date"),
        "investment_events",
        ["event_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_investment_events_event_type"),
        "investment_events",
        ["event_type"],
        unique=False,
    )

    op.add_column(
        "asset_valuations",
        sa.Column(
            "method",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="market",
        ),
    )
    op.add_column("asset_valuations", sa.Column("fx_rate", sa.Float(), nullable=True))
    op.create_index(
        op.f("ix_asset_valuations_asset_id"),
        "asset_valuations",
        ["asset_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_asset_valuations_as_of_date"),
        "asset_valuations",
        ["as_of_date"],
        unique=False,
    )
    op.alter_column("asset_valuations", "method", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_asset_valuations_as_of_date"), table_name="asset_valuations")
    op.drop_index(op.f("ix_asset_valuations_asset_id"), table_name="asset_valuations")
    op.drop_column("asset_valuations", "fx_rate")
    op.drop_column("asset_valuations", "method")

    op.drop_index(
        op.f("ix_investment_events_event_type"), table_name="investment_events"
    )
    op.drop_index(
        op.f("ix_investment_events_event_date"), table_name="investment_events"
    )
    op.drop_index(
        op.f("ix_investment_events_created_at"), table_name="investment_events"
    )
    op.drop_index(op.f("ix_investment_events_asset_id"), table_name="investment_events")
    op.drop_table("investment_events")

    op.drop_index(op.f("ix_investment_lots_lot_date"), table_name="investment_lots")
    op.drop_index(op.f("ix_investment_lots_created_at"), table_name="investment_lots")
    op.drop_index(op.f("ix_investment_lots_asset_id"), table_name="investment_lots")
    op.drop_table("investment_lots")

    op.drop_index(
        op.f("ix_investment_profiles_ticker"), table_name="investment_profiles"
    )
    op.drop_index(op.f("ix_investment_profiles_isin"), table_name="investment_profiles")
    op.drop_index(
        op.f("ix_investment_profiles_exchange"), table_name="investment_profiles"
    )
    op.drop_index(
        op.f("ix_investment_profiles_asset_id"), table_name="investment_profiles"
    )
    op.drop_table("investment_profiles")
