"""Forward Outcome Generation, Temporal Purging, and Embargo Engine (Phase 4).

Strictly enforces:
- Discrete Bar-Indexed Forward Returns: R(t, H) = (Close[t+H] - Open[t+1]) / Open[t+1].
- Exact label_interval: [OpenTimestamp[t+1], CloseTimestamp[t+H]].
- Boundary Purging: Purges training samples whose label_interval extends past partition boundaries.
- Embargo Buffers: Enforces unallocated bar buffers between Train -> Validation and Validation -> OOS.
- Zero Lookahead: Evaluated strictly as of Bar t Close.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple
import pyarrow as pa

from acash.data.features.engine import to_decimal18
from acash.data.schema import DataContractError
from acash.research.schema import CANONICAL_FORWARD_OUTCOMES_SCHEMA, SplitPolicy


def compute_discrete_forward_returns(
    bars_table: pa.Table,
    symbol: str,
    trading_date: date,
    horizons: Sequence[int] = (1, 5, 15, 60),
    train_end_idx: Optional[int] = None,
    val_end_idx: Optional[int] = None,
) -> pa.Table:
    """Compute discrete bar-indexed forward returns for specified horizons.

    Args:
        bars_table: PyArrow Table containing bar data with columns:
            ['bar_start_utc', 'bar_end_utc', 'open', 'close']
        symbol: Target instrument symbol.
        trading_date: Trading session date.
        horizons: List of forward bar horizons H.
        train_end_idx: Optional index boundary for training set (for purging).
        val_end_idx: Optional index boundary for validation set (for purging).

    Returns:
        PyArrow Table conforming to CANONICAL_FORWARD_OUTCOMES_SCHEMA.
    """
    if bars_table.num_rows == 0:
        return pa.Table.from_batches([], schema=CANONICAL_FORWARD_OUTCOMES_SCHEMA)

    pydict = bars_table.to_pydict()
    num_bars = bars_table.num_rows

    # Extract required series
    bar_starts = pydict["bar_start_utc"]
    bar_ends = pydict["bar_end_utc"]
    opens = [
        to_decimal18(pydict["open"][i]) or Decimal("0")
        for i in range(num_bars)
    ]
    closes = [
        to_decimal18(pydict["close"][i]) or Decimal("0")
        for i in range(num_bars)
    ]

    out_records: List[Dict[str, Any]] = []

    for H in sorted(horizons):
        if H <= 0:
            raise DataContractError(f"Horizon H must be >= 1, got {H}")

        for t in range(num_bars):
            decision_t = bar_ends[t]
            entry_idx = t + 1
            exit_idx = t + H

            if exit_idx >= num_bars:
                # Horizon extends beyond available bar series
                continue

            entry_t = bar_starts[entry_idx]
            exit_t = bar_ends[exit_idx]
            entry_px = opens[entry_idx]
            exit_px = closes[exit_idx]

            if entry_px <= Decimal("0"):
                continue

            fwd_ret = to_decimal18((exit_px - entry_px) / entry_px)

            # Determine purging status
            is_purged = False
            if train_end_idx is not None and t <= train_end_idx and exit_idx > train_end_idx:
                is_purged = True
            elif val_end_idx is not None and t <= val_end_idx and exit_idx > val_end_idx:
                is_purged = True

            out_records.append({
                "symbol": symbol,
                "trading_date": trading_date,
                "decision_bar_index": t,
                "decision_bar_utc": decision_t,
                "entry_bar_utc": entry_t,
                "exit_bar_utc": exit_t,
                "entry_price": entry_px,
                "exit_price": exit_px,
                "horizon_bars": H,
                "forward_return": fwd_ret,
                "is_purged_boundary": is_purged,
            })


    if not out_records:
        return pa.Table.from_batches([], schema=CANONICAL_FORWARD_OUTCOMES_SCHEMA)

    table_data = {col: [r[col] for r in out_records] for col in CANONICAL_FORWARD_OUTCOMES_SCHEMA.names}
    return pa.Table.from_pydict(table_data, schema=CANONICAL_FORWARD_OUTCOMES_SCHEMA)


def partition_dataset_with_embargo(
    total_bars: int,
    split_policy: Optional[SplitPolicy] = None,
) -> Dict[str, Tuple[int, int]]:
    """Calculate index ranges for Train, Validation, and Held-Out OOS with embargo gaps.

    Returns:
        Dict with keys 'TRAIN', 'VAL', 'OOS', each mapping to (start_idx, end_idx) inclusive.
    """
    policy = split_policy or SplitPolicy()
    embargo = policy.embargo_bars

    train_count = max(1, int(total_bars * float(policy.train_pct)))
    val_count = max(1, int(total_bars * float(policy.val_pct)))

    train_start = 0
    train_end = max(0, min(total_bars - 1, train_count - 1))

    val_start = min(total_bars - 1, train_end + 1 + embargo)
    val_end = min(total_bars - 1, val_start + val_count - 1)

    oos_start = min(total_bars - 1, val_end + 1 + embargo)
    oos_end = total_bars - 1

    return {
        "TRAIN": (train_start, train_end),
        "VAL": (val_start, val_end),
        "OOS": (oos_start, oos_end),
    }



