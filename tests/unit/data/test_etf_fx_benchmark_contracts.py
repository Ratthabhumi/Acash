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
    DistributionTaxClassification,
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
    """Payable date cannot precede ex-date, and gross amount must be strictly positive."""
    # Valid distribution (gross basis)
    dist = EtfDistributionRecord(
        symbol="VOO",
        ex_date=date(2023, 3, 24),
        payable_date=date(2023, 3, 29),
        gross_amount=Decimal("1.442"),
    )
    assert dist.gross_amount == Decimal("1.442")
    assert dist.net_amount is None
    assert dist.cash_amount == Decimal("1.442")

    # Inverted dates fail closed
    with pytest.raises(DataContractError, match="payable_date .* cannot precede ex_date"):
        EtfDistributionRecord(
            symbol="VOO",
            ex_date=date(2023, 3, 24),
            payable_date=date(2023, 3, 20),
            gross_amount=Decimal("1.442"),
        )

    # Non-positive gross amount fails validation
    with pytest.raises(DomainValidationError, match="gross_amount must be strictly positive"):
        EtfDistributionRecord(
            symbol="VOO",
            ex_date=date(2023, 3, 24),
            payable_date=date(2023, 3, 29),
            gross_amount=Decimal("0.0"),
        )


def test_distribution_gross_net_separation_no_universal_withholding() -> None:
    """Gross is issuer-reported; net requires an explicit owner rate. No universal 15%."""
    # Gross-only record: no withholding assumed, cash basis stays gross.
    gross_only = EtfDistributionRecord(
        symbol="BND",
        ex_date=date(2023, 3, 24),
        payable_date=date(2023, 3, 29),
        gross_amount=Decimal("0.50"),
    )
    assert gross_only.tax_classification.value == "GROSS_BEFORE_WITHHOLDING"
    assert gross_only.cash_amount == Decimal("0.50")

    # Explicit owner rate (15% DTA example): net must be computed and consistent.
    netted = EtfDistributionRecord(
        symbol="BND",
        ex_date=date(2023, 3, 24),
        payable_date=date(2023, 3, 29),
        gross_amount=Decimal("0.50"),
        net_amount=Decimal("0.425"),
        withholding_rate=Decimal("0.15"),
        tax_classification=DistributionTaxClassification.NET_AFTER_WITHHOLDING,
    )
    assert netted.cash_amount == Decimal("0.425")

    # Net exceeding gross is impossible: fail closed.
    with pytest.raises(DataContractError, match="cannot exceed gross_amount"):
        EtfDistributionRecord(
            symbol="BND",
            ex_date=date(2023, 3, 24),
            payable_date=date(2023, 3, 29),
            gross_amount=Decimal("0.50"),
            net_amount=Decimal("0.60"),
            withholding_rate=Decimal("0.15"),
        )

    # A withholding rate without a computed net amount is ambiguous: fail closed.
    with pytest.raises(DataContractError, match="withholding_rate is set but net_amount is None"):
        EtfDistributionRecord(
            symbol="BND",
            ex_date=date(2023, 3, 24),
            payable_date=date(2023, 3, 29),
            gross_amount=Decimal("0.50"),
            withholding_rate=Decimal("0.15"),
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
            gross_amount=Decimal("2.0"),
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
    """IBKR Tiered per-share commission: $0.0035/share, $0.35 minimum, 1% cap.

    Classification must stay IBKR_INSPIRED_SYNTHETIC_FRICTION (never presented
    as account-verified fees). Whole-share basis; fractional terms unmodeled.
    """
    from acash.data.contracts.etf_fx_benchmark import IBKR_COST_MODEL_CLASSIFICATION

    model = SmallOrderFrictionModel()
    assert model.pricing_schedule == "IBKR_TIERED_US_SYNTHETIC"
    assert model.share_quantity_basis == "WHOLE_SHARE"
    assert IBKR_COST_MODEL_CLASSIFICATION == "IBKR_INSPIRED_SYNTHETIC_FRICTION"

    # Small order: 1 share @ $50 (e.g. 5% rebalance on $1,000).
    # Per-share commission = 1 * 0.0035 = $0.0035 -> $0.35 minimum applies.
    # Spread + slippage = 50 * 0.0007 = $0.035. Total = $0.385.
    cost_small = model.calculate_cost(Decimal("50.0"), Decimal("1"))
    assert cost_small == Decimal("0.385")
    # Percentage drag on $50 trade: 0.385 / 50 = 0.77%.
    drag_pct = cost_small / Decimal("50.0")
    assert drag_pct == Decimal("0.0077")

    # Large per-share-driven order: 2000 shares @ $5 = $10,000.
    # Per-share commission = 2000 * 0.0035 = $7.00 (cap 1% = $100 does not bind).
    # Spread + slippage = 10000 * 0.0007 = $7.00. Total = $14.00.
    cost_large = model.calculate_cost(Decimal("10000.0"), Decimal("2000"))
    assert cost_large == Decimal("14.0")

    # Cap binds: 1000 shares @ $0.20 = $200 notional.
    # Per-share = 1000 * 0.0035 = $3.50, capped at 1% of $200 = $2.00.
    # Spread + slippage = 200 * 0.0007 = $0.14. Total = $2.14.
    cost_capped = model.calculate_cost(Decimal("200.0"), Decimal("1000"))
    assert cost_capped == Decimal("2.14")

    # Micro order: 1 share @ $10 (cap $0.10 binds below the $0.35 minimum).
    # Spread + slippage = 10 * 0.0007 = $0.007. Total = $0.107.
    cost_micro = model.calculate_cost(Decimal("10.0"), Decimal("1"))
    assert cost_micro == Decimal("0.107")

    # Zero order: $0 cost.
    assert model.calculate_cost(Decimal("0.0"), Decimal("0")) == Decimal("0.0")

    # Positive notional with zero shares is inconsistent under WHOLE_SHARE basis.
    with pytest.raises(DataContractError, match="zero shares is inconsistent"):
        model.calculate_cost(Decimal("50.0"), Decimal("0"))


def test_fractional_shares_rejected_under_whole_share_tariff() -> None:
    """Fractional quantities must not silently pass through the whole-share tariff.

    IBKR prices fractional trades under separate terms (documented but
    unmodeled); this model fails closed instead of mispricing them.
    """
    model = SmallOrderFrictionModel()
    with pytest.raises(DataContractError, match="FRACTIONAL_SHARES_UNSUPPORTED"):
        model.calculate_cost(Decimal("50.0"), Decimal("0.5"))
    # Integral values expressed with a decimal point still pass.
    assert model.calculate_cost(Decimal("50.0"), Decimal("1.0")) == Decimal("0.385")


def test_total_return_panel_declares_its_amount_basis() -> None:
    """TR panels use gross when net is absent and net when the owner set it.

    Issuer gross total return and owner-specific after-tax NAV stay reported
    separately via the record fields; the panel never blends them silently.
    """
    voo = KNOWN_ETF_REGISTRY["VOO"]
    raw_bars = [
        (date(2020, 1, 2), Decimal("100.0")),
        (date(2020, 1, 3), Decimal("99.0")),
    ]
    gross_panel = build_total_return_panel(
        voo,
        raw_bars,
        distributions=[
            EtfDistributionRecord(
                symbol="VOO",
                ex_date=date(2020, 1, 3),
                payable_date=date(2020, 1, 8),
                gross_amount=Decimal("1.0"),
            )
        ],
    )
    net_panel = build_total_return_panel(
        voo,
        raw_bars,
        distributions=[
            EtfDistributionRecord(
                symbol="VOO",
                ex_date=date(2020, 1, 3),
                payable_date=date(2020, 1, 8),
                gross_amount=Decimal("1.0"),
                net_amount=Decimal("0.85"),
                withholding_rate=Decimal("0.15"),
            )
        ],
    )
    # Gross basis: (99 + 1.0) / 100 = 1.00. Net basis: (99 + 0.85) / 100 = 0.9985.
    assert gross_panel[1].total_return_factor == Decimal("1.00")
    assert net_panel[1].total_return_factor == Decimal("0.9985")
    assert gross_panel[1].total_return_factor != net_panel[1].total_return_factor


def test_split_regression_2_for_1_zero_economic_loss() -> None:
    """A 2-for-1 split drops price from 100 to 50 with zero economic loss (return == 0.0)."""
    gld = KNOWN_ETF_REGISTRY["GLD"]
    raw_bars = [
        (date(2020, 1, 2), Decimal("100.0")),
        (date(2020, 1, 3), Decimal("50.0")),  # Price halved due to 2:1 split
    ]
    splits = [
        EtfSplitRecord(
            symbol="GLD",
            ex_date=date(2020, 1, 3),
            split_from=Decimal("1.0"),
            split_to=Decimal("2.0"),
        )
    ]

    obs = build_total_return_panel(gld, raw_bars, splits=splits)
    assert len(obs) == 2
    # Day 1: base TR = 1.0
    assert obs[0].total_return_factor == Decimal("1.0")
    assert obs[0].split_factor == Decimal("1.0")

    # Day 2: split factor = 2.0, total return factor must remain 1.0 (0.0% return)
    assert obs[1].split_factor == Decimal("2.0")
    assert obs[1].total_return_factor == Decimal("1.0")


def test_simultaneous_split_and_dividend_exact_math() -> None:
    """Simultaneous 2:1 split and $1.00 dividend on ex-date calculates correct compounding."""
    voo = KNOWN_ETF_REGISTRY["VOO"]
    raw_bars = [
        (date(2020, 1, 2), Decimal("100.0")),
        (date(2020, 1, 3), Decimal("50.0")),  # Split 2:1 and pays $1.00 dividend
    ]
    splits = [
        EtfSplitRecord(
            symbol="VOO",
            ex_date=date(2020, 1, 3),
            split_from=Decimal("1.0"),
            split_to=Decimal("2.0"),
        )
    ]
    distributions = [
        EtfDistributionRecord(
            symbol="VOO",
            ex_date=date(2020, 1, 3),
            payable_date=date(2020, 1, 8),
            gross_amount=Decimal("1.0"),
        )
    ]

    obs = build_total_return_panel(voo, raw_bars, distributions=distributions, splits=splits)
    assert len(obs) == 2
    # Holding 1 share at $100 becomes 2 shares at $50 = $100 + 2 * $1 dividend = $102
    # Gross return = 2.0 * (50 + 1) / 100 = 102 / 100 = 1.02 (+2.0%)
    assert obs[1].total_return_factor == Decimal("1.02")
    assert obs[1].cumulative_dividend == Decimal("1.0")
    assert obs[1].split_factor == Decimal("2.0")


def test_fractional_split_3_for_2() -> None:
    """A 3-for-2 split (ratio 1.5) preserves economic value accurately."""
    bnd = KNOWN_ETF_REGISTRY["BND"]
    raw_bars = [
        (date(2020, 1, 2), Decimal("90.0")),
        (date(2020, 1, 3), Decimal("60.0")),  # 90 / 1.5 = 60
    ]
    splits = [
        EtfSplitRecord(
            symbol="BND",
            ex_date=date(2020, 1, 3),
            split_from=Decimal("2.0"),
            split_to=Decimal("3.0"),
        )
    ]

    obs = build_total_return_panel(bnd, raw_bars, splits=splits)
    assert len(obs) == 2
    assert obs[1].total_return_factor == Decimal("1.0")
    assert obs[1].split_factor == Decimal("1.5")


def test_double_counting_guards_fail_closed() -> None:
    """Applying corporate actions to already-adjusted series raises DataContractError fail-closed."""
    from acash.data.contracts.etf_fx_benchmark import PriceBasis

    voo = KNOWN_ETF_REGISTRY["VOO"]
    raw_bars = [(date(2020, 1, 2), Decimal("100.0")), (date(2020, 1, 3), Decimal("101.0"))]
    dists = [
        EtfDistributionRecord(
            symbol="VOO",
            ex_date=date(2020, 1, 3),
            payable_date=date(2020, 1, 8),
            gross_amount=Decimal("1.0"),
        )
    ]
    splits = [
        EtfSplitRecord(
            symbol="VOO",
            ex_date=date(2020, 1, 3),
            split_from=Decimal("1.0"),
            split_to=Decimal("2.0"),
        )
    ]

    # Cannot apply distributions to TOTAL_RETURN_ADJUSTED_PRICE
    with pytest.raises(DataContractError, match="cannot apply cash distributions to a TOTAL_RETURN_ADJUSTED_PRICE"):
        build_total_return_panel(
            voo, raw_bars, distributions=dists, price_basis=PriceBasis.TOTAL_RETURN_ADJUSTED_PRICE
        )

    # Cannot apply splits to SPLIT_ADJUSTED_PRICE
    with pytest.raises(DataContractError, match="cannot apply splits to a SPLIT_ADJUSTED_PRICE"):
        build_total_return_panel(
            voo, raw_bars, splits=splits, price_basis=PriceBasis.SPLIT_ADJUSTED_PRICE
        )

    # Cannot apply distributions to DIVIDEND_ADJUSTED_PRICE
    with pytest.raises(DataContractError, match="cannot apply cash distributions to a DIVIDEND_ADJUSTED_PRICE"):
        build_total_return_panel(
            voo, raw_bars, distributions=dists, price_basis=PriceBasis.DIVIDEND_ADJUSTED_PRICE
        )

