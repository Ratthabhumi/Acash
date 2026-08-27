"""Unit tests for Pure Mathematical Microstructure Feature Engine (Phase 3C)."""

from datetime import date, datetime, timezone
from decimal import Decimal
import math
import pyarrow as pa
import pytest

from acash.data.features.engine import (
    calculate_book_microstructure,
    calculate_footprint_analytics,
    calculate_session_vwap_and_dispersion,
    calculate_volume_profile,
    compute_trade_features_table,
)
from acash.data.features.schema import (
    BookFeaturesConfig,
    TradeFeaturesConfig,
)
from acash.data.orderbook.reconstruction import DepthLadderState, PriceLevel
from acash.data.trades.schema import CANONICAL_TRADES_SCHEMA


def test_vwap_and_volume_weighted_dispersion_exact_math() -> None:
    """Verify exact mathematical calculation of VWAP and dispersion against manual calculation.

    Trades:
    1. P = 100.00, Size = 10 -> P*V = 1000
    2. P = 102.00, Size = 30 -> P*V = 3060
    Total V = 40, Total PV = 4060 -> VWAP = 4060 / 40 = 101.50
    Variance = ( (100 - 101.5)^2 * 10 + (102 - 101.5)^2 * 30 ) / 40
             = ( 2.25 * 10 + 0.25 * 30 ) / 40 = ( 22.5 + 7.5 ) / 40 = 30 / 40 = 0.75
    Std = sqrt(0.75) ~= 0.8660254037844386
    """
    trades = [
        (Decimal("100.00"), Decimal("10")),
        (Decimal("102.00"), Decimal("30")),
    ]
    vwap, std_val = calculate_session_vwap_and_dispersion(trades)
    assert vwap == Decimal("101.50")
    assert std_val is not None
    assert math.isclose(float(std_val), math.sqrt(0.75), rel_tol=1e-6)

    # Zero volume handling -> (None, None)
    vwap_z, std_z = calculate_session_vwap_and_dispersion([(Decimal("100.00"), Decimal("0"))])
    assert vwap_z is None
    assert std_z is None


def test_volume_profile_poc_and_value_area_deterministic_rules() -> None:
    """Verify POC tie-breaker, Value Area lower-price-first expansion, and boundary inclusion."""
    # 1. Symmetric Tie-Breaker Case:
    # Prices: 99.00 (vol 30), 100.00 (POC, vol 40), 101.00 (vol 30)
    # Total Vol = 100. Target 70% = 70.
    # POC is 100.00 (vol 40).
    # Adjacent levels: 99.00 (vol 30) vs 101.00 (vol 30) -> Equal volume!
    # Deterministic Tie-Breaker: lower price (99.00) first!
    # Accumulated volume: 40 + 30 = 70 >= 70 (Target reached!).
    # Value Area = [99.00, 100.00] (Boundary 99.00 is included).
    trades_sym = [
        (Decimal("99.00"), Decimal("30")),
        (Decimal("100.00"), Decimal("40")),
        (Decimal("101.00"), Decimal("30")),
    ]
    poc, vah, val = calculate_volume_profile(trades_sym, value_area_pct=Decimal("0.70"))
    assert poc == Decimal("100.00")
    assert val == Decimal("99.00")
    assert vah == Decimal("100.00")

    # 2. POC Tie-Breaker Case:
    # 98.00 (vol 50) and 102.00 (vol 50) share max volume -> POC must be lowest price (98.00)
    trades_poc_tie = [
        (Decimal("102.00"), Decimal("50")),
        (Decimal("98.00"), Decimal("50")),
    ]
    poc_tie, _, _ = calculate_volume_profile(trades_poc_tie)
    assert poc_tie == Decimal("98.00")

    # 3. Zero total volume -> (None, None, None)
    poc_0, vah_0, val_0 = calculate_volume_profile([])
    assert poc_0 is None
    assert vah_0 is None
    assert val_0 is None


