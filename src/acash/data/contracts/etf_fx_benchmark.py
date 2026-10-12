"""ETF, FX, and Benchmark Data Contracts for Phase M1 Personal Quantitative System.

Strictly enforces:
1. ETF Inception Boundaries: Fail-closed if observations precede fund inception without explicit synthetic proxy designation.
2. Separation of Concerns: Raw execution price != Split-adjusted != Dividend-adjusted != NAV != Total Return.
3. Corporate Actions & Distributions: Ex-date vs. payable-date modeling; dividend double-count prevention.
4. FX Quote Directionality & Valuation: Fail-closed quote orientation checks for cross-currency conversion.
5. Cash / Risk-Free Accrual: Canonical ACT/360 and ACT/365 yield accrual.
6. Broker Friction Model: Enforces minimum commission constraints (e.g. IBKR $0.35/$1.00) critical for small-capital portfolios ($1,000).
7. Holdings-Based Benchmark: Tracks shares, cash, and drifting weights; rebalances only on scheduled dates with explicit friction.
8. Gross/Net Distribution Separation: Owner-specific tax deductions are separate from provider-reported gross distributions.
"""
from __future__ import annotations

# Model Classification Labels (for audit provenance)
IBKR_COST_MODEL_CLASSIFICATION = "IBKR_INSPIRED_SYNTHETIC_FRICTION"  # NOT ACCOUNT_VERIFIED_ACTUAL_FEE
HOLDINGS_BENCHMARK_CLASSIFICATION = "SYNTHETIC_HOLDINGS_BASED_BENCHMARK"  # NOT live execution

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_DOWN
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from acash.core.domain.exceptions import DataContractError, DomainValidationError
from acash.core.domain.types import ensure_finite_decimal
from acash.data.calendar.nyse_ca1 import NonTradingDayError, NyseCa1Calendar
from acash.data.schema import validate_decimal128_bounds


class AssetClass(str, Enum):
    GLOBAL_EQUITY = "GLOBAL_EQUITY"
    FIXED_INCOME = "FIXED_INCOME"
    COMMODITY_GOLD = "COMMODITY_GOLD"
    CASH_EQUIVALENT = "CASH_EQUIVALENT"


class PriceBasis(str, Enum):
    """Declared epistemic basis of historical prices to prevent double-adjustment."""
    RAW_UNADJUSTED_PRICE = "RAW_UNADJUSTED_PRICE"
    SPLIT_ADJUSTED_PRICE = "SPLIT_ADJUSTED_PRICE"
    DIVIDEND_ADJUSTED_PRICE = "DIVIDEND_ADJUSTED_PRICE"
    TOTAL_RETURN_ADJUSTED_PRICE = "TOTAL_RETURN_ADJUSTED_PRICE"
    ETF_NAV = "ETF_NAV"
    EXECUTABLE_MARKET_PRICE = "EXECUTABLE_MARKET_PRICE"


class DayCountConvention(str, Enum):
    ACT_360 = "ACT/360"
    ACT_365 = "ACT/365"


