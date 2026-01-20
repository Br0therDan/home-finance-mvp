from datetime import date, datetime

from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel

# ==========================================
# Enums or Constants
# ==========================================


class AppSettings(SQLModel, table=True):
    __tablename__ = "app_settings"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    base_currency: str = Field(default="KRW")
    updated_at: datetime = Field(default_factory=datetime.now)


class FxRate(SQLModel, table=True):
    __tablename__ = "fx_rates"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    base_currency: str = Field(index=True)
    quote_currency: str = Field(index=True)
    rate: float
    as_of: datetime = Field(default_factory=datetime.now, index=True)


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

    entry: "JournalEntry" = Relationship(back_populates="lines")

    # Unidirectional relationship to Account (no back_populates on Account)
    account: "Account" = Relationship()


class JournalEntry(SQLModel, table=True):
    __tablename__ = "journal_entries"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    entry_date: date = Field(index=True)
    description: str
    source: str = Field(default="manual")
    created_at: datetime = Field(default_factory=datetime.now)

    lines: list["JournalLine"] = Relationship(
        back_populates="entry", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
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
    linked_account: "Account" = Relationship()

    valuations: list["AssetValuation"] = Relationship(
        back_populates="asset", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    investment_profile: "InvestmentProfile" = Relationship(
        back_populates="asset", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    investment_lots: list["InvestmentLot"] = Relationship(
        back_populates="asset", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    investment_events: list["InvestmentEvent"] = Relationship(
        back_populates="asset", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class InvestmentProfile(SQLModel, table=True):
    __tablename__ = "investment_profiles"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="assets.id", index=True, unique=True)
    ticker: str = Field(index=True)
    exchange: str | None = Field(default=None, index=True)
    trading_currency: str
    security_type: str | None = Field(default=None)
    isin: str | None = Field(default=None, index=True)
    broker: str | None = Field(default=None)

    asset: "Asset" = Relationship(back_populates="investment_profile")


class InvestmentLot(SQLModel, table=True):
    __tablename__ = "investment_lots"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="assets.id", index=True)
    lot_date: date = Field(index=True)
    quantity: float
    remaining_quantity: float
    unit_price_native: float
    fees_native: float = Field(default=0.0)
    currency: str
    fx_rate: float | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now, index=True)

    asset: "Asset" = Relationship(back_populates="investment_lots")


class InvestmentEvent(SQLModel, table=True):
    __tablename__ = "investment_events"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="assets.id", index=True)
    event_type: str = Field(index=True)
    event_date: date = Field(index=True)
    quantity: float | None = Field(default=None)
    price_per_unit_native: float | None = Field(default=None)
    gross_amount_native: float | None = Field(default=None)
    fees_native: float = Field(default=0.0)
    currency: str
    fx_rate: float | None = Field(default=None)
    cash_account_id: int | None = Field(default=None, foreign_key="accounts.id")
    income_account_id: int | None = Field(default=None, foreign_key="accounts.id")
    fee_account_id: int | None = Field(default=None, foreign_key="accounts.id")
    journal_entry_id: int | None = Field(default=None, foreign_key="journal_entries.id")
    note: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now, index=True)

    asset: "Asset" = Relationship(back_populates="investment_events")


class Subscription(SQLModel, table=True):
    __tablename__ = "subscriptions"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    name: str
    cadence: str = Field(index=True)
    interval: int = Field(default=1)
    next_due_date: date = Field(index=True)
    amount: float
    debit_account_id: int = Field(foreign_key="accounts.id")
    credit_account_id: int = Field(foreign_key="accounts.id")
    memo: str = Field(default="")
    is_active: bool = Field(default=True)
    auto_create_journal: bool = Field(default=False)
    last_run_date: date | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class AssetValuation(SQLModel, table=True):
    __tablename__ = "asset_valuations"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="assets.id", index=True)
    as_of_date: date = Field(index=True)
    value_native: float
    currency: str
    method: str = Field(default="market")
    note: str | None = Field(default=None)
    source: str = Field(default="manual")
    fx_rate: float | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    asset: "Asset" = Relationship(back_populates="valuations")


class JournalEntryInput(BaseModel):
    entry_date: date
    description: str
    source: str = "manual"
    lines: list[JournalLine]
