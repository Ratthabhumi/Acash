"""ETF, FX, and Benchmark Data Contracts for Phase M1 Personal Quantitative System.

Strictly enforces:
1. ETF Inception Boundaries: Fail-closed if observations precede fund inception without explicit synthetic proxy designation.
2. Separation of Concerns: Raw execution price != Split-adjusted != Dividend-adjusted != NAV != Total Return.
3. Corporate Actions & Distributions: Ex-date vs. payable-date modeling; dividend double-count prevention.
4. FX Quote Directionality & Valuation: Fail-closed quote orientation checks for cross-currency conversion.
5. Cash / Risk-Free Accrual: Canonical ACT/360 and ACT/365 yield accrual.
6. Broker Friction Model: Enforces minimum commission constraints (e.g. IBKR $0.35/$1.00) critical for small-capital portfolios ($1,000).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from acash.core.domain.exceptions import DataContractError, DomainValidationError
from acash.core.domain.types import ensure_finite_decimal
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


class EtfDistributionRecord(BaseModel):
    """Immutable record of an ETF dividend/capital gain cash distribution."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    ex_date: date
    record_date: Optional[date] = None
    payable_date: date
    cash_amount: Decimal
    distribution_type: str = "DIVIDEND_CASH"

    @field_validator("cash_amount")
    @classmethod
    def validate_cash_amount(cls, v: Decimal) -> Decimal:
        ensure_finite_decimal(v, field_name="cash_amount")
        if v <= Decimal("0"):
            raise DomainValidationError(f"cash_amount must be strictly positive, got {v}")
        return v

    @model_validator(mode="after")
    def validate_dates(self) -> "EtfDistributionRecord":
        if self.payable_date < self.ex_date:
            raise DataContractError(
                f"payable_date ({self.payable_date}) cannot precede ex_date ({self.ex_date})."
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
    """Cost model enforcing broker order minimums and percentage caps critical for small ($1,000) accounts."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    commission_rate: Decimal = Decimal("0.0005")       # 5 bps
    min_commission_usd: Decimal = Decimal("0.35")      # IBKR Tiered minimum $0.35
    max_commission_pct: Decimal = Decimal("0.01")      # IBKR rule: Maximum 1.0% of order value
    half_spread: Decimal = Decimal("0.0005")           # 5 bps
    slippage: Decimal = Decimal("0.0002")              # 2 bps

    def calculate_cost(self, notional_traded: Decimal) -> Decimal:
        """Calculate total transaction friction including minimum commission floor and percentage cap."""
        ensure_finite_decimal(notional_traded, field_name="notional_traded")
        if notional_traded <= Decimal("0"):
            return Decimal("0.0")

        linear_commission = notional_traded * self.commission_rate
        max_cap = notional_traded * self.max_commission_pct
        actual_commission = min(max(linear_commission, self.min_commission_usd), max_cap)
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

    # Index distributions by ex_date
    dist_map: Dict[date, List[Decimal]] = {}
    for d in distributions:
        if d.symbol != instrument.symbol:
            raise DataContractError(f"Distribution symbol {d.symbol} != instrument {instrument.symbol}")
        dist_map.setdefault(d.ex_date, []).append(d.cash_amount)

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
        div_amount_today = sum(divs_today, Decimal("0.0"))
        cum_div += div_amount_today

        split_ratio_today = split_map.get(trading_date, Decimal("1.0"))
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

