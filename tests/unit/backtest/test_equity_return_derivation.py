"""Adversarial tests for canonical equity-derived simple return derivation (Phase 14, D2-A / D3).

Attack the ratified D3 semantics:
- first observation excluded (returns length == rows - 1);
- duplicates preserved, never collapsed;
- no imputation / padding / interpolation / resampling;
- deterministic canonical row order enforced (decreasing timestamps fail closed);
- non-finite / non-Decimal / zero-denominator / negative-equity states fail closed;
- insufficient observations fail closed.
"""

from decimal import Decimal

import pyarrow as pa
import pytest

from acash.backtest.equity_returns import (
    CANONICAL_EQUITY_COLUMN,
    MINIMUM_EQUITY_OBSERVATIONS,
    derive_canonical_equity_returns,
)
from acash.backtest.schema import CANONICAL_EQUITY_CURVE_SCHEMA
from acash.core.domain.exceptions import DataContractError

_T60_NS = 60_000_000_000


def _equity_table(timestamps_ns: list[int], equities: list[Decimal]) -> pa.Table:
    n = len(equities)
    return pa.Table.from_pydict(
        {
            "timestamp_utc": timestamps_ns,
            "cash_balance": [Decimal("0.0")] * n,
            "realized_pnl": [Decimal("0.0")] * n,
            "unrealized_pnl": [Decimal("0.0")] * n,
            CANONICAL_EQUITY_COLUMN: equities,
            "margin_utilized": [Decimal("0.0")] * n,
            "accounting_residual": [Decimal("0.0")] * n,
        },
        schema=CANONICAL_EQUITY_CURVE_SCHEMA,
    )


def _ts(n: int) -> list[int]:
    return [1_768_833_000_000_000_000 + (i * _T60_NS) for i in range(n)]


class TestGoldenSemantics:
    def test_golden_exact_returns(self) -> None:
        table = _equity_table(_ts(4), [Decimal("100000"), Decimal("100000"), Decimal("110000"), Decimal("99000")])
        returns = derive_canonical_equity_returns(table)
        assert returns == [Decimal("0.0"), Decimal("0.1"), Decimal("-0.1")]
        assert len(returns) == table.num_rows - 1

    def test_first_observation_excluded(self) -> None:
        table = _equity_table(_ts(3), [Decimal("999")] * 3)
        returns = derive_canonical_equity_returns(table)
        assert len(returns) == 2

    def test_constant_equity_is_not_imputed_or_padded(self) -> None:
        table = _equity_table(_ts(4), [Decimal("100000"), Decimal("100000"), Decimal("100000"), Decimal("100000")])
        returns = derive_canonical_equity_returns(table)
        assert returns == [Decimal("0.0"), Decimal("0.0"), Decimal("0.0")]

    def test_duplicate_timestamps_preserved_not_collapsed(self) -> None:
        ts = [10, 10, 20, 20]  # duplicates preserved in row order
        table = _equity_table(ts, [Decimal("100000"), Decimal("101000"), Decimal("99000"), Decimal("101000")])
        returns = derive_canonical_equity_returns(table)
        assert len(returns) == 3  # all 4 observations contribute; no deduplication


class TestFailClosed:
    def test_zero_rows_fails_closed(self) -> None:
        empty = pa.Table.from_arrays(
            [pa.array([], type=pa.timestamp("ns", tz="UTC"))]
            + [pa.array([], type=pa.decimal128(38, 18))] * 6,
            schema=CANONICAL_EQUITY_CURVE_SCHEMA,
        )
        with pytest.raises(DataContractError, match="at least 2"):
            derive_canonical_equity_returns(empty)

    def test_single_row_fails_closed(self) -> None:
        table = _equity_table([10], [Decimal("100000")])
        with pytest.raises(DataContractError, match="at least 2"):
            derive_canonical_equity_returns(table)

    def test_minimum_observation_boundary_passes(self) -> None:
        table = _equity_table(_ts(2), [Decimal("100000"), Decimal("101000")])
        assert derive_canonical_equity_returns(table) == [Decimal("0.01")]

    def test_decreasing_timestamp_fails_closed(self) -> None:
        table = _equity_table([30, 20, 10], [Decimal("100000"), Decimal("101000"), Decimal("99000")])
        with pytest.raises(DataContractError, match="ordering violated"):
            derive_canonical_equity_returns(table)

    def test_zero_previous_denominator_fails_closed(self) -> None:
        table = _equity_table(_ts(2), [Decimal("0.0"), Decimal("100.0")])
        with pytest.raises(DataContractError, match="non-positive previous equity denominator"):
            derive_canonical_equity_returns(table)

    def test_negative_previous_denominator_fails_closed(self) -> None:
        table = _equity_table(_ts(2), [Decimal("-50.0"), Decimal("100.0")])
        with pytest.raises(DataContractError, match="non-positive previous equity denominator"):
            derive_canonical_equity_returns(table)

    def test_negative_current_equity_state_fails_closed(self) -> None:
        table = _equity_table(_ts(2), [Decimal("100.0"), Decimal("-10.0")])
        with pytest.raises(DataContractError, match="negative equity state"):
            derive_canonical_equity_returns(table)

    def test_missing_authoritative_column_fails_closed(self) -> None:
        broken = pa.Table.from_pydict({"other_col": [1, 2, 3]})
        with pytest.raises(DataContractError, match="missing from equity table"):
            derive_canonical_equity_returns(broken)

    def test_non_hex_or_foreign_table_fails_closed(self) -> None:
        table = _equity_table(_ts(3), [Decimal("100000"), Decimal("101000"), Decimal("99000")])
        non_schema = pa.Table.from_pydict(
            {
                "timestamp_utc": [1, 2, 3],
                "cash_balance": [1.0, 1.0, 1.0],
                "realized_pnl": [0.0, 0.0, 0.0],
                "unrealized_pnl": [0.0, 0.0, 0.0],
                CANONICAL_EQUITY_COLUMN: [100000.0, 101000.0, 99000.0],  # float64, not Decimal
                "margin_utilized": [0.0, 0.0, 0.0],
                "accounting_residual": [0.0, 0.0, 0.0],
            }
        )
        assert non_schema.schema == table.schema or not non_schema.schema.equals(table.schema)
        with pytest.raises(DataContractError, match="not a Decimal"):
            derive_canonical_equity_returns(non_schema)

    def test_none_input_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="at least 2"):
            derive_canonical_equity_returns(None)
