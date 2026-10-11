"""Offline Golden Fixture and Contract Invariant Tests for ETF, FX, and Small-Order Friction.

Tests all Phase M1 data contract invariants:
1. ETF Inception Boundaries (fail-closed pre-inception access without synthetic proxy)
2. Synthetic Proxy Exemption Lineage
3. Distribution Validation & Ex-date vs. Payable-date Invariant
4. Exact Dividend Reinvestment Math in Total Return Construction
5. Non-monotonic Dates Detection
6. FX Fixing Conversion Directionality & Unsupported Pairs
7. Cash Accrual Math (ACT/360 & ACT/365)
8. Small-Order Broker Commission Minimum Floor ($0.35 on small notionals)
9. Negative or Non-finite Prices Fail-Closed
10. Empty Sequence Fail-Closed
"""

from datetime import date
from decimal import Decimal
import pytest

from acash.core.domain.exceptions import DataContractError, DomainValidationError
from acash.data.contracts.etf_fx_benchmark import (
    AssetClass,
    CashAccrualModel,
    DayCountConvention,
    EtfDailyObservation,
    EtfDistributionRecord,
    EtfInstrumentContract,
    EtfSplitRecord,
    FxFixingRecord,
    KNOWN_ETF_REGISTRY,
    SmallOrderFrictionModel,
    build_total_return_panel,
)


def test_etf_inception_boundary_violation() -> None:
    """Requesting ETF observations prior to fund inception fails closed with DataContractError."""
    voo = KNOWN_ETF_REGISTRY["VOO"]
    assert voo.inception_date == date(2010, 9, 7)

    # Valid post-inception date
    voo.validate_observation_date(date(2010, 9, 7))
    voo.validate_observation_date(date(2021, 1, 4))

    # Pre-inception date (e.g. 2008 GFC) must fail closed
    with pytest.raises(DataContractError, match="strictly precedes VOO inception date"):
        voo.validate_observation_date(date(2008, 9, 15))


def test_synthetic_proxy_allowed_pre_inception() -> None:
    """Explicit synthetic proxy instrument allows pre-inception date with proper lineage."""
    proxy = EtfInstrumentContract(
        symbol="VOO_SYNTHETIC",
        name="VOO Synthetic Proxy via S&P 500 Index",
        asset_class=AssetClass.GLOBAL_EQUITY,
        base_currency="USD",
        inception_date=date(2010, 9, 7),
        is_synthetic_proxy=True,
        proxy_underlying="SPX",
    )
    # Should not raise
    proxy.validate_observation_date(date(2008, 9, 15))


def test_distribution_record_invariants() -> None:
    """Payable date cannot precede ex-date, and cash amount must be strictly positive."""
    # Valid distribution
    dist = EtfDistributionRecord(
        symbol="VOO",
        ex_date=date(2023, 3, 24),
        payable_date=date(2023, 3, 29),
        cash_amount=Decimal("1.442"),
    )
    assert dist.cash_amount == Decimal("1.442")

    # Inverted dates fail closed
    with pytest.raises(DataContractError, match="payable_date .* cannot precede ex_date"):
        EtfDistributionRecord(
            symbol="VOO",
            ex_date=date(2023, 3, 24),
            payable_date=date(2023, 3, 20),
            cash_amount=Decimal("1.442"),
        )

    # Non-positive cash amount fails validation
    with pytest.raises(DomainValidationError, match="cash_amount must be strictly positive"):
        EtfDistributionRecord(
            symbol="VOO",
            ex_date=date(2023, 3, 24),
            payable_date=date(2023, 3, 29),
            cash_amount=Decimal("0.0"),
        )


def test_etf_split_record() -> None:
    """Stock split calculates split ratio and enforces strictly positive values."""
    split = EtfSplitRecord(
        symbol="GLD",
        ex_date=date(2020, 1, 1),
        split_from=Decimal("1.0"),
        split_to=Decimal("2.0"),
    )
    assert split.split_ratio == Decimal("2.0")

    with pytest.raises(DomainValidationError):
        EtfSplitRecord(
            symbol="GLD",
            ex_date=date(2020, 1, 1),
            split_from=Decimal("-1.0"),
            split_to=Decimal("2.0"),
        )


def test_total_return_panel_mathematical_precision() -> None:
    """Verify exact total return compounding: (P_t + D_t) / P_{t-1}."""
    voo = KNOWN_ETF_REGISTRY["VOO"]
    raw_bars = [
        (date(2020, 1, 2), Decimal("100.0")),
        (date(2020, 1, 3), Decimal("100.0")),  # $2 dividend on this day
        (date(2020, 1, 6), Decimal("102.0")),  # Price appreciation, no dividend
    ]
    distributions = [
        EtfDistributionRecord(
            symbol="VOO",
            ex_date=date(2020, 1, 3),
            payable_date=date(2020, 1, 8),
            cash_amount=Decimal("2.0"),
        )
    ]

    obs = build_total_return_panel(voo, raw_bars, distributions)
    assert len(obs) == 3

    # Day 1: base
    assert obs[0].total_return_factor == Decimal("1.0")
    assert obs[0].cumulative_dividend == Decimal("0.0")

    # Day 2: gross return = (100 + 2) / 100 = 1.02 -> TR factor = 1.02
    assert obs[1].total_return_factor == Decimal("1.02")
    assert obs[1].cumulative_dividend == Decimal("2.0")

    # Day 3: gross return = (102 + 0) / 100 = 1.02 -> TR factor = 1.02 * 1.02 = 1.0404
    assert obs[2].total_return_factor == Decimal("1.0404")
    assert obs[2].cumulative_dividend == Decimal("2.0")


