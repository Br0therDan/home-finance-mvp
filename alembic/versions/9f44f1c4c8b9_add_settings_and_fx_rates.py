"""add_settings_and_fx_rates

Revision ID: 9f44f1c4c8b9
Revises: 7639e42c4c35
Create Date: 2026-01-20 03:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "9f44f1c4c8b9"
down_revision: Union[str, Sequence[str], None] = "7639e42c4c35"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("base_currency", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "fx_rates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("base_currency", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("quote_currency", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("rate", sa.Float(), nullable=False),
        sa.Column("as_of", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_fx_rates_base_currency"),
        "fx_rates",
        ["base_currency"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fx_rates_quote_currency"),
        "fx_rates",
        ["quote_currency"],
        unique=False,
    )
    op.create_index(op.f("ix_fx_rates_as_of"), "fx_rates", ["as_of"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_fx_rates_as_of"), table_name="fx_rates")
    op.drop_index(op.f("ix_fx_rates_quote_currency"), table_name="fx_rates")
    op.drop_index(op.f("ix_fx_rates_base_currency"), table_name="fx_rates")
    op.drop_table("fx_rates")
    op.drop_table("app_settings")