def test_footprint_and_diagonal_imbalance_zero_volume_rules() -> None:
    """Verify Buy/Sell Diagonal Imbalances under zero opposing volume and minimum volume diffs."""
    cfg = TradeFeaturesConfig(
        imbalance_ratio=Decimal("3.0"),
        min_imbalance_volume_diff=Decimal("10.0"),
        stacked_imbalance_min_levels=2,
        tick_size=Decimal("0.25"),
    )

    # Trades:
    # P = 5000.00: Sell Volume = 0, Buy Volume = 0
    # P = 5000.25: Buy Volume = 35 (aggressor BUY)
    # Testing Buy Diagonal Imbalance: V_buy(5000.25) vs V_sell(5000.00)
    # V_sell(5000.00) == 0 -> Imbalance True iff V_buy(5000.25) >= min_diff (35 >= 10 -> True)
    trades_diag = [
        {"price": Decimal("5000.25"), "size": Decimal("35"), "aggressor_side": "BUY"},
        {"price": Decimal("5000.50"), "size": Decimal("40"), "aggressor_side": "BUY"},
        {"price": Decimal("5000.00"), "size": Decimal("5"), "aggressor_side": "SELL"},
    ]

    res = calculate_footprint_analytics(trades_diag, cfg)
    assert res["buy_volume"] == Decimal("75")
    assert res["sell_volume"] == Decimal("5")
    assert res["delta"] == Decimal("70")
    assert res["has_stacked_buy_imbalance"]  # 5000.25 and 5000.50 are stacked buy imbalances


def test_book_microstructure_signals_and_zero_depth() -> None:
    """Verify BBO micro-price, Top-N depth-weighted micro-price, OBI, and zero depth handling."""
    cfg = BookFeaturesConfig(use_linear_depth_weights=True)

    # Depth ladder:
    # Bids: Level 0 @ 5000.00 (size 30), Level 1 @ 4999.75 (size 20)
    # Asks: Level 0 @ 5000.50 (size 10), Level 1 @ 5000.75 (size 40)
    ladder = DepthLadderState(
        stream_scope=("CME", "310", "ES.FUT", "2026-01-19"),
        exchange_time_utc=datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc),
        source_order_key="001",
        bids=[
            PriceLevel(price=Decimal("5000.00"), size=Decimal("30")),
            PriceLevel(price=Decimal("4999.75"), size=Decimal("20")),
        ],
        asks=[
            PriceLevel(price=Decimal("5000.50"), size=Decimal("10")),
            PriceLevel(price=Decimal("5000.75"), size=Decimal("40")),
        ],
    )

    micro = calculate_book_microstructure(ladder, cfg)
    assert micro["spread"] == Decimal("0.50")
    # Top-1 OBI = (30 - 10) / (30 + 10) = 20 / 40 = 0.50
    assert micro["obi_top1"] == Decimal("0.50")

    # Linear depth weights:
    # w_bid = 30/1 + 20/2 = 30 + 10 = 40
    # w_ask = 10/1 + 40/2 = 10 + 20 = 30
    # Top-5 Micro-price = (40 * 5000.50 + 30 * 5000.00) / 70 = (200020 + 150000) / 70 = 350020 / 70 = 5000.285714285714285714
    assert micro["micro_price"] is not None
    assert math.isclose(float(micro["micro_price"]), 5000.2857142857, rel_tol=1e-6)

    # Zero depth ladder -> micro_price = None, spread = 0, obi = 0
    empty_ladder = DepthLadderState(
        stream_scope=("CME", "310", "ES.FUT", "2026-01-19"),
        exchange_time_utc=datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc),
        source_order_key="001",
        bids=[],
        asks=[],
    )
    empty_micro = calculate_book_microstructure(empty_ladder, cfg)
    assert empty_micro["micro_price"] is None
    assert empty_micro["spread"] == Decimal("0")
    assert empty_micro["obi_top1"] == Decimal("0")
