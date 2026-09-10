"""Canonical Phase 5 equity-derived simple return derivation (Phase 14, D2-A / D3 ratified).

Ratified semantics (see ``docs/phase14/phase14_evidence_bridge_ratification_D1_D9.md``, D3):

- Authoritative Phase 5 accounting column: the canonical equity curve table
  (``CANONICAL_EQUITY_CURVE_SCHEMA`` in ``acash.backtest.schema``) column ``total_equity``
  (balance-sheet equity). Double-entry conservation of this quantity is enforced by
  ``ShadowAccountingLedger`` during the run (``verify_internal_conservation``).
- Returns are a property of realized accounting/equity evolution (D2-A): ``r_t = E_t / E_{t-1} - 1``.
- Observations are processed in canonical row order, which is the deterministic event-timestamp /
  canonical tie-break order emitted by the Phase 5 runner. Decreasing timestamps fail closed.
- The first observation has no return and is excluded from the return series.
- Duplicate observations are preserved (never silently collapsed); missing observations are never
  imputed; no future padding, no interpolation, no look-ahead, and no resampling rule are introduced.
- Non-finite equity, non-positive previous equity (zero or invalid denominator), negative current
  equity (invalid accounting state), and non-finite derived returns fail closed.
- Insufficient observations (fewer than two equity observations) fail closed.
"""

from decimal import Decimal
from typing import List

import pyarrow as pa

from acash.backtest.schema import CANONICAL_EQUITY_CURVE_SCHEMA
from acash.core.domain.exceptions import DataContractError

CANONICAL_EQUITY_COLUMN = "total_equity"
CANONICAL_TIMESTAMP_COLUMN = "timestamp_utc"
MINIMUM_EQUITY_OBSERVATIONS = 2


def derive_canonical_equity_returns(equity_table: pa.Table) -> List[Decimal]:
    """Derive deterministic simple returns ``r_t = E_t / E_{t-1} - 1`` from canonical equity observations.

    Args:
        equity_table: The canonical Phase 5 equity curve table (``CANONICAL_EQUITY_CURVE_SCHEMA``).

    Returns:
        List of per-observation simple returns, length = ``num_rows - 1`` (first observation excluded).

    Raises:
        DataContractError: On insufficient observations, missing authoritative column, non-monotonic
            canonical ordering, non-finite equity, invalid denominator, negative equity state, or
            non-finite derived returns (strict fail-closed contract).
    """
    num_rows = equity_table.num_rows if equity_table is not None else 0
    if num_rows < MINIMUM_EQUITY_OBSERVATIONS:
        raise DataContractError(
            f"Cannot derive canonical equity returns: equity table has {num_rows} observation(s); "
            f"at least {MINIMUM_EQUITY_OBSERVATIONS} non-empty equity observations are required."
        )

    if CANONICAL_EQUITY_COLUMN not in equity_table.column_names:
        raise DataContractError(
            f"Cannot derive canonical equity returns: authoritative equity column "
            f"'{CANONICAL_EQUITY_COLUMN}' missing from equity table (schema: {CANONICAL_EQUITY_CURVE_SCHEMA})."
        )
    if CANONICAL_TIMESTAMP_COLUMN not in equity_table.column_names:
        raise DataContractError(
            f"Cannot derive canonical equity returns: ordering column '{CANONICAL_TIMESTAMP_COLUMN}' "
            f"missing from equity table (schema: {CANONICAL_EQUITY_CURVE_SCHEMA})."
        )

    timestamps_ns = [int(v) for v in equity_table.column(CANONICAL_TIMESTAMP_COLUMN).cast(pa.int64()).to_pylist()]
    equities = equity_table.column(CANONICAL_EQUITY_COLUMN).to_pylist()

    # 1. Canonical deterministic ordering enforcement (equal timestamps are preserved in row order,
    #    i.e. duplicate observations are never silently collapsed); decreasing timestamps fail closed.
    prev_ts: int | None = None
    for idx, ts in enumerate(timestamps_ns):
        if prev_ts is not None and ts < prev_ts:
            raise DataContractError(
                f"Cannot derive canonical equity returns: equity observation at index {idx} has "
                f"timestamp {ts} preceding previous observation timestamp {prev_ts}; "
                f"canonical event ordering violated."
            )
        prev_ts = ts

    # 2. Deterministic simple-return derivation over consecutive canonical equity observations.
    returns: List[Decimal] = []
    for idx in range(1, num_rows):
        prev_eq = equities[idx - 1]
        cur_eq = equities[idx]
        if not isinstance(prev_eq, Decimal):
            raise DataContractError(
                f"Cannot derive canonical equity returns: previous equity at index {idx - 1} is not a Decimal "
                f"(got {type(prev_eq).__name__})."
            )
        if not isinstance(cur_eq, Decimal):
            raise DataContractError(
                f"Cannot derive canonical equity returns: current equity at index {idx} is not a Decimal "
                f"(got {type(cur_eq).__name__})."
            )
        if not prev_eq.is_finite():
            raise DataContractError(
                f"Cannot derive canonical equity returns: non-finite previous equity observation "
                f"at index {idx - 1} ({prev_eq})."
            )
        if not cur_eq.is_finite():
            raise DataContractError(
                f"Cannot derive canonical equity returns: non-finite current equity observation "
                f"at index {idx} ({cur_eq})."
            )
        if prev_eq <= Decimal("0.0"):
            raise DataContractError(
                f"Cannot derive canonical equity returns: non-positive previous equity denominator "
                f"{prev_eq} at index {idx - 1}; zero or invalid denominator fails closed."
            )
        if cur_eq < Decimal("0.0"):
            raise DataContractError(
                f"Cannot derive canonical equity returns: negative equity state {cur_eq} at index {idx}; "
                f"invalid accounting state fails closed."
            )

        ret = (cur_eq / prev_eq) - Decimal("1.0")
        if not ret.is_finite():
            raise DataContractError(
                f"Cannot derive canonical equity returns: non-finite derived return at index {idx - 1} "
                f"(E_prev={prev_eq}, E_cur={cur_eq})."
            )
        returns.append(ret)

    return returns