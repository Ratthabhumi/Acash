"""Unit tests for Discrete Forward Returns, Boundary Purging, and Embargo Buffers (Phase 4)."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pyarrow as pa
import pytest

from acash.research.outcomes import (
    compute_discrete_forward_returns,
    partition_dataset_with_embargo,
)
from acash.research.schema import SplitPolicy


def _make_sample_bars_table(num_bars: int = 10) -> pa.Table:
    t0 = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
    bar_starts = [t0 + timedelta(minutes=i) for i in range(num_bars)]
    bar_ends = [t0 + timedelta(minutes=i + 1) for i in range(num_bars)]
    opens = [Decimal(f"{5000 + i}.00") for i in range(num_bars)]
    highs = [Decimal(f"{5001 + i}.00") for i in range(num_bars)]
    lows = [Decimal(f"{4999 + i}.00") for i in range(num_bars)]
    closes = [Decimal("5000.50") + Decimal(str(i)) for i in range(num_bars)]
    volumes = [Decimal("100") for _ in range(num_bars)]


    data = {
        "bar_start_utc": bar_starts,
        "bar_end_utc": bar_ends,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    }
    return pa.Table.from_pydict(data)


def test_discrete_forward_returns_next_bar_open_alignment() -> None:
    """Verify forward return calculates strictly from Open[t+1] to Close[t+H].

    Bars:
    Bar 0: Open=5000.00, Close=5000.50
    Bar 1: Open=5001.00, Close=5001.50
    Bar 2: Open=5002.00, Close=5002.50

    For t = 0 and H = 1:
    Entry = Open[1] = 5001.00
    Exit = Close[1] = 5001.50
    R(0, 1) = (5001.50 - 5001.00) / 5001.00 = 0.50 / 5001.00 ~= 0.0000999800039992
    """
    bars = _make_sample_bars_table(num_bars=5)
    outcomes = compute_discrete_forward_returns(
        bars_table=bars,
        symbol="ES.FUT",
        trading_date=date(2026, 1, 19),
        horizons=[1],
    )

    pydict = outcomes.to_pydict()
    assert outcomes.num_rows == 4  # Bars 0, 1, 2, 3 have horizon 1 available

    # Check t=0 entry and exit
    assert pydict["entry_price"][0] == Decimal("5001.00")
    assert pydict["exit_price"][0] == Decimal("5001.50")
    expected_ret = float(Decimal("0.50") / Decimal("5001.00"))
    assert float(pydict["forward_return"][0]) == pytest.approx(expected_ret, rel=1e-6)



def test_boundary_purging_and_embargo_partitioning() -> None:
    """Verify boundary purging flags observations crossing train_end_idx and embargo buffers."""
    bars = _make_sample_bars_table(num_bars=10)
    # If train_end_idx = 4 and H = 2:
    # Bar 3 has exit at idx 3 + 2 = 5 > 4 -> Must be marked is_purged_boundary = True!
    outcomes = compute_discrete_forward_returns(
        bars_table=bars,
        symbol="ES.FUT",
        trading_date=date(2026, 1, 19),
        horizons=[2],
        train_end_idx=4,
    )

    pydict = outcomes.to_pydict()
    # At t=3 (index 3), exit_idx = 5 > 4 -> is_purged_boundary = True
    assert pydict["is_purged_boundary"][3] is True
    # At t=2 (index 2), exit_idx = 4 <= 4 -> is_purged_boundary = False
    assert pydict["is_purged_boundary"][2] is False

    # Test Embargo Gap Calculation
    policy = SplitPolicy(train_pct=Decimal("0.50"), val_pct=Decimal("0.20"), oos_pct=Decimal("0.30"), embargo_bars=5)
    parts = partition_dataset_with_embargo(100, policy)
    train_s, train_e = parts["TRAIN"]
    val_s, val_e = parts["VAL"]
    oos_s, oos_e = parts["OOS"]

    assert train_e == 49
    assert val_s == 49 + 1 + 5  # 55
    assert oos_s == val_e + 1 + 5


def test_multi_horizon_interval_purging_exact_bounds() -> None:
    """Verify observations with varying horizons purge exactly when label intervals cross train_end_idx."""
    bars = _make_sample_bars_table(num_bars=15)
    # train_end_idx = 7
    # For H=1: bar 7 has exit at 7+1 = 8 > 7 -> purged; bar 6 has exit at 6+1 = 7 <= 7 -> not purged.
    # For H=3: bar 5 has exit at 5+3 = 8 > 7 -> purged; bar 4 has exit at 4+3 = 7 <= 7 -> not purged.
    outcomes = compute_discrete_forward_returns(
        bars_table=bars,
        symbol="ES.FUT",
        trading_date=date(2026, 1, 19),
        horizons=[1, 3],
        train_end_idx=7,
    )

    df = outcomes.to_pandas()
    h1 = df[df["horizon_bars"] == 1].reset_index(drop=True)
    h3 = df[df["horizon_bars"] == 3].reset_index(drop=True)

    # Check H=1
    assert bool(h1.loc[6, "is_purged_boundary"]) is False
    assert bool(h1.loc[7, "is_purged_boundary"]) is True

    # Check H=3
    assert bool(h3.loc[4, "is_purged_boundary"]) is False
    assert bool(h3.loc[5, "is_purged_boundary"]) is True


