"""add_subscriptions_table

Revision ID: 1b4b7e8a9b10
Revises: 4c8d1f2a9b7a
Create Date: 2026-02-15 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1b4b7e8a9b10"
down_revision: str | Sequence[str] | None = "4c8d1f2a9b7a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("cadence", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("interval", sa.Integer(), nullable=False),
        sa.Column("next_due_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("debit_account_id", sa.Integer(), nullable=False),
        sa.Column("credit_account_id", sa.Integer(), nullable=False),
        sa.Column("memo", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("auto_create_journal", sa.Boolean(), nullable=False),
        sa.Column("last_run_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["credit_account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["debit_account_id"],
            ["accounts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_subscriptions_cadence"), "subscriptions", ["cadence"], unique=False
    )
    op.create_index(
        op.f("ix_subscriptions_next_due_date"),
        "subscriptions",
        ["next_due_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_subscriptions_next_due_date"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_cadence"), table_name="subscriptions")
    op.drop_table("subscriptions")
