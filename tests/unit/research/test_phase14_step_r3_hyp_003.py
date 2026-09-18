"""Unit & Invariant Tests for Phase 14 Step R3 In-Sample Census (HYP_003).

Test Coverage:
1. R2 dataset hash verification
2. OOS hard rejection
3. K=4 exact census
4. 5m OR construction
5. 15m OR construction
6. close-through signal semantics
7. wick-only no-signal
8. next-bar-open entry
9. last-bar signal -> no trade
10. fixed opposite-boundary stop
11. conservative stop fill
12. EOD 15:59 exit
13. long slippage direction
14. short slippage direction
15. transaction-cost application
16. maximum one trade/cell/session
17. no re-entry
18. independent LONG/SHORT cells
19. incomplete sessions cannot enter R3
20. deterministic result hashes
"""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.step_r3_hyp_003 import (
    EXPECTED_CANONICAL_DATASET_SHA256,
    EXPECTED_QUALIFIED_SESSIONS,
    FROZEN_SLIPPAGE_PER_SIDE,
    FROZEN_TRANSACTION_COST_PER_SIDE,
    OOS_SEALED_BOUNDARY_DATE,
    PRIMARY_ORB_CELLS,
    REGULAR_SESSION_BAR_COUNT,
    OrbBar,
    OrbCellConfig,
    assert_is_boundary,
    execute_cell_census,
    load_and_validate_canonical_r2_dataset,
    simulate_orb_session,
    validate_r3_preconditions,
)


def _create_synthetic_390_bars(
    session_date: date,
    base_price: Decimal = Decimal("100.00"),
) -> list[OrbBar]:
    """Helper to generate a clean synthetic 390-bar regular session."""
    bars: list[OrbBar] = []
    # 09:30 ET = 14:30 UTC standard
    start_utc = datetime.combine(session_date, time(14, 30), tzinfo=timezone.utc)
    for i in range(REGULAR_SESSION_BAR_COUNT):
        ts = start_utc + timedelta(minutes=i)
        # For opening range bars (first 5 bars), establish [99.50, 100.50]
        if i < 5:
            h = base_price + Decimal("0.50")
            l = base_price - Decimal("0.50")
        else:
            # Post-OR bars default to staying inside [99.80, 100.20] unless modified
            h = base_price + Decimal("0.20")
            l = base_price - Decimal("0.20")
        bars.append(
            OrbBar(
                event_start_utc=ts,
                open=base_price,
                high=h,
                low=l,
                close=base_price,
                volume=Decimal("1000"),
            )
        )
    return bars



def test_gate1_r2_dataset_hash_verification() -> None:
    """Gate 1: Preconditions verify R2 dataset and lineage hashes."""
    preconditions = validate_r3_preconditions()
    assert preconditions["hypothesis_sha256"]
    assert preconditions["preregistration_sha256"]
    assert preconditions["r1_manifest_sha256"]
    assert Path(preconditions["parquet_path"]).exists()


def test_gate2_oos_hard_rejection() -> None:
    """Gate 2: Any date >= 2023-01-01 immediately aborts with DataContractError."""
    with pytest.raises(DataContractError, match="OOS HARD BOUNDARY VIOLATION"):
        assert_is_boundary(date(2023, 1, 1))

    with pytest.raises(DataContractError, match="OOS HARD BOUNDARY VIOLATION"):
        assert_is_boundary(date(2024, 6, 15))


def test_gate3_k4_exact_census() -> None:
    """Gate 3: Primary cell configuration is exactly K=4."""
    assert len(PRIMARY_ORB_CELLS) == 4
    cell_ids = tuple(c.cell_id for c in PRIMARY_ORB_CELLS)
    assert cell_ids == ("ORB_5M_LONG", "ORB_5M_SHORT", "ORB_15M_LONG", "ORB_15M_SHORT")