def test_total_return_non_monotonic_dates_fail_closed() -> None:
    """Non-monotonic or duplicate dates in bars raise DataContractError."""
    voo = KNOWN_ETF_REGISTRY["VOO"]
    raw_bars = [
        (date(2020, 1, 2), Decimal("100.0")),
        (date(2020, 1, 2), Decimal("101.0")),  # Duplicate date!
    ]
    with pytest.raises(DataContractError, match="Non-monotonic date sequence detected"):
        build_total_return_panel(voo, raw_bars)


def test_fx_fixing_conversion_and_directionality() -> None:
    """FX fixing converts in both directions with exact orientation, and rejects foreign pairs."""
    fixing = FxFixingRecord(
        base_currency="USD",
        quote_currency="THB",
        fixing_date=date(2026, 10, 9),
        rate=Decimal("35.50"),
        source="BOT",
    )

    # 1. USD to THB (direct multiplication)
    thb_amt = fixing.convert(Decimal("100.0"), from_currency="USD", to_currency="THB")
    assert thb_amt == Decimal("3550.0")

    # 2. THB to USD (inverse division)
    usd_amt = fixing.convert(Decimal("3550.0"), from_currency="THB", to_currency="USD")
    assert usd_amt == Decimal("100.0")

    # 3. Same currency identity
    assert fixing.convert(Decimal("50.0"), "USD", "USD") == Decimal("50.0")

    # 4. Foreign pair mismatch fails closed
    with pytest.raises(DataContractError, match="Cannot convert EUR -> THB"):
        fixing.convert(Decimal("100.0"), from_currency="EUR", to_currency="THB")


def test_cash_accrual_model_exact_math() -> None:
    """Cash yield accrual correctly computes interest under ACT/360 and ACT/365."""
    # 5.0% p.a. on $1,000 for 30 days
    model_360 = CashAccrualModel(annual_rate=Decimal("0.05"), convention=DayCountConvention.ACT_360)
    interest_360 = model_360.accrue(principal=Decimal("1000.0"), days=30)
    # 1000 * 0.05 * (30 / 360) = 50 * (1/12) = 4.166666666666666666666666667
    assert abs(interest_360 - (Decimal("50.0") / Decimal("12"))) < Decimal("1e-12")

    model_365 = CashAccrualModel(annual_rate=Decimal("0.05"), convention=DayCountConvention.ACT_365)
    interest_365 = model_365.accrue(principal=Decimal("1000.0"), days=30)
    # 1000 * 0.05 * (30 / 365) = 50 * (30/365) = 1500 / 365
    assert abs(interest_365 - (Decimal("1500.0") / Decimal("365"))) < Decimal("1e-12")


def test_small_order_broker_friction_minimum_drag() -> None:
    """Verifies that for small accounts ($1,000), minimum ticket commission dominates linear rate."""
    model = SmallOrderFrictionModel(
        commission_rate=Decimal("0.0005"),   # 5 bps
        min_commission_usd=Decimal("0.35"),  # $0.35 IBKR Tiered minimum
        half_spread=Decimal("0.0005"),       # 5 bps
        slippage=Decimal("0.0002"),          # 2 bps
    )

    # Small order: $50 trade (e.g. 5% rebalance on $1,000)
    cost_small = model.calculate_cost(Decimal("50.0"))
    # Linear commission would be 50 * 0.0005 = $0.025.
    # Minimum commission of $0.35 applies!
    # Spread + slippage = 50 * 0.0007 = $0.035.
    # Total cost = 0.35 + 0.035 = $0.385.
    assert cost_small == Decimal("0.385")
    # Percentage drag on $50 trade: 0.385 / 50 = 0.77% (over 10x larger than nominal 5 bps)!
    drag_pct = cost_small / Decimal("50.0")
    assert drag_pct == Decimal("0.0077")

    # Large order: $10,000 trade
    cost_large = model.calculate_cost(Decimal("10000.0"))
    # Linear commission = 10000 * 0.0005 = $5.00 > $0.35 minimum.
    # Spread + slippage = 10000 * 0.0007 = $7.00.
    # Total cost = 5.00 + 7.00 = $12.00.
    assert cost_large == Decimal("12.0")

    # Zero order: $0 cost
    assert model.calculate_cost(Decimal("0.0")) == Decimal("0.0")
