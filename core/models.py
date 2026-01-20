from __future__ import annotations

from datetime import date, datetime

# ==========================================
# Enums or Constants (Simple Classes)
# ==========================================


class AssetType:
    SECURITY = "SECURITY"
    REAL_ESTATE = "REAL_ESTATE"
    VEHICLE = "VEHICLE"
    OTHER = "OTHER"


class DepreciationMethod:
    NONE = "NONE"
    STRAIGHT_LINE = "STRAIGHT_LINE"
    DECLINING_BALANCE = "DECLINING_BALANCE"


class RepaymentMethod:
    AMORTIZATION = "AMORTIZATION"  # 원리금균등
    BULLET = "BULLET"  # 만기일시
    INTEREST_ONLY = "INTEREST_ONLY"  # 거치식


# ==========================================
# DTO Classes (Plain Python)
# ==========================================


class AppSettings:
    def __init__(
        self,
        id: int = None,
        base_currency: str = "KRW",
        alpha_vantage_api_key: str = None,
        updated_at: datetime = None,
    ):
        self.id = id
        self.base_currency = base_currency
        self.alpha_vantage_api_key = alpha_vantage_api_key
        self.updated_at = updated_at or datetime.now()


class FxRate:
    def __init__(
        self,
        id: int = None,
        base_currency: str = None,
        quote_currency: str = None,
        rate: float = None,
        as_of: datetime = None,
    ):
        self.id = id
        self.base_currency = base_currency
        self.quote_currency = quote_currency
        self.rate = rate
        self.as_of = as_of or datetime.now()


class Account:
    def __init__(
        self,
        id: int = None,
        name: str = None,
        type: str = None,
        parent_id: int = None,
        is_active: bool = True,
        is_system: bool = False,
        level: int = 1,
        allow_posting: bool = True,
        currency: str = "KRW",
        description: str | None = None,
        account_number: str | None = None,
    ):
        self.id = id
        self.name = name
        self.type = type
        self.parent_id = parent_id
        self.is_active = bool(is_active)
        self.is_system = bool(is_system)
        self.level = level
        self.allow_posting = bool(allow_posting)
        self.currency = currency
        self.description = description
        self.account_number = account_number


class JournalLine:
    def __init__(
        self,
        id: int = None,
        entry_id: int = None,
        account_id: int = None,
        debit: float = 0.0,
        credit: float = 0.0,
        memo: str = "",
        native_amount: float = None,
        native_currency: str = None,
        fx_rate: float = None,
    ):
        self.id = id
        self.entry_id = entry_id
        self.account_id = account_id
        self.debit = debit
        self.credit = credit
        self.memo = memo
        self.native_amount = native_amount
        self.native_currency = native_currency
        self.fx_rate = fx_rate


class JournalEntry:
    def __init__(
        self,
        id: int = None,
        entry_date: date = None,
        description: str = None,
        source: str = "manual",
        created_at: datetime = None,
    ):
        self.id = id
        self.entry_date = entry_date
        self.description = description
        self.source = source
        self.created_at = created_at or datetime.now()


class Asset:
    def __init__(
        self,
        id: int = None,
        name: str = None,
        asset_class: str = None,
        asset_type: str = "OTHER",
        linked_account_id: int = None,
        acquisition_date: date = None,
        acquisition_cost: float = None,
        disposal_date: date = None,
        note: str = "",
        depreciation_method: str = "NONE",
        useful_life_years: int = None,
        salvage_value: float = 0.0,
    ):
        self.id = id
        self.name = name
        self.asset_class = asset_class
        self.asset_type = asset_type
        self.linked_account_id = linked_account_id
        self.acquisition_date = acquisition_date
        self.acquisition_cost = acquisition_cost
        self.disposal_date = disposal_date
        self.note = note
        self.depreciation_method = depreciation_method
        self.useful_life_years = useful_life_years
        self.salvage_value = salvage_value


class InvestmentProfile:
    def __init__(
        self,
        id: int = None,
        asset_id: int = None,
        ticker: str = None,
        exchange: str = None,
        trading_currency: str = None,
        security_type: str = None,
        isin: str = None,
        broker: str = None,
    ):
        self.id = id
        self.asset_id = asset_id
        self.ticker = ticker
        self.exchange = exchange
        self.trading_currency = trading_currency
        self.security_type = security_type
        self.isin = isin
        self.broker = broker


class RealEstateProfile:
    def __init__(
        self,
        id: int = None,
        asset_id: int = None,
        address: str = None,
        property_type: str = "APARTMENT",
        area_sqm: float = None,
        exclusive_area_sqm: float = None,
        floor: int = None,
        total_floors: int = None,
        completion_date: date = None,
    ):
        self.id = id
        self.asset_id = asset_id
        self.address = address
        self.property_type = property_type
        self.area_sqm = area_sqm
        self.exclusive_area_sqm = exclusive_area_sqm
        self.floor = floor
        self.total_floors = total_floors
        self.completion_date = completion_date