def test_gate4_5m_or_construction() -> None:
    """Gate 4: 5m opening range uses exactly bars 0 to 4."""
    d = date(2020, 1, 6)
    bars = _create_synthetic_390_bars(d, base_price=Decimal("100.00"))
    # Modify bar 2 to have higher high and bar 3 to have lower low
    bars[2] = OrbBar(
        event_start_utc=bars[2].event_start_utc,
        open=Decimal("100"),
        high=Decimal("105.00"),
        low=Decimal("99.00"),
        close=Decimal("101.00"),
        volume=Decimal("1000"),
    )
    bars[3] = OrbBar(
        event_start_utc=bars[3].event_start_utc,
        open=Decimal("100"),
        high=Decimal("102.00"),
        low=Decimal("94.00"),
        close=Decimal("99.00"),
        volume=Decimal("1000"),
    )
    # Breakout at bar 5 (09:35)
    bars[5] = OrbBar(
        event_start_utc=bars[5].event_start_utc,
        open=Decimal("102"),
        high=Decimal("106.00"),
        low=Decimal("101.00"),
        close=Decimal("105.50"),  # > 105.00
        volume=Decimal("1000"),
    )
    config = OrbCellConfig(cell_id="ORB_5M_LONG", window_minutes=5, direction="LONG")
    res = simulate_orb_session(d, bars, config)
    assert res.had_signal is True
    assert res.trade is not None
    assert res.trade.signal_bar_index == 5
    # Entry at bar 6
    assert res.trade.entry_bar_index == 6


def test_gate5_15m_or_construction() -> None:
    """Gate 5: 15m opening range uses exactly bars 0 to 14."""
    d = date(2020, 1, 6)
    bars = _create_synthetic_390_bars(d, base_price=Decimal("100.00"))
    # Bar 5 has high 105. In 5m cell it would break, but in 15m cell it's inside the OR
    bars[5] = OrbBar(
        event_start_utc=bars[5].event_start_utc,
        open=Decimal("100"),
        high=Decimal("105.00"),
        low=Decimal("99.00"),
        close=Decimal("101.00"),
        volume=Decimal("1000"),
    )
    # Breakout at bar 15 (09:45)
    bars[15] = OrbBar(
        event_start_utc=bars[15].event_start_utc,
        open=Decimal("101"),
        high=Decimal("106.00"),
        low=Decimal("100.00"),
        close=Decimal("105.50"),  # > 105.00
        volume=Decimal("1000"),
    )
    config = OrbCellConfig(cell_id="ORB_15M_LONG", window_minutes=15, direction="LONG")
    res = simulate_orb_session(d, bars, config)
    assert res.had_signal is True
    assert res.trade is not None
    assert res.trade.signal_bar_index == 15
    assert res.trade.entry_bar_index == 16


def test_gate6_close_through_signal_semantics() -> None:
    """Gate 6: Breakout requires Close > OR_high (Long) or Close < OR_low (Short)."""
    d = date(2020, 1, 6)
    bars = _create_synthetic_390_bars(d, base_price=Decimal("100.00"))
    # OR high = 100.50
    # Bar 5 close = 100.51 -> breakout!
    bars[5] = OrbBar(
        event_start_utc=bars[5].event_start_utc,
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100.51"),
        volume=Decimal("1000"),
    )
    config = OrbCellConfig(cell_id="ORB_5M_LONG", window_minutes=5, direction="LONG")
    res = simulate_orb_session(d, bars, config)
    assert res.had_signal is True


def test_gate7_wick_only_no_signal() -> None:
    """Gate 7: High touches/crosses OR_high but Close <= OR_high produces NO signal."""
    d = date(2020, 1, 6)
    bars = _create_synthetic_390_bars(d, base_price=Decimal("100.00"))
    # OR high = 100.50
    # Bar 5 has high 102.00, but close = 100.40
    bars[5] = OrbBar(
        event_start_utc=bars[5].event_start_utc,
        open=Decimal("100"),
        high=Decimal("102.00"),
        low=Decimal("99"),
        close=Decimal("100.40"),
        volume=Decimal("1000"),
    )
    config = OrbCellConfig(cell_id="ORB_5M_LONG", window_minutes=5, direction="LONG")
    res = simulate_orb_session(d, bars, config)
    assert res.had_signal is False
    assert res.had_trade is False


