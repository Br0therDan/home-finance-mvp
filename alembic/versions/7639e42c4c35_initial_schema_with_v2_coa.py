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
    # 2. SEED DATA (CoA from CSV)
    import csv
    from pathlib import Path

    # Locate the CSV file relative to the project root
    # Assuming alembic is running from project root, or we can find it relative to this file
    # This file is in alembic/versions/
    # Seed is in core/seeds/

    # Try to find the seed file safely
    current_file = Path(__file__).resolve()
    # ../../core/seeds/seed_coa.csv
    seed_path = current_file.parent.parent.parent / "core" / "seeds" / "seed_coa.csv"

    if not seed_path.exists():
        # Fallback if path resolution fails (e.g. running differently)
        seed_path = Path("core/seeds/seed_coa.csv")

    if not seed_path.exists():
        print(f"WARNING: Seed file not found at {seed_path}. Skipping CoA seeding.")
        return

    initial_accounts = []
    with open(seed_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert types
            acc = {
                "id": int(row["id"]),
                "name": row["name"],
                "type": row["type"],
                "level": int(row["level"]),
                "is_system": bool(int(row["is_system"])),
                "allow_posting": bool(int(row["allow_posting"])),
                "is_active": bool(int(row.get("is_active", 1))),
                "currency": row.get("currency", "KRW"),
                "parent_id": int(row["parent_id"]) if row.get("parent_id") else None,
            }
            initial_accounts.append(acc)

    if initial_accounts:
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
