"""Phase 8.5 research-test data-dependency policy & deterministic synthetic fixtures.

REPOSITORY RESEARCH-DATA TEST POLICY
------------------------------------
1. Unit / governance tests MUST run in a clean clone WITHOUT proprietary or local
   research artifacts (everything under /data/ is gitignored).
2. Tests that verify SEALED research artifacts (dataset row counts, digests,
   provenance ledger records, trial return series) are data-integrity checks.
   They run their full, unweakened assertions whenever the local sealed artifact
   is present. When the artifact is ABSENT (clean clone / non-research box), they
   must report the missing dependency as an explicit DATA-DEPENDENT-ENVIRONMENT
   condition (pytest.skip with a descriptive reason), NOT as a failure and NOT
   silently.
3. Generic data-contract tests (monotonicity, no duplicates, OHLC structural
   invariants, lookahead-free features, label boundary handling) must use
   deterministic SYNTHETIC fixtures built against the CANONICAL_ARROW_SCHEMA.
   Synthetic fixtures never pretend to be EURUSD research data.
4. No test or helper may read or synthesize real market data, bypass quarantine,
   or alter governance semantics.

The two fixtures below are the single authority for this policy:
- ``build_canonical_synthetic_table`` : deterministic synthetic OHLCV table.
- ``require_research_artifact``       : explicit data-dependency gate.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, List, Sequence

import pyarrow as pa
import pytest

from acash.data.schema import CANONICAL_ARROW_SCHEMA


def _metric_step(idx: int) -> Decimal:
    """Deterministic bounded pseudo-walk used ONLY for synthetic non-market data."""
    return Decimal((idx % 5) - 2)


def _build_canonical_synthetic_table(
    n_bars: int,
    symbol: str = "SYNTH_ASSET",
    timeframe: str = "TF5",
    source_id: str = "SRC-SYNTHETIC-NONMARKET",
    base_price: Decimal = Decimal("101.25"),
    start_utc: datetime = datetime(2021, 1, 4, 0, 0, 0, tzinfo=timezone.utc),
    step_minutes: int = 5,
) -> pa.Table:
    """Build a deterministic schema-valid synthetic OHLCV table.

    The rows satisfy:
    - strictly monotonic event_start_utc, non-overlapping intervals
    - OHLC structural invariants (H>=L, H>=O, H>=C, L<=O, L<=C, prices>0, volume>=0)
    This is NOT market data; it is a generic, reproducible test fixture.
    """
    step = timedelta(minutes=step_minutes)

    starts: List[datetime] = []
    ends: List[datetime] = []
    knowledge_times: List[datetime] = []
    opens: List[Decimal] = []
    highs: List[Decimal] = []
    lows: List[Decimal] = []
    closes: List[Decimal] = []
    volumes: List[Decimal] = []
    quote_volumes: List[Decimal] = []
    trade_counts: List[int] = []
    revision_seqs: List[int] = []

    for i in range(n_bars):
        s = start_utc + i * step
        e = s + step
        starts.append(s)
        ends.append(e)
        knowledge_times.append(e)

        o = base_price + _metric_step((i + 1) % 7)
        c = base_price + _metric_step(i % 7)
        hi = (o if o >= c else c) + Decimal("0.50")
        lo = (o if o <= c else c) - Decimal("0.50")
        v = Decimal(i % 3 + 1)
        qv = v * Decimal("2")
        tc = i * 10 + 1

        opens.append(o)
        highs.append(hi)
        lows.append(lo)
        closes.append(c)
        volumes.append(v)
        quote_volumes.append(qv)
        trade_counts.append(tc)
        revision_seqs.append(0)

    table = pa.table(
        {
            "source_id": pa.array([source_id] * n_bars, type=pa.string()),
            "symbol": pa.array([symbol] * n_bars, type=pa.string()),
            "timeframe": pa.array([timeframe] * n_bars, type=pa.string()),
            "event_start_utc": pa.array(starts, type=pa.timestamp("us", tz="UTC")),
            "event_end_utc": pa.array(ends, type=pa.timestamp("us", tz="UTC")),
            "knowledge_time_utc": pa.array(knowledge_times, type=pa.timestamp("us", tz="UTC")),
            "revision_seq": pa.array(revision_seqs, type=pa.int64()),
            "open": pa.array(opens, type=pa.decimal128(38, 18)),
            "high": pa.array(highs, type=pa.decimal128(38, 18)),
            "low": pa.array(lows, type=pa.decimal128(38, 18)),
            "close": pa.array(closes, type=pa.decimal128(38, 18)),
            "volume": pa.array(volumes, type=pa.decimal128(38, 18)),
            "quote_volume": pa.array(quote_volumes, type=pa.decimal128(38, 18)),
            "trade_count": pa.array(trade_counts, type=pa.int64()),
        }
    )
    return pa.Table.from_arrays(list(table.columns), schema=CANONICAL_ARROW_SCHEMA)


@pytest.fixture
def build_canonical_synthetic_table() -> Callable[..., pa.Table]:
    """Fixture factory returning deterministic schema-valid synthetic OHLCV tables."""
    return _build_canonical_synthetic_table


@pytest.fixture
def require_research_artifact() -> Callable[[Sequence[Path], str], None]:
    """Fixture factory returning an explicit data-dependency gate.

    Usage: ``require_research_artifact([path1, path2], "description")``.
    - If all paths exist: returns silently; the test then runs its FULL assertions.
    - If any path is missing: raises ``pytest.skip`` with a DATA-DEPENDENT-ENVIRONMENT
      reason (reported, never silent, never a PASS).
    """

    def _require(paths: Sequence[Path], description: str) -> None:
        missing = [p for p in paths if not Path(p).exists()]
        if missing:
            pytest.skip(
                f"DATA-DEPENDENT-ENVIRONMENT: {description} not present in this environment "
                f"(missing: {', '.join(str(p) for p in missing)}). This is a gitignored sealed "
                f"research artifact; full data-integrity assertions run only when it is present."
            )

    return _require


__all__: List[str] = [
    "build_canonical_synthetic_table",
    "require_research_artifact",
]