def test_gate8_next_bar_open_entry() -> None:
    """Gate 8: Entry is strictly at bar t+1 Open (zero same-bar execution)."""
    d = date(2020, 1, 6)
    bars = _create_synthetic_390_bars(d, base_price=Decimal("100.00"))
    # Signal at bar 10
    bars[10] = OrbBar(
        event_start_utc=bars[10].event_start_utc,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("100"),
        close=Decimal("101.50"),
        volume=Decimal("1000"),
    )
    # Entry at bar 11 with Open = 101.80
    bars[11] = OrbBar(
        event_start_utc=bars[11].event_start_utc,
        open=Decimal("101.80"),
        high=Decimal("102.00"),
        low=Decimal("101.00"),
        close=Decimal("101.50"),
        volume=Decimal("1000"),
    )
    config = OrbCellConfig(cell_id="ORB_5M_LONG", window_minutes=5, direction="LONG")
    res = simulate_orb_session(d, bars, config)
    assert res.trade is not None
    assert res.trade.entry_bar_index == 11
    assert res.trade.observable_entry_price == Decimal("101.80")


def test_gate9_last_bar_signal_no_trade() -> None:
    """Gate 9: If breakout occurs on bar 389 (15:59), no next bar exists -> no trade."""
    d = date(2020, 1, 6)
    bars = _create_synthetic_390_bars(d, base_price=Decimal("100.00"))
    # Signal on bar 389
    bars[389] = OrbBar(
        event_start_utc=bars[389].event_start_utc,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("100"),
        close=Decimal("101.50"),
        volume=Decimal("1000"),
    )
    config = OrbCellConfig(cell_id="ORB_5M_LONG", window_minutes=5, direction="LONG")
    res = simulate_orb_session(d, bars, config)
    assert res.had_signal is True
    assert res.had_trade is False
    assert res.trade is None


def test_gate10_fixed_opposite_boundary_stop() -> None:
    """Gate 10: Long stop is fixed at OR_low; Short stop is fixed at OR_high."""
    d = date(2020, 1, 6)
    bars = _create_synthetic_390_bars(d, base_price=Decimal("100.00"))
    # OR low = 99.50, OR high = 100.50
    # Long breakout at bar 5, entry at bar 6
    bars[5] = OrbBar(
        event_start_utc=bars[5].event_start_utc,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("100"),
        close=Decimal("101.50"),
        volume=Decimal("1000"),
    )
    # Stop hit at bar 20: low drops to 99.00 <= 99.50
    bars[20] = OrbBar(
        event_start_utc=bars[20].event_start_utc,
        open=Decimal("100"),
        high=Decimal("100.20"),
        low=Decimal("99.00"),
        close=Decimal("99.20"),
        volume=Decimal("1000"),
    )
    config = OrbCellConfig(cell_id="ORB_5M_LONG", window_minutes=5, direction="LONG")
    res = simulate_orb_session(d, bars, config)
    assert res.trade is not None
    assert res.trade.exit_reason == "STOP_LOSS"
    assert res.trade.exit_bar_index == 20


def test_gate11_conservative_stop_fill() -> None:
    """Gate 11: Long stop fill uses min(stop, open, low); Short uses max(stop, open, high)."""
    d = date(2020, 1, 6)
    bars = _create_synthetic_390_bars(d, base_price=Decimal("100.00"))
    # OR_low = 99.50
    bars[5] = OrbBar(
        event_start_utc=bars[5].event_start_utc,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("100"),
        close=Decimal("101.50"),
        volume=Decimal("1000"),
    )
    # Gapped down below stop at bar 7: Open = 98.00, Low = 97.00
    bars[7] = OrbBar(
        event_start_utc=bars[7].event_start_utc,
        open=Decimal("98.00"),
        high=Decimal("98.50"),
        low=Decimal("97.00"),
        close=Decimal("97.50"),
        volume=Decimal("1000"),
    )
    config = OrbCellConfig(cell_id="ORB_5M_LONG", window_minutes=5, direction="LONG")
    res = simulate_orb_session(d, bars, config)
    assert res.trade is not None
    assert res.trade.exit_reason == "STOP_LOSS"
    # min(99.50, 98.00, 97.00) = 97.00
    assert res.trade.observable_exit_price == Decimal("97.00")


