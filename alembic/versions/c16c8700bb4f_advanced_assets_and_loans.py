"""advanced_assets_and_loans

Revision ID: c16c8700bb4f
Revises: 1b4b7e8a9b10
Create Date: 2026-01-20 14:00:09.450985

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c16c8700bb4f"
down_revision: Union[str, Sequence[str], None] = "1b4b7e8a9b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update app_settings
    op.add_column(
        "app_settings", sa.Column("alpha_vantage_api_key", sa.String(), nullable=True)
    )

    # 2. Update assets
    op.add_column(
        "assets",
        sa.Column("asset_type", sa.String(), nullable=False, server_default="OTHER"),
    )
    op.add_column(
        "assets",
        sa.Column(
            "depreciation_method", sa.String(), nullable=False, server_default="NONE"
        ),
    )
    op.add_column("assets", sa.Column("useful_life_years", sa.Integer(), nullable=True))
    op.add_column(
        "assets",
        sa.Column("salvage_value", sa.Float(), nullable=False, server_default="0.0"),
    )

    # 3. Create loans
    op.create_table(
        "loans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("liability_account_id", sa.Integer(), nullable=False),
        sa.Column("principal_amount", sa.Float(), nullable=False),
        sa.Column("interest_rate", sa.Float(), nullable=False),
        sa.Column("term_months", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column(
            "repayment_method",
            sa.String(),
            nullable=False,
            server_default="AMORTIZATION",
        ),
        sa.Column("payment_day", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "grace_period_months", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("note", sa.String(), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["liability_account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 4. Create loan_schedules
    op.create_table(
        "loan_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("loan_id", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("installment_number", sa.Integer(), nullable=False),
        sa.Column("principal_payment", sa.Float(), nullable=False),
        sa.Column("interest_payment", sa.Float(), nullable=False),
        sa.Column("total_payment", sa.Float(), nullable=False),
        sa.Column("remaining_balance", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("journal_entry_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"]),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["journal_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_loan_schedules_due_date"), "loan_schedules", ["due_date"], unique=False
    )
    op.create_index(
        op.f("ix_loan_schedules_loan_id"), "loan_schedules", ["loan_id"], unique=False
    )

    # 5. Create evidences
    op.create_table(
        "evidences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("loan_id", sa.Integer(), nullable=True),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("note", sa.String(), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evidences_asset_id"), "evidences", ["asset_id"], unique=False
    )
    op.create_index(
        op.f("ix_evidences_loan_id"), "evidences", ["loan_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_evidences_loan_id"), table_name="evidences")
    op.drop_index(op.f("ix_evidences_asset_id"), table_name="evidences")
    op.drop_table("evidences")
    op.drop_index(op.f("ix_loan_schedules_loan_id"), table_name="loan_schedules")
    op.drop_index(op.f("ix_loan_schedules_due_date"), table_name="loan_schedules")
    op.drop_table("loan_schedules")
    op.drop_table("loans")
    op.drop_column("assets", "salvage_value")
    op.drop_column("assets", "useful_life_years")
    op.drop_column("assets", "depreciation_method")
    op.drop_column("assets", "asset_type")
    op.drop_column("app_settings", "alpha_vantage_api_key")
