"""Hand-Calculated Golden Mathematical Reference Tests for Alpha Research Engine (Phase 4).

Eliminates shared implementation bias by verifying calculations against independently derived manual reference vectors.
"""

from decimal import Decimal
import math
import numpy as np
import pytest

from acash.data.schema import DataContractError, IntegrityViolationError
from acash.research.evaluation import (
    calculate_3tier_friction_waterfall,
    calculate_pearson_ic,
    calculate_spearman_rank_ic,
    compute_ols_beta_and_hac,
    determine_hac_bandwidth,
)
from acash.research.schema import CostModelConfig, HacBandwidthMethod


def test_hand_calculated_ols_slope_and_pearson_ic() -> None:
    """Verify OLS slope beta and Pearson IC against exact manual derivations."""
    x = [Decimal("1.0"), Decimal("2.0"), Decimal("3.0"), Decimal("4.0"), Decimal("5.0")]
    y = [Decimal("2.0"), Decimal("4.0"), Decimal("5.0"), Decimal("4.0"), Decimal("5.0")]

    beta, se, t_stat, p_val = compute_ols_beta_and_hac(x, y, lag_bandwidth=1)

    assert beta == Decimal("0.60")

    expected_se = math.sqrt(0.0272)
    expected_t = 0.60 / expected_se
    expected_p = 2.0 * (1.0 - (1.0 + math.erf(expected_t / math.sqrt(2.0))) / 2.0)

    assert math.isclose(float(se), expected_se, rel_tol=1e-5)
    assert math.isclose(float(t_stat), expected_t, rel_tol=1e-5)
    assert math.isclose(float(p_val), expected_p, rel_tol=1e-4)

    p_ic = calculate_pearson_ic(x, y)
    assert p_ic is not None
    assert math.isclose(float(p_ic), 6.0 / math.sqrt(60.0), rel_tol=1e-6)


def test_hand_calculated_spearman_rank_ic_with_fractional_ties() -> None:
    """Verify Spearman Rank IC with fractional tie handling against manual derivation."""
    x = [Decimal("1.0"), Decimal("2.0"), Decimal("3.0"), Decimal("4.0"), Decimal("5.0")]
    y = [Decimal("2.0"), Decimal("4.0"), Decimal("5.0"), Decimal("4.0"), Decimal("5.0")]

    r_ic = calculate_spearman_rank_ic(x, y)
    assert r_ic is not None

    expected_corr = 7.0 / math.sqrt(90.0)
    assert math.isclose(float(r_ic), expected_corr, rel_tol=1e-6)


def test_hand_calculated_3tier_friction_waterfall() -> None:
    """Verify 3-tier friction deductions and basis point conversions."""
    fwd_ret = [Decimal("0.0010"), Decimal("0.0020")]
    signals = [Decimal("1.0"), Decimal("1.0")]
    cfg = CostModelConfig(
        quoted_spread_bps=Decimal("2.0"),
        roundtrip_broker_fee_bps=Decimal("1.0"),
        fixed_slippage_bps=Decimal("0.5"),
    )

    t1, t2, t3 = calculate_3tier_friction_waterfall(fwd_ret, signals, cfg)
    assert t1 == Decimal("15.0")
    assert t2 == Decimal("12.0")
    assert t3 == Decimal("11.5")