def test_gate12_eod_1559_exit() -> None:
    """Gate 12: If stop not hit, trade exits at bar 389 (15:59) Close."""
    d = date(2020, 1, 6)
    bars = _create_synthetic_390_bars(d, base_price=Decimal("100.00"))
    bars[5] = OrbBar(
        event_start_utc=bars[5].event_start_utc,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("100"),
        close=Decimal("101.50"),
        volume=Decimal("1000"),
    )
    bars[389] = OrbBar(
        event_start_utc=bars[389].event_start_utc,
        open=Decimal("103"),
        high=Decimal("104"),
        low=Decimal("102.50"),
        close=Decimal("103.50"),
        volume=Decimal("1000"),
    )
    config = OrbCellConfig(cell_id="ORB_5M_LONG", window_minutes=5, direction="LONG")
    res = simulate_orb_session(d, bars, config)
    assert res.trade is not None
    assert res.trade.exit_reason == "EOD_FLATTEN"
    assert res.trade.exit_bar_index == 389
    assert res.trade.observable_exit_price == Decimal("103.50")


def test_gate13_long_slippage_direction() -> None:
    """Gate 13: Long slippage increases entry price and decreases exit price."""
    d = date(2020, 1, 6)
    bars = _create_synthetic_390_bars(d, base_price=Decimal("100.00"))
    bars[5] = OrbBar(
        event_start_utc=bars[5].event_start_utc,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("100"),
        close=Decimal("101.50"),
        volume=Decimal("1000"),
    )
    config = OrbCellConfig(cell_id="ORB_5M_LONG", window_minutes=5, direction="LONG")
    res = simulate_orb_session(d, bars, config)
    trade = res.trade
    assert trade is not None
    assert trade.fill_entry_price > trade.observable_entry_price
    assert trade.fill_exit_price < trade.observable_exit_price


def test_gate14_short_slippage_direction() -> None:
    """Gate 14: Short slippage decreases entry price and increases exit price."""
    d = date(2020, 1, 6)
    bars = _create_synthetic_390_bars(d, base_price=Decimal("100.00"))
    # Short breakout: close < OR_low (99.50)
    bars[5] = OrbBar(
        event_start_utc=bars[5].event_start_utc,
        open=Decimal("100"),
        high=Decimal("100"),
        low=Decimal("98"),
        close=Decimal("99.00"),
        volume=Decimal("1000"),
    )
    config = OrbCellConfig(cell_id="ORB_5M_SHORT", window_minutes=5, direction="SHORT")
    res = simulate_orb_session(d, bars, config)
    trade = res.trade
    assert trade is not None
    assert trade.fill_entry_price < trade.observable_entry_price
    assert trade.fill_exit_price > trade.observable_exit_price


def test_gate15_transaction_cost_application() -> None:
    """Gate 15: Net return is strictly less than gross return due to transaction costs & slippage."""
    d = date(2020, 1, 6)
    bars = _create_synthetic_390_bars(d, base_price=Decimal("100.00"))
    bars[5] = OrbBar(
        event_start_utc=bars[5].event_start_utc,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("100"),
        close=Decimal("101.50"),
        volume=Decimal("1000"),
    )
    config = OrbCellConfig(cell_id="ORB_5M_LONG", window_minutes=5, direction="LONG")
    res = simulate_orb_session(d, bars, config)
    assert res.trade is not None
    assert res.trade.net_return < res.trade.gross_return


