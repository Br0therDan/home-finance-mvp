from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel

# ==========================================
# Enums or Constants
# ==========================================


class Account(SQLModel, table=True):
    __tablename__ = "accounts"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    type: str  # ASSET, LIABILITY, EQUITY, INCOME, EXPENSE
    parent_id: int | None = Field(default=None, foreign_key="accounts.id")
    is_active: bool = Field(default=True)
    is_system: bool = Field(default=False)
    level: int = Field(default=1)  # 1=System, 2=User
    allow_posting: bool = Field(default=True)  # True=Leaf, False=Aggregate
    currency: str = Field(default="KRW")


class JournalLine(SQLModel, table=True):
    __tablename__ = "journal_lines"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    entry_id: int = Field(foreign_key="journal_entries.id", index=True)
    account_id: int = Field(foreign_key="accounts.id", index=True)
    debit: float = Field(default=0.0)
    credit: float = Field(default=0.0)
    memo: str = Field(default="")

    # FX Fields
    native_amount: float | None = Field(default=None)
    native_currency: str | None = Field(default=None)
    fx_rate: float | None = Field(default=None)

    entry: "core.models.JournalEntry" = Relationship(
        sa_relationship_kwargs={
            "back_populates": "lines",
        },
    )

    # Unidirectional relationship to Account (no back_populates on Account)
    account: "core.models.Account" = Relationship()


class JournalEntry(SQLModel, table=True):
    __tablename__ = "journal_entries"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    entry_date: date = Field(index=True)
    description: str
    source: str = Field(default="manual")
    created_at: datetime = Field(default_factory=datetime.now)

    lines: list["core.models.JournalLine"] = Relationship(
        sa_relationship_kwargs={
            "back_populates": "entry",
            "cascade": "all, delete-orphan",
        }
    )


class Asset(SQLModel, table=True):
    __tablename__ = "assets"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    name: str
    asset_class: str  # CASH, BANK, STOCK...
    linked_account_id: int = Field(foreign_key="accounts.id")
    acquisition_date: date
    acquisition_cost: float
    disposal_date: date | None = Field(default=None)
    note: str = Field(default="")

    # Unidirectional relationship to Account (no back_populates on Account)
    linked_account: "core.models.Account" = Relationship()

    valuations: list["core.models.AssetValuation"] = Relationship(
        sa_relationship_kwargs={
            "back_populates": "asset",
            "cascade": "all, delete-orphan",
        }
    )


class AssetValuation(SQLModel, table=True):
    __tablename__ = "asset_valuations"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="assets.id")
    as_of_date: date
    value_native: float
    currency: str
    note: str | None = Field(default=None)
    source: str = Field(default="manual")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    asset: "core.models.Asset" = Relationship(
        sa_relationship_kwargs={"back_populates": "valuations"}
    )


class JournalEntryInput(BaseModel):
    entry_date: date
    description: str
    source: str = "manual"
    lines: list[JournalLine]