class InvestmentLot:
    def __init__(
        self,
        id: int = None,
        asset_id: int = None,
        lot_date: date = None,
        quantity: float = None,
        remaining_quantity: float = None,
        unit_price_native: float = None,
        fees_native: float = 0.0,
        currency: str = None,
        fx_rate: float = None,
        created_at: datetime = None,
    ):
        self.id = id
        self.asset_id = asset_id
        self.lot_date = lot_date
        self.quantity = quantity
        self.remaining_quantity = remaining_quantity
        self.unit_price_native = unit_price_native
        self.fees_native = fees_native
        self.currency = currency
        self.fx_rate = fx_rate
        self.created_at = created_at or datetime.now()


class InvestmentEvent:
    def __init__(
        self,
        id: int = None,
        asset_id: int = None,
        event_type: str = None,
        event_date: date = None,
        quantity: float = None,
        price_per_unit_native: float = None,
        gross_amount_native: float = None,
        fees_native: float = 0.0,
        currency: str = None,
        fx_rate: float = None,
        cash_account_id: int = None,
        income_account_id: int = None,
        fee_account_id: int = None,
        journal_entry_id: int = None,
        note: str = None,
        created_at: datetime = None,
    ):
        self.id = id
        self.asset_id = asset_id
        self.event_type = event_type
        self.event_date = event_date
        self.quantity = quantity
        self.price_per_unit_native = price_per_unit_native
        self.gross_amount_native = gross_amount_native
        self.fees_native = fees_native
        self.currency = currency
        self.fx_rate = fx_rate
        self.cash_account_id = cash_account_id
        self.income_account_id = income_account_id
        self.fee_account_id = fee_account_id
        self.journal_entry_id = journal_entry_id
        self.note = note
        self.created_at = created_at or datetime.now()


class Subscription:
    def __init__(
        self,
        id: int = None,
        name: str = None,
        cadence: str = None,
        interval: int = 1,
        next_due_date: date = None,
        amount: float = None,
        debit_account_id: int = None,
        credit_account_id: int = None,
        memo: str = "",
        is_active: bool = True,
        auto_create_journal: bool = False,
        last_run_date: date = None,
        created_at: datetime = None,
        updated_at: datetime = None,
    ):
        self.id = id
        self.name = name
        self.cadence = cadence
        self.interval = interval
        self.next_due_date = next_due_date
        self.amount = amount
        self.debit_account_id = debit_account_id
        self.credit_account_id = credit_account_id
        self.memo = memo
        self.is_active = bool(is_active)
        self.auto_create_journal = bool(auto_create_journal)
        self.last_run_date = last_run_date
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()


class AssetValuation:
    def __init__(
        self,
        id: int = None,
        asset_id: int = None,
        as_of_date: date = None,
        value_native: float = None,
        currency: str = None,
        method: str = "market",
        note: str = None,
        source: str = "manual",
        fx_rate: float = None,
        created_at: datetime = None,
        updated_at: datetime = None,
    ):
        self.id = id
        self.asset_id = asset_id
        self.as_of_date = as_of_date
        self.value_native = value_native
        self.currency = currency
        self.method = method
        self.note = note
        self.source = source
        self.fx_rate = fx_rate
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()


class Loan:
    def __init__(
        self,
        id: int = None,
        name: str = None,
        asset_id: int = None,
        liability_account_id: int = None,
        principal_amount: float = None,
        interest_rate: float = None,
        term_months: int = None,
        start_date: date = None,
        repayment_method: str = "AMORTIZATION",
        payment_day: int = 1,
        grace_period_months: int = 0,
        note: str = "",
        created_at: datetime = None,
    ):
        self.id = id
        self.name = name
        self.asset_id = asset_id
        self.liability_account_id = liability_account_id
        self.principal_amount = principal_amount
        self.interest_rate = interest_rate
        self.term_months = term_months
        self.start_date = start_date
        self.repayment_method = repayment_method
        self.payment_day = payment_day
        self.grace_period_months = grace_period_months
        self.note = note
        self.created_at = created_at or datetime.now()


class LoanSchedule:
    def __init__(
        self,
        id: int = None,
        loan_id: int = None,
        due_date: date = None,
        installment_number: int = None,
        principal_payment: float = None,
        interest_payment: float = None,
        total_payment: float = None,
        remaining_balance: float = None,
        status: str = "PENDING",
        journal_entry_id: int = None,
    ):
        self.id = id
        self.loan_id = loan_id
        self.due_date = due_date
        self.installment_number = installment_number
        self.principal_payment = principal_payment
        self.interest_payment = interest_payment
        self.total_payment = total_payment
        self.remaining_balance = remaining_balance
        self.status = status
        self.journal_entry_id = journal_entry_id


class Evidence:
    def __init__(
        self,
        id: int = None,
        asset_id: int = None,
        loan_id: int = None,
        file_path: str = None,
        original_filename: str = None,
        note: str = "",
        created_at: datetime = None,
    ):
        self.id = id
        self.asset_id = asset_id
        self.loan_id = loan_id
        self.file_path = file_path
        self.original_filename = original_filename
        self.note = note
        self.created_at = created_at or datetime.now()


# For compatibility during transition if needed
class JournalEntryInput:
    def __init__(
        self,
        entry_date: date,
        description: str,
        lines: list[JournalLine],
        source: str = "manual",
    ):
        self.entry_date = entry_date
        self.description = description
        self.source = source
        self.lines = lines