class EtfInstrumentContract(BaseModel):
    """Authoritative metadata and inception boundary for a target ETF instrument."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    name: str
    asset_class: AssetClass
    base_currency: str = "USD"
    inception_date: date
    is_synthetic_proxy: bool = False
    proxy_underlying: Optional[str] = None

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        s = v.strip().upper()
        if not s:
            raise DomainValidationError("Symbol cannot be empty.")
        return s

    def validate_observation_date(self, obs_date: date) -> None:
        """Enforce strict inception boundary fail-closed."""
        if obs_date < self.inception_date and not self.is_synthetic_proxy:
            raise DataContractError(
                f"Observation date {obs_date} strictly precedes {self.symbol} inception date {self.inception_date}. "
                "Historical observations cannot be fabricated without explicit synthetic proxy designation."
            )


# Canonical Inception Registry for Personal Quant Universe
KNOWN_ETF_REGISTRY: Mapping[str, EtfInstrumentContract] = {
    "VOO": EtfInstrumentContract(
        symbol="VOO",
        name="Vanguard S&P 500 ETF",
        asset_class=AssetClass.GLOBAL_EQUITY,
        base_currency="USD",
        inception_date=date(2010, 9, 7),
    ),
    "BND": EtfInstrumentContract(
        symbol="BND",
        name="Vanguard Total Bond Market ETF",
        asset_class=AssetClass.FIXED_INCOME,
        base_currency="USD",
        inception_date=date(2007, 4, 10),
    ),
    "AGG": EtfInstrumentContract(
        symbol="AGG",
        name="iShares Core U.S. Aggregate Bond ETF",
        asset_class=AssetClass.FIXED_INCOME,
        base_currency="USD",
        inception_date=date(2003, 9, 22),
    ),
    "GLD": EtfInstrumentContract(
        symbol="GLD",
        name="SPDR Gold Shares",
        asset_class=AssetClass.COMMODITY_GOLD,
        base_currency="USD",
        inception_date=date(2004, 11, 18),
    ),
    "BIL": EtfInstrumentContract(
        symbol="BIL",
        name="SPDR Bloomberg 1-3 Month T-Bill ETF",
        asset_class=AssetClass.CASH_EQUIVALENT,
        base_currency="USD",
        inception_date=date(2007, 5, 25),
    ),
}


class DistributionTaxClassification(str, Enum):
    """Distinguish reported gross amount from investor net cash.

    Owner-specific withholding rates (e.g. 15% US-Thai DTA via W-8BEN) are applied
    OUTSIDE source-reported gross amounts. Never assume 15% universally.
    """
    GROSS_BEFORE_WITHHOLDING = "GROSS_BEFORE_WITHHOLDING"   # Issuer/provider-reported amount
    NET_AFTER_WITHHOLDING = "NET_AFTER_WITHHOLDING"          # After owner-specific deduction
    UNKNOWN_TAX_BASIS = "UNKNOWN_TAX_BASIS"                  # Ambiguous — fail-closed for research


class DistributionShareBasis(str, Enum):
    """Declared share basis for a distribution on the same ex-date as a split.

    Single canonical authority for interpreting simultaneous split/dividend
    economics. POST_SPLIT matches build_total_return_panel() where one
    pre-split share becomes split_ratio post-split shares each earning
    cash_amount. PRE_SPLIT means cash_amount applies per pre-split share.
    UNKNOWN (default for legacy records) fails closed when a same-session
    split exists for the symbol — the adapter must declare the basis.
    """

    PRE_SPLIT = "PRE_SPLIT"
    POST_SPLIT = "POST_SPLIT"
    UNKNOWN = "UNKNOWN"


class EtfDistributionRecord(BaseModel):
    """Immutable record of an ETF dividend/capital gain cash distribution.

    Always record the gross_amount as reported by the issuer/provider.
    If owner-specific withholding applies, set net_amount and tax_classification separately.
    Never silently apply universal 15% withholding — it is owner-specific and treaty-dependent.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    ex_date: date
    record_date: Optional[date] = None
    payable_date: date
    gross_amount: Decimal                                    # Issuer-reported gross distribution
    net_amount: Optional[Decimal] = None                    # Net after owner withholding (if known)
    withholding_rate: Optional[Decimal] = None              # Owner-specific rate (e.g. 0.15 for DTA)
    tax_classification: DistributionTaxClassification = DistributionTaxClassification.GROSS_BEFORE_WITHHOLDING
    distribution_type: str = "DIVIDEND_CASH"
    event_id: Optional[str] = None                          # Source-provided event identity (if any)
    share_basis: DistributionShareBasis = DistributionShareBasis.UNKNOWN

    # Legacy compatibility: cash_amount resolves to net if available, gross otherwise
    @property
    def cash_amount(self) -> Decimal:
        """Cash amount to use in total return calculations.

        Returns net_amount if provided (owner has applied withholding),
        otherwise returns gross_amount. Callers should explicitly set
        net_amount when owner withholding is known.
        """
        return self.net_amount if self.net_amount is not None else self.gross_amount

    @field_validator("gross_amount")
    @classmethod
    def validate_gross_amount(cls, v: Decimal) -> Decimal:
        ensure_finite_decimal(v, field_name="gross_amount")
        if v <= Decimal("0"):
            raise DomainValidationError(f"gross_amount must be strictly positive, got {v}")
        return v

    @field_validator("net_amount")
    @classmethod
    def validate_net_amount(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            ensure_finite_decimal(v, field_name="net_amount")
            if v <= Decimal("0"):
                raise DomainValidationError(f"net_amount must be strictly positive if provided, got {v}")
        return v

    @field_validator("withholding_rate")
    @classmethod
    def validate_withholding_rate(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            ensure_finite_decimal(v, field_name="withholding_rate")
            if not (Decimal("0") <= v < Decimal("1")):
                raise DomainValidationError(f"withholding_rate must be in [0, 1), got {v}")
        return v

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise DomainValidationError("event_id, when provided, must be non-blank.")
        return v

    @model_validator(mode="after")
    def validate_distribution_consistency(self) -> "EtfDistributionRecord":
        if self.payable_date < self.ex_date:
            raise DataContractError(
                f"payable_date ({self.payable_date}) cannot precede ex_date ({self.ex_date})."
            )
        if self.net_amount is not None and self.net_amount > self.gross_amount:
            raise DataContractError(
                f"net_amount ({self.net_amount}) cannot exceed gross_amount ({self.gross_amount})."
            )
        if self.withholding_rate is not None and self.net_amount is None:
            raise DataContractError(
                "withholding_rate is set but net_amount is None. Compute net_amount = gross * (1 - rate)."
            )
        if self.withholding_rate is not None and self.net_amount is not None:
            expected_net = self.gross_amount * (Decimal("1") - self.withholding_rate)
            if self.net_amount != expected_net:
                raise DataContractError(
                    f"net_amount ({self.net_amount}) is inconsistent with "
                    f"gross_amount * (1 - withholding_rate) = {expected_net}. "
                    "Net must be exactly computed, never hand-adjusted."
                )
        return self


class EtfSplitRecord(BaseModel):
    """Immutable record of a stock split corporate action."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    ex_date: date
    split_from: Decimal
    split_to: Decimal

    @property
    def split_ratio(self) -> Decimal:
        return self.split_to / self.split_from

    @field_validator("split_from", "split_to")
    @classmethod
    def validate_ratios(cls, v: Decimal, info: Any) -> Decimal:
        ensure_finite_decimal(v, field_name=getattr(info, "field_name", "split_val"))
        if v <= Decimal("0"):
            raise DomainValidationError("Split components must be strictly positive.")
        return v


class EtfDailyObservation(BaseModel):
    """Complete, dimensionally separated daily observation record for an ETF."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    trading_date: date
    raw_close: Decimal
    price_basis: PriceBasis = PriceBasis.RAW_UNADJUSTED_PRICE
    split_factor: Decimal = Decimal("1.0")
    cumulative_dividend: Decimal = Decimal("0.0")
    total_return_factor: Decimal = Decimal("1.0")
    nav: Optional[Decimal] = None
    volume: Decimal = Decimal("0.0")

    @field_validator("raw_close")
    @classmethod
    def validate_raw_close(cls, v: Decimal) -> Decimal:
        ensure_finite_decimal(v, field_name="raw_close")
        validate_decimal128_bounds(v, field_name="raw_close")
        if v <= Decimal("0"):
            raise DomainValidationError(f"raw_close must be strictly positive, got {v}")
        return v

    @field_validator("nav")
    @classmethod
    def validate_nav(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            ensure_finite_decimal(v, field_name="nav")
            if v <= Decimal("0"):
                raise DomainValidationError(f"nav must be strictly positive if provided, got {v}")
        return v

    @property
    def split_adjusted_close(self) -> Decimal:
        return self.raw_close * self.split_factor


class FxFixingRecord(BaseModel):
    """Authoritative official daily foreign exchange reference fixing rate."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    base_currency: str
    quote_currency: str
    fixing_date: date
    rate: Decimal
    source: str = "BOT"  # Bank of Thailand or Federal Reserve

    @field_validator("base_currency", "quote_currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        s = v.strip().upper()
        if len(s) != 3:
            raise DomainValidationError(f"Currency code must be 3 characters, got '{v}'")
        return s

    @field_validator("rate")
    @classmethod
    def validate_rate(cls, v: Decimal) -> Decimal:
        ensure_finite_decimal(v, field_name="rate")
        if v <= Decimal("0"):
            raise DomainValidationError(f"FX rate must be strictly positive, got {v}")
        return v

    def convert(self, amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
        """Convert currency with strict orientation checks fail-closed."""
        ensure_finite_decimal(amount, field_name="amount")
        f_curr = from_currency.strip().upper()
        t_curr = to_currency.strip().upper()

        if f_curr == t_curr:
            return amount

        if f_curr == self.base_currency and t_curr == self.quote_currency:
            return amount * self.rate
        elif f_curr == self.quote_currency and t_curr == self.base_currency:
            return amount / self.rate
        else:
            raise DataContractError(
                f"Cannot convert {f_curr} -> {t_curr} using fixing pair {self.base_currency}/{self.quote_currency}."
            )


class CashAccrualModel(BaseModel):
    """Computes exact daily risk-free or cash yield accrual in Decimal space."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    annual_rate: Decimal
    convention: DayCountConvention = DayCountConvention.ACT_360

    @field_validator("annual_rate")
    @classmethod
    def validate_annual_rate(cls, v: Decimal) -> Decimal:
        ensure_finite_decimal(v, field_name="annual_rate")
        if v < Decimal("0"):
            raise DomainValidationError("annual_rate cannot be negative.")
        return v

    def accrue(self, principal: Decimal, days: int) -> Decimal:
        """Calculate accrued interest for a given period in days."""
        ensure_finite_decimal(principal, field_name="principal")
        if principal < Decimal("0"):
            raise DomainValidationError("principal cannot be negative.")
        if days < 0:
            raise DomainValidationError("days cannot be negative.")

        divisor = Decimal("360") if self.convention == DayCountConvention.ACT_360 else Decimal("365")
        return principal * self.annual_rate * (Decimal(str(days)) / divisor)


class SmallOrderFrictionModel(BaseModel):
    """Per-share Tiered-style cost model for small ($1,000) accounts.

    Classification: IBKR_INSPIRED_SYNTHETIC_FRICTION (see
    IBKR_COST_MODEL_CLASSIFICATION). This is NOT an account-verified fee
    schedule.

    Modeled (IBKR US Tiered, whole shares): per-share commission with
    per-order minimum and order-value cap, plus half-spread and slippage.
    Explicitly NOT modeled: Pro Fixed schedule, fractional-share-specific
    terms, exchange/clearing/regulatory pass-through fees, FX conversion
    spreads, and Thailand-to-broker funding costs. Whole-share quantity basis
    is assumed; fractional-share orders must not use this model silently.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    pricing_schedule: str = "IBKR_TIERED_US_SYNTHETIC"
    share_quantity_basis: str = "WHOLE_SHARE"
    per_share_commission: Decimal = Decimal("0.0035")  # IBKR Tiered US stocks
    min_commission_usd: Decimal = Decimal("0.35")      # IBKR Tiered per-order minimum
    max_commission_pct: Decimal = Decimal("0.01")      # IBKR rule: maximum 1.0% of order value
    half_spread: Decimal = Decimal("0.0005")           # 5 bps synthetic assumption
    slippage: Decimal = Decimal("0.0002")              # 2 bps synthetic assumption

    def calculate_cost(self, notional_traded: Decimal, shares_traded: Decimal) -> Decimal:
        """Calculate total transaction friction (Tiered per-share + floor + cap).

        `shares_traded` must be the executed whole-share quantity. Fractional
        quantities are rejected: this tariff models whole shares only, and
        IBKR prices fractional trades under separate terms (documented but
        unmodeled here). A positive notional with zero shares is inconsistent
        under the whole-share basis and fails closed.
        """
        ensure_finite_decimal(notional_traded, field_name="notional_traded")
        ensure_finite_decimal(shares_traded, field_name="shares_traded")
        if notional_traded < Decimal("0") or shares_traded < Decimal("0"):
            raise DomainValidationError("notional_traded and shares_traded cannot be negative.")
        if notional_traded == Decimal("0"):
            return Decimal("0.0")
        if shares_traded == Decimal("0"):
            raise DataContractError(
                "Positive notional with zero shares is inconsistent under WHOLE_SHARE basis."
            )
        if shares_traded != shares_traded.to_integral_value():
            raise DataContractError(
                f"FRACTIONAL_SHARES_UNSUPPORTED: {shares_traded} shares cannot pass "
                "through the WHOLE_SHARE tariff. Fractional execution requires a "
                "separately documented fractional fee model."
            )

        per_share_commission = shares_traded * self.per_share_commission
        max_cap = notional_traded * self.max_commission_pct
        actual_commission = min(max(per_share_commission, self.min_commission_usd), max_cap)
        spread_and_slippage = notional_traded * (self.half_spread + self.slippage)
        return actual_commission + spread_and_slippage


def build_total_return_panel(
    instrument: EtfInstrumentContract,
    raw_bars: Sequence[Tuple[date, Decimal]],  # (trading_date, price)
    distributions: Sequence[EtfDistributionRecord] = (),
    splits: Sequence[EtfSplitRecord] = (),
    price_basis: PriceBasis = PriceBasis.RAW_UNADJUSTED_PRICE,
) -> List[EtfDailyObservation]:
    """Construct an immutable sequence of total return observations with split and dividend reinvestment.

    Fails closed if:
    - Observations precede fund inception date.
    - Dates are not strictly monotonically increasing.
    - Prices are non-positive or non-finite.
    - Double-counting hazard: applying splits/distributions to already adjusted series.
    - Unknown price_basis provided.
    """
    if not raw_bars:
        raise DataContractError("Cannot build total return panel from empty raw bars.")

    if not isinstance(price_basis, PriceBasis):
        try:
            price_basis = PriceBasis(str(price_basis))
        except ValueError:
            raise DataContractError(f"Unknown or invalid price_basis: '{price_basis}'")

    # Double-counting prevention guards
    if price_basis == PriceBasis.TOTAL_RETURN_ADJUSTED_PRICE:
        if len(distributions) > 0:
            raise DataContractError(
                "Double-counting hazard: cannot apply cash distributions to a TOTAL_RETURN_ADJUSTED_PRICE series."
            )
        if len(splits) > 0:
            raise DataContractError(
                "Double-counting hazard: cannot apply splits to a TOTAL_RETURN_ADJUSTED_PRICE series."
            )
    elif price_basis == PriceBasis.SPLIT_ADJUSTED_PRICE:
        if len(splits) > 0:
            raise DataContractError(
                "Double-counting hazard: cannot apply splits to a SPLIT_ADJUSTED_PRICE series."
            )
    elif price_basis == PriceBasis.DIVIDEND_ADJUSTED_PRICE:
        if len(distributions) > 0:
            raise DataContractError(
                "Double-counting hazard: cannot apply cash distributions to a DIVIDEND_ADJUSTED_PRICE series."
            )

    # Index distributions by ex_date, preserving declared share basis.
    # Same-session splits apply BEFORE entitlements: POST_SPLIT amounts are
    # per post-split share (TR-panel canonical convention); PRE_SPLIT
    # amounts are normalized to post-split-per-share (divided by the
    # same-session split ratio) so both engines agree. UNKNOWN basis with a
    # same-session split fails closed (AMBIGUOUS_SHARE_BASIS).
    dist_map: Dict[date, List[EtfDistributionRecord]] = {}
    for d in distributions:
        if d.symbol != instrument.symbol:
            raise DataContractError(f"Distribution symbol {d.symbol} != instrument {instrument.symbol}")
        dist_map.setdefault(d.ex_date, []).append(d)

    # Index splits by ex_date
    split_map: Dict[date, Decimal] = {}
    for s in splits:
        if s.symbol != instrument.symbol:
            raise DataContractError(f"Split symbol {s.symbol} != instrument {instrument.symbol}")
        if s.ex_date in split_map:
            raise DataContractError(f"Duplicate split record on ex_date {s.ex_date} for {s.symbol}")
        split_map[s.ex_date] = s.split_ratio

    observations: List[EtfDailyObservation] = []
    prev_date: Optional[date] = None
    prev_price: Optional[Decimal] = None
    cum_tr_factor = Decimal("1.0")
    cum_div = Decimal("0.0")
    cum_split_factor = Decimal("1.0")

    for trading_date, price in raw_bars:
        # 1. Enforce inception boundary
        instrument.validate_observation_date(trading_date)

        # 2. Enforce monotonic dates
        if prev_date is not None and trading_date <= prev_date:
            raise DataContractError(
                f"Non-monotonic date sequence detected: {trading_date} <= {prev_date}."
            )

        ensure_finite_decimal(price, field_name="price")
        if price <= Decimal("0"):
            raise DomainValidationError(f"Price must be strictly positive (> 0), got {price}")

        # 3. Handle distributions and splits on ex-date
        divs_today = dist_map.get(trading_date, [])
        split_ratio_today = split_map.get(trading_date, Decimal("1.0"))
        div_amount_today = Decimal("0.0")
        for d in divs_today:
            if split_ratio_today != Decimal("1.0"):
                if d.share_basis == DistributionShareBasis.UNKNOWN:
                    raise DataContractError(
                        f"AMBIGUOUS_SHARE_BASIS: {d.symbol} distribution "
                        f"on split ex-date {d.ex_date} has undeclared "
                        "share_basis. Declare PRE_SPLIT or POST_SPLIT."
                    )
                if d.share_basis == DistributionShareBasis.PRE_SPLIT:
                    # Normalize to post-split-per-share so the TR formula
                    # (split_ratio * (price + div)) matches holdings.
                    div_amount_today += d.cash_amount / split_ratio_today
                    continue
            div_amount_today += d.cash_amount
        cum_div += div_amount_today

        cum_split_factor *= split_ratio_today

        # 4. Total return factor progression
        if prev_price is not None:
            if price_basis == PriceBasis.TOTAL_RETURN_ADJUSTED_PRICE:
                period_gross_return = price / prev_price
            elif price_basis == PriceBasis.SPLIT_ADJUSTED_PRICE:
                period_gross_return = (price + div_amount_today) / prev_price
            elif price_basis == PriceBasis.DIVIDEND_ADJUSTED_PRICE:
                period_gross_return = (split_ratio_today * price) / prev_price
            else:
                # RAW_UNADJUSTED_PRICE, EXECUTABLE_MARKET_PRICE, ETF_NAV
                # 1 pre-split share at t-1 becomes split_ratio_today shares at t, each with price + dividend
                period_gross_return = (split_ratio_today * (price + div_amount_today)) / prev_price

            cum_tr_factor *= period_gross_return

        obs = EtfDailyObservation(
            symbol=instrument.symbol,
            trading_date=trading_date,
            raw_close=price,
            price_basis=price_basis,
            split_factor=cum_split_factor,
            cumulative_dividend=cum_div,
            total_return_factor=cum_tr_factor,
        )
        observations.append(obs)

        prev_date = trading_date
        prev_price = price

    return observations


# ---------------------------------------------------------------------------
# Synthetic Trading Calendar Guard (Phase 3)
# ---------------------------------------------------------------------------
# Single canonical authority: NyseCa1Calendar (official NYSE pinned artifacts,
# 2013-2026). No duplicated holiday tables here.


def validate_synthetic_trading_session(session_date: date) -> None:
    """Fail-closed guard: reject weekend and official US equity holiday dates.

    Delegates to the single canonical NyseCa1Calendar authority. Synthetic ETF
    session sequences must not include non-trading days. Missing FX fixings on
    non-sessions are genuine omissions; do not fabricate same-day fixings.

    Raises:
        DataContractError: if session_date is a weekend or an official holiday
            (NonTradingDayError is itself a DataContractError subclass).
    """
    calendar = NyseCa1Calendar()
    try:
        calendar.get_session(session_date)
    except NonTradingDayError as exc:
        raise DataContractError(
            f"INVALID_SESSION_DATE: {exc} "
            "Synthetic ETF sessions must use canonical trading sessions only."
        ) from exc


def build_valid_synthetic_session_sequence(dates: Sequence[date]) -> Sequence[date]:
    """Validate and return a sequence of synthetic trading dates after strict calendar checking.

    All dates are checked against weekend and known-holiday guards fail-closed.
    Dates must be strictly monotonically increasing.

    Returns the validated sequence unchanged (for downstream binding).
    Raises DataContractError on any invalid date.
    """
    if not dates:
        raise DataContractError("Synthetic session sequence cannot be empty.")
    prev: Optional[date] = None
    for d in dates:
        validate_synthetic_trading_session(d)
        if prev is not None and d <= prev:
            raise DataContractError(
                f"Non-monotonic synthetic session sequence: {d} <= {prev}."
            )
        prev = d
    return dates


def resolve_fx_fixing_for_date(
    fixings: Mapping[date, FxFixingRecord], fixing_date: date
) -> FxFixingRecord:
    """Fail-closed as-of FX fixing resolution: exact-date match only.

    A missing fixing for `fixing_date` is a genuine omission (weekend, holiday,
    or unpublished fixing) and must NEVER silently become a same-day verified
    fixing via fallback to another date. Callers must handle the raised error
    by excluding the date or obtaining the authoritative fixing.
    """
    try:
        return fixings[fixing_date]
    except KeyError:
        raise DataContractError(
            f"MISSING_FX_FIXING: no verified fixing for {fixing_date}. "
            "Fallback to another date's fixing is prohibited."
        ) from None


# ---------------------------------------------------------------------------
# Exact Cash Accrual Convention Results (Phase 4)
# ---------------------------------------------------------------------------

class CashAccrualConventionResult:
    """Exact named accrual results for a given principal/rate/days under each convention.

    Consumers must explicitly choose a convention; the two results are NOT interchangeable.
    Do not claim ACT/360 and ACT/365 are economically equivalent.

    Example (principal=1000, rate=0.045, days=4):
      ACT/360 interest = 1000 * 0.045 * 4/360 = 0.50000  (exactly)
      ACT/365 interest = 1000 * 0.045 * 4/365 = 0.49315... (approximately)
    """

    def __init__(self, principal: Decimal, annual_rate: Decimal, days: int) -> None:
        if days < 0:
            raise DataContractError("days cannot be negative.")
        ensure_finite_decimal(principal, field_name="principal")
        ensure_finite_decimal(annual_rate, field_name="annual_rate")
        self.principal = principal
        self.annual_rate = annual_rate
        self.days = days
        d = Decimal(str(days))
        self.act_360_interest: Decimal = principal * annual_rate * (d / Decimal("360"))
        self.act_365_interest: Decimal = principal * annual_rate * (d / Decimal("365"))
        self.act_360_ending_nav: Decimal = principal + self.act_360_interest
        self.act_365_ending_nav: Decimal = principal + self.act_365_interest

    def __repr__(self) -> str:
        return (
            f"CashAccrualConventionResult("
            f"principal={self.principal}, rate={self.annual_rate}, days={self.days}, "
            f"ACT/360_interest={self.act_360_interest}, "
            f"ACT/365_interest={self.act_365_interest})"
        )


# ---------------------------------------------------------------------------
# Holdings-Based Benchmark Engine (Phase 2)
# ---------------------------------------------------------------------------

class HoldingsBenchmarkTransaction:
    """Record of a single benchmark trade (rebalance or initial buy) for lineage."""

    def __init__(
        self,
        trading_date: date,
        symbol: str,
        shares_delta: Decimal,
        price: Decimal,
        notional: Decimal,
        friction_cost: Decimal,
        reason: str,
    ) -> None:
        self.trading_date = trading_date
        self.symbol = symbol
        self.shares_delta = shares_delta   # positive = buy, negative = sell
        self.price = price
        self.notional = notional
        self.friction_cost = friction_cost
        self.reason = reason

    def __repr__(self) -> str:
        return (
            f"HoldingsBenchmarkTransaction({self.trading_date}, {self.symbol}, "
            f"delta={self.shares_delta}, price={self.price}, "
            f"friction={self.friction_cost}, reason={self.reason})"
        )


class HoldingsBasedBenchmark:
    """Holdings-based benchmark engine tracking shares, cash, and drifting weights.

    Classification: SYNTHETIC_HOLDINGS_BASED_BENCHMARK
    This is NOT a live order engine. All fills are synthetic at raw close price.
    No fractional shares by default (positions are whole-share quantities).
    Rebalancing occurs only on specified scheduled dates.
    Transaction friction is explicit (never silent).
    Negative cash raises DataContractError (no implicit leverage or borrowing).
    """

    def __init__(
        self,
        target_weights: Dict[str, Decimal],
        rebalance_dates: Set[date],
        friction_model: "SmallOrderFrictionModel",
        allow_fractional_shares: bool = False,
        model_classification: str = HOLDINGS_BENCHMARK_CLASSIFICATION,
    ) -> None:
        if not target_weights:
            raise DataContractError("Target weights must name at least one holding.")
        for sym, wt in target_weights.items():
            ensure_finite_decimal(wt, field_name=f"target_weight[{sym}]")
            if wt < Decimal("0"):
                raise DataContractError(
                    f"LONG_ONLY_VIOLATION: target weight for {sym} is negative ({wt}). "
                    "Short positions are prohibited in this benchmark."
                )
        total_weight = sum(target_weights.values(), Decimal("0"))
        if abs(total_weight - Decimal("1")) > Decimal("0.0001"):
            raise DataContractError(
                f"Target weights must sum to 1.0, got {total_weight}."
            )
        # All weights are finite and non-negative and sum to 1.0, therefore
        # gross exposure equals 1.0 exactly: no hidden leverage is expressible.
        self.target_weights = dict(target_weights)
        self.rebalance_dates = rebalance_dates
        self.friction_model = friction_model
        self.allow_fractional_shares = allow_fractional_shares
        self.model_classification = model_classification

        self._shares: Dict[str, Decimal] = {}
        self._cash: Decimal = Decimal("0")
        # Ex-date entitlements not yet paid: (symbol, payable_date) -> amount.
        # Entitlement is fixed by shares held on ex-date; cash arrives on
        # payable date. NAV includes receivables (economic entitlement).
        self._receivables: Dict[Tuple[str, date], Decimal] = {}
        # Event identity sets for replay safety (monotonic processing below
        # makes replays unreachable, these are defense-in-depth lineage).
        # Booked key is the FULL event identity: distinct events sharing a
        # symbol/ex-date/payable triple (e.g. dividend + capital gain) never
        # merge silently; settlement stays keyed by (symbol, payable) because
        # cash is fungible on arrival. A second record reusing the same
        # provider event_id with DIFFERENT economics (revised amount) is a
        # provider revision, not a new event — it fails closed
        # (REVISED_EVENT) instead of double-booking.
        self._booked_entitlements: Set[Tuple[str, date, date, str, str, str, str, str]] = set()
        self._booked_provider_event_ids: Set[Tuple[str, str]] = set()
        self._settled_payables: Set[Tuple[str, date]] = set()
        self._applied_splits: Set[Tuple[str, date]] = set()
        self._initialized: bool = False
        self.nav_history: List[Decimal] = []
        self.date_history: List[date] = []
        self.weight_history: List[Dict[str, Decimal]] = []
        self.transactions: List[HoldingsBenchmarkTransaction] = []

    def _receivables_total(self) -> Decimal:
        return sum(self._receivables.values(), Decimal("0"))

    def outstanding_receivables(self) -> Dict[Tuple[str, date], Decimal]:
        """Current ex-date entitlements awaiting payable-date cash (read-only copy)."""
        return dict(self._receivables)

    @staticmethod
    def _entitlement_key(dist: "EtfDistributionRecord") -> Tuple[str, date, date, str, str, str, str, str]:
        """Full economic-event identity for duplicate detection.

        Distinct distributions may share symbol/ex-date/payable-date (e.g. a
        dividend and a capital gain payable together); identity therefore
        binds event_id (when the source provides one), distribution type,
        and both amounts. Cash settlement remains keyed by (symbol, payable)
        because arriving cash is fungible.
        """
        return (
            dist.symbol,
            dist.ex_date,
            dist.payable_date,
            dist.event_id or "",
            dist.distribution_type,
            str(dist.gross_amount),
            str(dist.net_amount) if dist.net_amount is not None else "",
            dist.share_basis.value,
        )

    def _compute_nav(self, prices: Dict[str, Decimal]) -> Decimal:
        """Total NAV = sum(shares * price) + cash + ex-date receivables."""
        equity_value = sum(
            (self._shares.get(sym, Decimal("0")) * prices[sym])
            for sym in self.target_weights
            if sym in prices
        )
        return equity_value + self._cash + self._receivables_total()

    def _compute_weights(self, prices: Dict[str, Decimal]) -> Dict[str, Decimal]:
        nav = self._compute_nav(prices)
        if nav <= Decimal("0"):
            raise DataContractError("NAV is non-positive; cannot compute weights.")
        return {
            sym: (self._shares.get(sym, Decimal("0")) * prices.get(sym, Decimal("0"))) / nav
            for sym in self.target_weights
        }

    def _floor_shares(self, target_value: Decimal, price: Decimal) -> Decimal:
        if self.allow_fractional_shares:
            return target_value / price
        return (target_value / price).to_integral_value(rounding=ROUND_DOWN)

    def _targets_total_cost(
        self, target_shares: Dict[str, Decimal], prices: Dict[str, Decimal]
    ) -> Decimal:
        """Total cash required to move from current shares to targets (buys only)."""
        total = Decimal("0")
        for sym, target in target_shares.items():
            delta = target - self._shares.get(sym, Decimal("0"))
            if delta > Decimal("0"):
                notional = delta * prices[sym]
                total += notional + self.friction_model.calculate_cost(notional, delta)
        return total

    def _plan_targets(
        self,
        trading_date: date,
        prices: Dict[str, Decimal],
        target_shares: Dict[str, Decimal],
    ) -> List[Tuple[str, Decimal, Decimal, Decimal]]:
        """Side-effect-free rebalance plan: ordered (symbol, delta, notional, friction).

        Sells precede buys in execution order. Funding is simulated over the
        ordered plan: running cash must never go negative at any step and the
        final balance must cover the batch. Any violation fails closed BEFORE
        any state mutation, so a failed rebalance leaves shares, cash,
        receivables, and history exactly untouched (atomicity).
        """
        sells: List[Tuple[str, Decimal, Decimal, Decimal]] = []
        buys: List[Tuple[str, Decimal, Decimal, Decimal]] = []
        for sym in self.target_weights:
            price = prices.get(sym)
            if price is None or price <= Decimal("0"):
                raise DataContractError(
                    f"MISSING_PRICE: Cannot rebalance {sym} on {trading_date}: price={price}"
                )
            delta = target_shares[sym] - self._shares.get(sym, Decimal("0"))
            if delta == Decimal("0"):
                continue
            notional = abs(delta) * price
            friction = self.friction_model.calculate_cost(notional, abs(delta))
            if delta < Decimal("0"):
                sells.append((sym, delta, notional, friction))
            else:
                buys.append((sym, delta, notional, friction))
        running_cash = self._cash
        for sym, delta, notional, friction in sells:
            running_cash += notional - friction
            if running_cash < Decimal("0"):
                raise DataContractError(
                    f"NEGATIVE_CASH_AFTER_SELL: Friction exceeded proceeds for {sym} "
                    f"on {trading_date} (running cash would be {running_cash})."
                )
        for sym, delta, notional, friction in buys:
            running_cash -= notional + friction
            if running_cash < Decimal("0"):
                raise DataContractError(
                    f"INSUFFICIENT_CASH: Cannot buy {delta} shares of {sym} on {trading_date}. "
                    f"Batch needs funding beyond available cash. No implicit borrowing."
                )
        return sells + buys

    def _apply_targets(
        self,
        trading_date: date,
        prices: Dict[str, Decimal],
        target_shares: Dict[str, Decimal],
        reason: str,
    ) -> None:
        """Execute a preflight-validated rebalance plan atomically.

        The plan phase proves funding before any mutation; the commit phase
        below therefore cannot fail financially. Any buy that exceeds
        available cash fails closed (INSUFFICIENT_CASH): no silent borrowing,
        no partial fills, no partially-mutated state.
        """
        actions = self._plan_targets(trading_date, prices, target_shares)
        for sym, delta, notional, friction in actions:
            price = prices[sym]
            if delta < Decimal("0"):
                self._cash += notional - friction
            else:
                self._cash -= notional + friction
            self._shares[sym] = self._shares.get(sym, Decimal("0")) + delta
            self.transactions.append(HoldingsBenchmarkTransaction(
                trading_date=trading_date, symbol=sym, shares_delta=delta,
                price=price, notional=notional, friction_cost=friction, reason=reason,
            ))

    def _execute_rebalance(
        self, trading_date: date, prices: Dict[str, Decimal], reason: str
    ) -> None:
        """Rebalance to target_weights at given prices with explicit friction.

        Targets are sized from pre-trade NAV. If the sized buys exceed cash,
        the rebalance fails closed (INSUFFICIENT_CASH) rather than borrowing:
        a scheduled rebalance that cannot be funded means the schedule is
        infeasible for this capital level.
        """
        nav = self._compute_nav(prices)
        target_shares = {
            sym: self._floor_shares(nav * wt, prices[sym])
            for sym, wt in self.target_weights.items()
        }
        self._apply_targets(trading_date, prices, target_shares, reason)

    def initialize(
        self,
        nav: Decimal,
        prices: Dict[str, Decimal],
        trading_date: date,
    ) -> None:
        """Set initial positions by buying target weights at given prices.

        Whole-share sizing plus explicit friction can exceed starting cash by
        a small residual; in that case the largest position is trimmed one
        whole share at a time (deterministic, bounded) until the buys fit.
        Residual cash after initialization is the whole-share rounding
        remainder. If even one minimum position is unaffordable, fail closed.
        """
        if self._initialized:
            raise DataContractError("HoldingsBasedBenchmark already initialized.")
        ensure_finite_decimal(nav, field_name="nav")
        if nav <= Decimal("0"):
            raise DataContractError(
                f"Initial NAV must be strictly positive, got {nav}."
            )
        for sym in self.target_weights:
            if sym not in prices or prices[sym] <= Decimal("0"):
                raise DataContractError(
                    f"MISSING_PRICE: Cannot initialize {sym} on {trading_date}."
                )
        # A failed initialization must leave no phantom holdings, cash,
        # transactions, or history behind: reset to pristine so the instance
        # stays uninitialized and a corrected retry is safe. (The rebalance
        # plan itself is atomic, so transactions/histories cannot be partial
        # here; only _cash/_shares need resetting.)
        try:
            return self._initialize_inner(nav, prices, trading_date)
        except DataContractError:
            self._cash = Decimal("0")
            self._shares = {}
            raise

    def _initialize_inner(
        self,
        nav: Decimal,
        prices: Dict[str, Decimal],
        trading_date: date,
    ) -> None:
        self._cash = nav
        self._shares = {sym: Decimal("0") for sym in self.target_weights}
        target_shares = {
            sym: self._floor_shares(nav * wt, prices[sym])
            for sym, wt in self.target_weights.items()
        }
        if not self.allow_fractional_shares:
            while self._targets_total_cost(target_shares, prices) > self._cash:
                candidates = [s for s in target_shares if target_shares[s] > Decimal("0")]
                if not candidates:
                    raise DataContractError(
                        "INSUFFICIENT_CASH: starting NAV cannot fund even one minimum "
                        "whole-share position including friction. No implicit borrowing."
                    )
                top = max(candidates, key=lambda s: target_shares[s] * prices[s])
                target_shares[top] -= Decimal("1")
            for sym, wt in self.target_weights.items():
                if wt > Decimal("0") and target_shares[sym] <= Decimal("0"):
                    raise DataContractError(
                        f"INSUFFICIENT_CASH: starting NAV cannot establish any shares of "
                        f"positively-weighted {sym} in whole shares. No silent cash-only "
                        "benchmark for an equity target."
                    )
        self._apply_targets(trading_date, prices, target_shares, reason="INITIAL_ALLOCATION")
        self._initialized = True
        nav_after = self._compute_nav(prices)
        self.nav_history.append(nav_after)
        self.date_history.append(trading_date)
        self.weight_history.append(self._compute_weights(prices))

    def step(
        self,
        trading_date: date,
        prices: Dict[str, Decimal],
        distributions: Optional[List[EtfDistributionRecord]] = None,
        splits: Optional[List[EtfSplitRecord]] = None,
    ) -> Decimal:
        """Advance the benchmark by one trading session (atomic event envelope).

        The session's prices, splits, distributions, and scheduled rebalance
        form ONE atomic unit: every event identity is validated before any
        mutation, and any failure restores all state bit-identically.
        Distribution lifecycle (ex-date entitlement vs payable-date cash):
        on a record's ex-date, book a receivable fixed by the record's
        declared share_basis: POST_SPLIT uses post-split shares (same-session
        splits apply BEFORE entitlements, matching build_total_return_panel()
        where one pre-split share becomes split_ratio post-split shares each
        earning cash_amount); PRE_SPLIT uses pre-split shares. UNKNOWN basis
        with a same-session split fails closed (AMBIGUOUS_SHARE_BASIS) — the
        adapter must declare the basis. Payable-date settlement is driven by the BOOKED LEDGER — every
        receivable whose payable date has arrived settles into cash whether
        or not the record is resupplied — so a data adapter that emits each
        event once cannot strand cash. Amount basis is the record's
        `cash_amount` (net_amount when the owner withholding is known, else
        gross_amount) — so benchmark NAV is investor-net when net is set,
        gross otherwise. Split records must carry this session as ex-date.
        Rebalances only if trading_date is in rebalance_dates.
        Sessions must be strictly increasing (replay fails closed).
        Returns current NAV (equity + cash + outstanding receivables).
        """
        if not self._initialized:
            raise DataContractError("Must call initialize() before step().")
        if self.date_history and trading_date <= self.date_history[-1]:
            raise DataContractError(
                f"REPLAYED_SESSION: {trading_date} is not strictly after last "
                f"processed session {self.date_history[-1]}. Sessions must advance "
                "monotonically; replaying a session would double-count economics."
            )
        for sym in self.target_weights:
            if sym not in prices or prices[sym] <= Decimal("0"):
                raise DataContractError(
                    f"MISSING_PRICE: {sym} price missing or non-positive on {trading_date}."
                )
        # Snapshot for atomicity: any failure below restores every field.
        snap_shares = dict(self._shares)
        snap_cash = self._cash
        snap_receivables = dict(self._receivables)
        snap_booked = set(self._booked_entitlements)
        snap_settled = set(self._settled_payables)
        snap_splits = set(self._applied_splits)
        snap_provider_ids = set(self._booked_provider_event_ids)
        snap_tx_len = len(self.transactions)
        snap_hist_len = len(self.nav_history)
        try:
            # Precompute same-session split factors from the snapshot (pre-split
            # shares stay available for PRE_SPLIT-basis entitlements).
            batch_split_factor: Dict[str, Decimal] = {}
            if splits:
                seen_in_batch: Dict[Tuple[str, date], Decimal] = {}
                for split in splits:
                    self._validate_split(split, trading_date)
                    if split.symbol not in self.target_weights:
                        raise DataContractError(
                            f"UNKNOWN_SPLIT_SYMBOL: {split.symbol} is not a benchmark holding."
                        )
                    if (split.symbol, split.ex_date) in self._applied_splits:
                        raise DataContractError(
                            f"DUPLICATE_SPLIT: {split.symbol} split for ex-date "
                            f"{split.ex_date} already applied."
                        )
                    batch_key = (split.symbol, split.ex_date)
                    if batch_key in seen_in_batch:
                        if seen_in_batch[batch_key] != split.split_ratio:
                            raise DataContractError(
                                f"CONFLICTING_SPLIT: {split.symbol} split for ex-date "
                                f"{split.ex_date} has conflicting ratios in one batch."
                            )
                        raise DataContractError(
                            f"DUPLICATE_SPLIT: {split.symbol} split for ex-date "
                            f"{split.ex_date} appears twice in one batch."
                        )
                    seen_in_batch[batch_key] = split.split_ratio
                for (sym, _), ratio in seen_in_batch.items():
                    batch_split_factor[sym] = (
                        batch_split_factor.get(sym, Decimal("1")) * ratio
                    )
            split_symbols = set(batch_split_factor)
            # Standalone-split boundary: a split for this ex-date applied via
            # the legacy apply_split() primitive (recorded in _applied_splits
            # but absent from this call's batch) leaves no batch factor, so a
            # same-ex-date distribution cannot be basis-validated. Fail closed
            # instead of silently treating it as post-split.
            if distributions and not splits:
                for dist in distributions:
                    if (
                        trading_date == dist.ex_date
                        and (dist.symbol, dist.ex_date) in self._applied_splits
                        and dist.symbol not in split_symbols
                    ):
                        raise DataContractError(
                            f"STANDALONE_SPLIT_BASIS: {dist.symbol} distribution "
                            f"on ex-date {dist.ex_date} follows a standalone "
                            "split outside this step() call. Pass the split "
                            "and distribution to the SAME step() call."
                        )
            if splits:
                for split in splits:
                    self._applied_splits.add((split.symbol, split.ex_date))
                    self._shares[split.symbol] = (
                        self._shares.get(split.symbol, Decimal("0"))
                        * split.split_ratio
                    )
            if distributions:
                for dist in distributions:
                    if dist.symbol not in self.target_weights:
                        continue
                    # Provider revision guard (checked BEFORE ex-date
                    # filtering): same event_id with different economics is
                    # a correction, not a new event — fail closed instead
                    # of double-booking the revised amount, even when the
                    # revision arrives on a later session.
                    provider_key = (
                        (dist.symbol, dist.event_id) if dist.event_id else None
                    )
                    entitlement_key = self._entitlement_key(dist)
                    if (
                        provider_key is not None
                        and provider_key in self._booked_provider_event_ids
                        and entitlement_key not in self._booked_entitlements
                    ):
                        raise DataContractError(
                            f"REVISED_EVENT: {dist.symbol} event_id "
                            f"{dist.event_id} already booked with different "
                            "economics. Provider revisions require adapter "
                            "reconciliation, not silent re-booking."
                        )
                    if trading_date == dist.ex_date:
                        if entitlement_key in self._booked_entitlements:
                            raise DataContractError(
                                f"DUPLICATE_ENTITLEMENT: {dist.symbol} ex-date "
                                f"{dist.ex_date} entitlement already booked."
                            )
                        if (
                            dist.symbol in split_symbols
                            and dist.share_basis == DistributionShareBasis.UNKNOWN
                        ):
                            raise DataContractError(
                                f"AMBIGUOUS_SHARE_BASIS: {dist.symbol} distribution "
                                f"on split ex-date {dist.ex_date} has undeclared "
                                "share_basis. Declare PRE_SPLIT or POST_SPLIT."
                            )
                        if dist.share_basis == DistributionShareBasis.PRE_SPLIT:
                            factor = batch_split_factor.get(
                                dist.symbol, Decimal("1")
                            )
                            shares_basis = self._shares.get(
                                dist.symbol, Decimal("0")
                            ) / factor
                        else:
                            # POST_SPLIT (same-session splits already applied
                            # above) or non-simultaneous legacy records where
                            # the basis is immaterial (factor == 1).
                            shares_basis = self._shares.get(
                                dist.symbol, Decimal("0")
                            )
                        if shares_basis > Decimal("0"):
                            key = (dist.symbol, dist.payable_date)
                            self._receivables[key] = (
                                self._receivables.get(key, Decimal("0"))
                                + shares_basis * dist.cash_amount
                            )
                        self._booked_entitlements.add(entitlement_key)
                        if provider_key is not None:
                            self._booked_provider_event_ids.add(provider_key)
            # Payable-date settlement is ledger-driven: every booked
            # receivable whose payable date has arrived settles into cash,
            # with or without the record being resupplied. Cash is fungible
            # on arrival, so settlement stays keyed by (symbol, payable).
            for key in sorted(
                [k for k in self._receivables if k[1] <= trading_date]
            ):
                self._cash += self._receivables.pop(key)
                self._settled_payables.add(key)

            if trading_date in self.rebalance_dates:
                self._execute_rebalance(trading_date, prices, reason="SCHEDULED_REBALANCE")

            nav = self._compute_nav(prices)
            self.nav_history.append(nav)
            self.date_history.append(trading_date)
            self.weight_history.append(self._compute_weights(prices))
            return nav
        except DataContractError:
            self._shares = snap_shares
            self._cash = snap_cash
            self._receivables = snap_receivables
            self._booked_entitlements = snap_booked
            self._settled_payables = snap_settled
            self._applied_splits = snap_splits
            self._booked_provider_event_ids = snap_provider_ids
            del self.transactions[snap_tx_len:]
            del self.nav_history[snap_hist_len:]
            del self.date_history[snap_hist_len:]
            del self.weight_history[snap_hist_len:]
            raise

    @staticmethod
    def _validate_split(split: "EtfSplitRecord", trading_date: date) -> None:
        """Pure split validation shared by step() staging and apply_split().

        A split applies only to its own ex-date session: silently attaching
        it to an unrelated date is prohibited.
        """
        if split.split_ratio <= Decimal("0"):
            raise DataContractError(
                f"split_ratio must be positive, got {split.split_ratio}"
            )
        if split.ex_date != trading_date:
            raise DataContractError(
                f"WRONG_SPLIT_SESSION: split ex-date {split.ex_date} does not match "
                f"session {trading_date}. Splits apply only on their ex-date."
            )

    def apply_split(self, symbol: str, split_ratio: Decimal, ex_date: date) -> None:
        """Multiply share count by split_ratio for the split ex-date.

        split_ratio = split_to / split_from (e.g., 2.0 for 2:1 split).
        This preserves investment value when the price series reflects post-split prices.
        Unknown symbols fail closed (no silent no-op); applying the same
        (symbol, ex-date) split twice fails closed (no double multiplication).
        Validation precedes mutation, so a rejected split changes nothing.
        Prefer passing splits to step() so the split joins the atomic session
        envelope (a later step() failure cannot strand an applied split).

        WARNING: a standalone split applied outside step() is recorded in
        _applied_splits but NOT in the step() same-session batch factor.
        A same-ex-date distribution passed to a LATER step() call therefore
        fails closed (STANDALONE_SPLIT_BASIS): pass the split and the
        distribution to the SAME step() call so share-basis validation
        applies. This boundary is intentional — standalone splits are a
        legacy primitive, not a same-session corporate-action path.
        """
        if symbol not in self._shares:
            raise DataContractError(
                f"UNKNOWN_SPLIT_SYMBOL: {symbol} is not a benchmark holding."
            )
        ensure_finite_decimal(split_ratio, field_name="split_ratio")
        if split_ratio <= Decimal("0"):
            raise DataContractError(f"split_ratio must be positive, got {split_ratio}")
        split_key = (symbol, ex_date)
        if split_key in self._applied_splits:
            raise DataContractError(
                f"DUPLICATE_SPLIT: {symbol} split for ex-date {ex_date} already applied."
            )
        self._applied_splits.add(split_key)
        self._shares[symbol] = self._shares[symbol] * split_ratio

    def allocation_snapshot(self, prices: Dict[str, Decimal]) -> Dict[str, object]:
        """Read-only disclosure: target vs realized allocation (no mutation).

        A nominal 60/40 target under whole-share constraints realizes as, e.g.,
        ~50/40/10 (assets/cash): this snapshot reports target weights,
        realized asset weights, residual cash weight, cumulative commission
        drag, and maximum absolute weight deviation so no allocation is ever
        reported as exactly invested at target when it is not.
        """
        nav = self._compute_nav(prices)
        if nav <= Decimal("0"):
            raise DataContractError("NAV is non-positive; cannot snapshot allocation.")
        realized = self._compute_weights(prices)
        cumulative_friction = sum((t.friction_cost for t in self.transactions), Decimal("0"))
        max_deviation = max(
            (abs(realized[sym] - self.target_weights[sym]) for sym in self.target_weights),
            default=Decimal("0"),
        )
        return {
            "model_classification": self.model_classification,
            "nav": nav,
            "target_weights": {sym: wt for sym, wt in self.target_weights.items()},
            "realized_weights": dict(realized),
            "residual_cash_weight": self._cash / nav,
            "receivables_weight": self._receivables_total() / nav,
            "cumulative_friction": cumulative_friction,
            "max_abs_weight_deviation": max_deviation,
        }