def test_gate16_max_one_trade_per_cell_session() -> None:
    """Gate 16: Maximum 1 trade executed per session per cell."""
    d = date(2020, 1, 6)
    bars = _create_synthetic_390_bars(d, base_price=Decimal("100.00"))
    # Signal at bar 5
    bars[5] = OrbBar(
        event_start_utc=bars[5].event_start_utc,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("100"),
        close=Decimal("101.50"),
        volume=Decimal("1000"),
    )
    # Stop hit at bar 7
    bars[7] = OrbBar(
        event_start_utc=bars[7].event_start_utc,
        open=Decimal("100"),
        high=Decimal("100"),
        low=Decimal("98.00"),
        close=Decimal("98.50"),
        volume=Decimal("1000"),
    )
    # Another breakout at bar 50
    bars[50] = OrbBar(
        event_start_utc=bars[50].event_start_utc,
        open=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("100"),
        close=Decimal("104.50"),
        volume=Decimal("1000"),
    )
    config = OrbCellConfig(cell_id="ORB_5M_LONG", window_minutes=5, direction="LONG")
    res = simulate_orb_session(d, bars, config)
    assert res.had_trade is True
    assert res.trade is not None
    # Trade was exited at bar 7 and never re-entered
    assert res.trade.exit_bar_index == 7


def test_gate17_no_reentry() -> None:
    """Gate 17: After stop or exit, no subsequent signals enter trades on same day."""
    test_gate16_max_one_trade_per_cell_session()


def test_gate18_independent_long_short_cells() -> None:
    """Gate 18: LONG and SHORT cells process breakouts independently on the same session."""
    d = date(2020, 1, 6)
    bars = _create_synthetic_390_bars(d, base_price=Decimal("100.00"))
    # Upward breakout at bar 5
    bars[5] = OrbBar(
        event_start_utc=bars[5].event_start_utc,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("100"),
        close=Decimal("101.50"),
        volume=Decimal("1000"),
    )
    # Downward breakout at bar 30
    bars[30] = OrbBar(
        event_start_utc=bars[30].event_start_utc,
        open=Decimal("100"),
        high=Decimal("100"),
        low=Decimal("97"),
        close=Decimal("98.00"),
        volume=Decimal("1000"),
    )
    long_cfg = OrbCellConfig(cell_id="ORB_5M_LONG", window_minutes=5, direction="LONG")
    short_cfg = OrbCellConfig(cell_id="ORB_5M_SHORT", window_minutes=5, direction="SHORT")
    res_long = simulate_orb_session(d, bars, long_cfg)
    res_short = simulate_orb_session(d, bars, short_cfg)
    assert res_long.had_trade is True
    assert res_short.had_trade is True
    assert res_long.trade is not None
    assert res_short.trade is not None
    assert res_long.trade.signal_bar_index == 5
    assert res_short.trade.signal_bar_index == 30


def test_gate19_incomplete_sessions_fail_closed() -> None:
    """Gate 19: Session with bar count != 390 is rejected immediately."""
    d = date(2020, 1, 6)
    bars = _create_synthetic_390_bars(d)
    bars_incomplete = bars[:380]  # Only 380 bars
    config = OrbCellConfig(cell_id="ORB_5M_LONG", window_minutes=5, direction="LONG")
    with pytest.raises(DataContractError, match=r"bar count != 390"):
        simulate_orb_session(d, bars_incomplete, config)


def test_gate20_deterministic_result_hashes() -> None:
    """Gate 20: Cell census produces deterministic series hashes across identical runs."""
    d1 = date(2020, 1, 6)
    d2 = date(2020, 1, 7)
    bars1 = _create_synthetic_390_bars(d1)
    bars2 = _create_synthetic_390_bars(d2)
    # Give session 1 a trade so variance is non-zero
    bars1[5] = OrbBar(
        event_start_utc=bars1[5].event_start_utc,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("100"),
        close=Decimal("101.50"),
        volume=Decimal("1000"),
    )
    sessions = [(d1, bars1), (d2, bars2)]
    config = OrbCellConfig(cell_id="ORB_5M_LONG", window_minutes=5, direction="LONG")
    s1, _, _ = execute_cell_census(config, sessions)
    s2, _, _ = execute_cell_census(config, sessions)
    assert s1.in_sample_return_series_sha256 == s2.in_sample_return_series_sha256
    assert s1.config_sha256 == s2.config_sha256
    assert s1.p_value_input_hash == s2.p_value_input_hash
