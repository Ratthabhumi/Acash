"""Unit tests for Phase 4 Research Baseline Strategy Models."""

from decimal import Decimal
import pytest

from acash.research.strategies import (
    MicrostructureImbalanceStrategy,
    MultiHorizonMomentumStrategy,
    SessionVwapMeanReversionStrategy,
)


def test_microstructure_imbalance_baseline_signals() -> None:
    """Verify Microstructure Imbalance Strategy signal bounds and directional skew."""
    strat = MicrostructureImbalanceStrategy(obi_threshold=Decimal("0.20"))

    obi_vals = [Decimal("0.50"), Decimal("-0.50"), Decimal("0.00")]
    micro_px = [Decimal("5000.50"), Decimal("4999.50"), Decimal("5000.00")]
    mid_px = [Decimal("5000.00"), Decimal("5000.00"), Decimal("5000.00")]

    signals = strat.generate_signals(obi_vals, micro_px, mid_px)
    assert len(signals) == 3
    assert signals[0] > Decimal("0")   # Positive skew + positive OBI -> positive signal
    assert signals[1] < Decimal("0")   # Negative skew + negative OBI -> negative signal
    assert signals[2] == Decimal("0")  # Zero skew + zero OBI -> zero signal


def test_session_vwap_mean_reversion_baseline_signals() -> None:
    """Verify Session VWAP Mean Reversion generates reversion signals on +/- 2 sigma excursions."""
    strat = SessionVwapMeanReversionStrategy(num_std=Decimal("2.0"))

    # VWAP = 5000.00, Std = 2.00 -> Upper Band = 5004.00, Lower Band = 4996.00
    closes = [Decimal("5005.00"), Decimal("4995.00"), Decimal("5001.00")]
    vwaps = [Decimal("5000.00"), Decimal("5000.00"), Decimal("5000.00")]
    stds = [Decimal("2.00"), Decimal("2.00"), Decimal("2.00")]

    signals = strat.generate_signals(closes, vwaps, stds)
    assert signals[0] == Decimal("-1.0")  # Overbought -> Short reversion signal
    assert signals[1] == Decimal("1.0")   # Oversold -> Long reversion signal
    assert signals[2] == Decimal("0.0")   # Within bands -> Neutral signal


def test_multi_horizon_momentum_baseline_signals() -> None:
    """Verify Time-Series Momentum baseline generates trend following signals."""
    strat = MultiHorizonMomentumStrategy(lookback_bars=2)

    # Prices rising: 100 -> 101 -> 102
    closes_up = [Decimal("100.00"), Decimal("101.00"), Decimal("102.00")]
    sigs_up = strat.generate_signals(closes_up)
    assert sigs_up[2] == Decimal("1.0")

    # Prices falling: 100 -> 99 -> 98
    closes_down = [Decimal("100.00"), Decimal("99.00"), Decimal("98.00")]
    sigs_down = strat.generate_signals(closes_down)
    assert sigs_down[2] == Decimal("-1.0")