def test_hand_calculated_andrews_ar1_and_newey_west_bandwidths() -> None:
    """Verify Andrews (1991, Econometrica 59(3)) AR(1) plug-in and Newey-West (1994) against exact manual hand-derived literals."""
    # 1. Newey-West rule-of-thumb: floor(4 * (T / 100)^(2/9))
    assert determine_hac_bandwidth(HacBandwidthMethod.NEWEY_WEST_PLUGIN, sample_size=1000, horizon=5) == 6
    assert determine_hac_bandwidth(HacBandwidthMethod.NEWEY_WEST_PLUGIN, sample_size=250, horizon=5) == 4

    # 2. Andrews (1991) AR(1) Bartlett kernel plug-in:
    np.random.seed(42)
    e = np.random.normal(0, 1, 1000)
    score_proc_1 = np.zeros(1000)
    for t in range(1, 1000):
        score_proc_1[t] = 0.50 * score_proc_1[t - 1] + e[t]

    andrews_bw_1 = determine_hac_bandwidth(
        HacBandwidthMethod.ANDREWS_AR1_PLUGIN,
        sample_size=1000,
        horizon=5,
        score_process=score_proc_1,
    )
    assert andrews_bw_1 in (13, 14)  # Exact external analytical range across floating point implementations

    # Hand-derived Golden Benchmark Vector 2:
    # Zero autocorrelation score process (rho = 0.0) -> alpha(1) = 0.0 -> returns 0
    zero_score_proc = np.array([1.0, 0.0, -1.0, 0.0, 1.0, 0.0, -1.0, 0.0])
    andrews_bw_zero = determine_hac_bandwidth(
        HacBandwidthMethod.ANDREWS_AR1_PLUGIN,
        sample_size=8,
        horizon=5,
        score_process=zero_score_proc,
    )
    assert andrews_bw_zero == 0



def test_empty_orderbook_and_trades_tables_validate_canonical_schema() -> None:
    """Verify that empty tables with malformed schemas fail-fast rather than silently returning success."""
    from acash.data.orderbook.pipeline import OrderBookIngestionPipeline
    from acash.data.trades.pipeline import TradesIngestionPipeline
    import pyarrow as pa

    ob_pipeline = OrderBookIngestionPipeline()
    trades_pipeline = TradesIngestionPipeline()

    bad_empty_table = pa.Table.from_pydict({"invalid_col_a": [], "invalid_col_b": []})

    with pytest.raises((IntegrityViolationError, DataContractError)):
        ob_pipeline.ingest_snapshots(raw_table=bad_empty_table, source_id="binance", source_uri="file://test")

    with pytest.raises((IntegrityViolationError, DataContractError)):
        ob_pipeline.ingest_deltas(raw_table=bad_empty_table, source_id="binance", source_uri="file://test")

    with pytest.raises((IntegrityViolationError, DataContractError)):
        trades_pipeline.ingest(raw_table=bad_empty_table, source_id="binance", source_uri="file://test")


def test_phase2_validator_rejects_duplicate_revision_identities_before_hashing() -> None:
    """Verify that rows with identical revision identities are rejected by validator before hashing."""
    from acash.data.integrity import DataIntegrityValidator
    from acash.data.schema import CANONICAL_ARROW_SCHEMA
    from datetime import datetime, timezone
    import pyarrow as pa

    validator = DataIntegrityValidator()
    t_event = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    t_end = datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc)
    t_know = datetime(2026, 1, 1, 10, 2, tzinfo=timezone.utc)

    data = {
        "source_id": ["binance", "binance"],
        "symbol": ["BTC/USDT", "BTC/USDT"],
        "timeframe": ["M1", "M1"],
        "event_start_utc": [t_event, t_event],
        "event_end_utc": [t_end, t_end],
        "knowledge_time_utc": [t_know, t_know],
        "revision_seq": [1, 1],  # Duplicate revision sequence within same event
        "open": [Decimal("100.00"), Decimal("105.00")],
        "high": [Decimal("105.00"), Decimal("110.00")],
        "low": [Decimal("95.00"), Decimal("100.00")],
        "close": [Decimal("102.00"), Decimal("108.00")],
        "volume": [Decimal("10.0"), Decimal("12.0")],
        "quote_volume": [Decimal("1010.0"), Decimal("1200.0")],
        "trade_count": [50, 60],
    }
    table = pa.Table.from_pydict(data, schema=CANONICAL_ARROW_SCHEMA)
    report, _ = validator.validate_table(table)

    assert report.is_valid is False
    assert any("DUPLICATE" in err.rule for err in report.errors)
