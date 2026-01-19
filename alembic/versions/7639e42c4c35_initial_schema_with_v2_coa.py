"""initial_schema_with_v2_coa

Revision ID: 7639e42c4c35
Revises:
Create Date: 2026-01-20 02:54:56.531372

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "7639e42c4c35"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Tables
    accounts_table = op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("allow_posting", sa.Boolean(), nullable=False),
        sa.Column("currency", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["accounts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_accounts_name"), "accounts", ["name"], unique=False)

    op.create_table(
        "journal_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("source", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_journal_entries_entry_date"),
        "journal_entries",
        ["entry_date"],
        unique=False,
    )

    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("asset_class", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("linked_account_id", sa.Integer(), nullable=False),
        sa.Column("acquisition_date", sa.Date(), nullable=False),
        sa.Column("acquisition_cost", sa.Float(), nullable=False),
        sa.Column("disposal_date", sa.Date(), nullable=True),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(
            ["linked_account_id"],
            ["accounts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "journal_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("debit", sa.Float(), nullable=False),
        sa.Column("credit", sa.Float(), nullable=False),
        sa.Column("memo", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("native_amount", sa.Float(), nullable=True),
        sa.Column("native_currency", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("fx_rate", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["journal_entries.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_journal_lines_account_id"),
        "journal_lines",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_journal_lines_entry_id"), "journal_lines", ["entry_id"], unique=False
    )

    op.create_table(
        "asset_valuations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("value_native", sa.Float(), nullable=False),
        sa.Column("currency", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("source", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. SEED DATA (CoA)
    # Explicit IDs to ensure stability
    initial_accounts = [
        # ASSET (1000 range) - L1
        {
            "id": 1001,
            "name": "현금",
            "type": "ASSET",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 1002,
            "name": "보통예금",
            "type": "ASSET",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 1003,
            "name": "정기예금",
            "type": "ASSET",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 1004,
            "name": "증권/투자자산",
            "type": "ASSET",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 1005,
            "name": "부동산",
            "type": "ASSET",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 1006,
            "name": "전세보증금(임차)",
            "type": "ASSET",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 1007,
            "name": "대여금/미수금",
            "type": "ASSET",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 1008,
            "name": "선급금/예치금",
            "type": "ASSET",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 1009,
            "name": "차량/운송수단",
            "type": "ASSET",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 1010,
            "name": "비품/장비",
            "type": "ASSET",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 1099,
            "name": "기타자산",
            "type": "ASSET",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        # LIABILITY (2000 range) - L1
        {
            "id": 2001,
            "name": "카드미지급금",
            "type": "LIABILITY",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 2002,
            "name": "주택담보대출",
            "type": "LIABILITY",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 2003,
            "name": "신용대출/기타대출",
            "type": "LIABILITY",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 2004,
            "name": "전세보증금(임대)",
            "type": "LIABILITY",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 2005,
            "name": "미지급금/외상",
            "type": "LIABILITY",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 2006,
            "name": "세금/공과금 미지급",
            "type": "LIABILITY",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 2099,
            "name": "기타부채",
            "type": "LIABILITY",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        # EQUITY (3000 range) - L1
        {
            "id": 3001,
            "name": "자본/순자산",
            "type": "EQUITY",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        # EQUITY (3000 range) - L2 System Leaves
        {
            "id": 300101,
            "name": "기초순자산(Opening Equity)",
            "type": "EQUITY",
            "level": 2,
            "is_system": True,
            "allow_posting": True,
            "parent_id": 3001,
        },
        # INCOME (4000 range) - L1
        {
            "id": 4001,
            "name": "근로/급여수익",
            "type": "INCOME",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 4002,
            "name": "사업/부업수익",
            "type": "INCOME",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 4003,
            "name": "임대수익",
            "type": "INCOME",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 4004,
            "name": "이자수익",
            "type": "INCOME",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 4005,
            "name": "배당수익",
            "type": "INCOME",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 4099,
            "name": "기타수익",
            "type": "INCOME",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        # EXPENSE (5000 range) - L1
        {
            "id": 5001,
            "name": "식비",
            "type": "EXPENSE",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 5002,
            "name": "주거/관리비",
            "type": "EXPENSE",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 5003,
            "name": "공과금/통신",
            "type": "EXPENSE",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 5004,
            "name": "교통/차량비",
            "type": "EXPENSE",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 5005,
            "name": "교육/육아",
            "type": "EXPENSE",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 5006,
            "name": "의료/건강",
            "type": "EXPENSE",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 5007,
            "name": "보험료",
            "type": "EXPENSE",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 5008,
            "name": "세금/수수료",
            "type": "EXPENSE",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 5009,
            "name": "이자비용",
            "type": "EXPENSE",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 5010,
            "name": "소비/쇼핑",
            "type": "EXPENSE",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 5011,
            "name": "여행/여가",
            "type": "EXPENSE",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 5012,
            "name": "감가상각비",
            "type": "EXPENSE",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        {
            "id": 5099,
            "name": "기타비용",
            "type": "EXPENSE",
            "level": 1,
            "is_system": True,
            "allow_posting": False,
        },
        # EXPENSE (5000 range) - L2 System Leaves
        {
            "id": 501201,
            "name": "감가상각비(일반)",
            "type": "EXPENSE",
            "level": 2,
            "is_system": True,
            "allow_posting": True,
            "parent_id": 5012,
        },
    ]

    # Defaults
    for acc in initial_accounts:
        acc.setdefault("is_active", True)
        acc.setdefault("currency", "KRW")
        acc.setdefault("parent_id", None)
        # Ensure bools are bools
        acc["is_active"] = bool(acc["is_active"])
        acc["is_system"] = bool(acc["is_system"])
        acc["allow_posting"] = bool(acc["allow_posting"])

    op.bulk_insert(accounts_table, initial_accounts)


def downgrade() -> None:
    op.drop_table("asset_valuations")
    op.drop_index(op.f("ix_journal_lines_entry_id"), table_name="journal_lines")
    op.drop_index(op.f("ix_journal_lines_account_id"), table_name="journal_lines")
    op.drop_table("journal_lines")
    op.drop_table("assets")
    op.drop_index(op.f("ix_journal_entries_entry_date"), table_name="journal_entries")
    op.drop_table("journal_entries")
    op.drop_index(op.f("ix_accounts_name"), table_name="accounts")
    op.drop_table("accounts")
