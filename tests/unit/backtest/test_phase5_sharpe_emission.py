"""Adversarial tests for Phase 5 canonical Sharpe emission from the event backtest engine (Phase 14, D8-B).

Verify:
- run_backtest emits execution_summary.sharpe_ratio from the canonical equity-derived return series
  and the single canonical Sharpe authority (D7), with ValidationConfig.periods_per_year supplied by
  the caller (D4);
- the emission never contaminates the content-derived manifest_id (identity invariance);
- fail-closed behavior for insufficient observations, zero variance, invalid annualization, and
  missing required argument.
"""

from decimal import Decimal
from typing import Any

import pyarrow as pa
import pytest

from acash.backtest.adapter import CanonicalDataAdapter
from acash.backtest.engine import EventBacktestRunner
from acash.backtest.equity_returns import derive_canonical_equity_returns
from acash.backtest.schema import (
    BacktestEngineConfig,
    calculate_backtest_manifest_id,
)
from acash.backtest.strategies.imbalance_actor import MicrostructureImbalanceActor
from acash.core.domain.exceptions import DataContractError
from acash.validation.deflated_sharpe import calculate_annualized_sharpe

_PPY = Decimal("252.0")


class BuyHoldingActor:
    """Places a single market buy on bar 2 and holds to the end."""

    def __init__(self, symbol: str) -> None:
        self._actor = MicrostructureImbalanceActor(symbol=symbol)

    def on_bar(self, event: Any, runner: Any) -> None:
        if event.payload["bar_index"] == 2:
            self._actor.generate_signal_and_order(Decimal("0.40"), runner)

    def on_trade(self, event: Any, runner: Any) -> None:
        pass


class NoTradeActor:
    """Never places an order -> flat book -> constant equity when prices are constant."""

    def on_bar(self, event: Any, runner: Any) -> None:
        pass

    def on_trade(self, event: Any, runner: Any) -> None:
        pass


def _bars_table(closes: list[Decimal], opens: list[Decimal] | None = None) -> pa.Table:
    n = len(closes)
    o = opens or [Decimal("5000.00")] * n
    return pa.Table.from_pydict(
        {
            "timestamp_utc": [1_768_833_000_000_000_000 + (i * 60_000_000_000) for i in range(n)],
            "open": o,
            "high": [max(x, y) + Decimal("1.00") for x, y in zip(opens or o, closes)],
            "low": [min(x, y) - Decimal("1.00") for x, y in zip(opens or o, closes)],
            "close": closes,
            "volume": [Decimal("100.0")] * n,
        }
    )


def _run(closes: list[Decimal], actor: Any, ppy: Decimal) -> tuple[Any, pa.Table]:
    events = CanonicalDataAdapter.from_bars_table(_bars_table(closes), symbol="ES.FUT")
    runner = EventBacktestRunner(
        config=BacktestEngineConfig(engine_id="BKT-SR-EMIT", symbol="ES.FUT"),
        strategy_actor=actor,
    )
    manifest, _fills, equity = runner.run_backtest(
        events=events,
        hypothesis_id="HYP_SR_EMIT_0001",
        hypothesis_spec_sha256="a" * 64,
        strategy_config_hash="b" * 64,
        pyproject_toml_sha256="c" * 64,
        git_commit_hash="a" * 40,
        periods_per_year=ppy,
        canonical_data_hashes=["d" * 64],
    )
    return manifest, equity


class TestEmission:
    def test_emitted_sharpe_equals_canonical_authority(self) -> None:
        closes = [Decimal("5000.00"), Decimal("5002.00"), Decimal("5004.00"), Decimal("5008.00"), Decimal("5006.00")]
        manifest, equity = _run(closes, BuyHoldingActor("ES.FUT"), _PPY)

        assert manifest.execution_summary.sharpe_ratio is not None
        expected = calculate_annualized_sharpe(derive_canonical_equity_returns(equity), _PPY)
        assert manifest.execution_summary.sharpe_ratio == expected
        assert manifest.execution_summary.sortino_ratio is None

    def test_different_periods_per_year_change_sharpe_not_manifest_id(self) -> None:
        closes = [Decimal("5000.00"), Decimal("5002.00"), Decimal("5004.00"), Decimal("5008.00"), Decimal("5006.00")]
        events = CanonicalDataAdapter.from_bars_table(_bars_table(closes), symbol="ES.FUT")
        cfg = BacktestEngineConfig(engine_id="BKT-SR-EMIT-SCALE", symbol="ES.FUT")
        runner_a = EventBacktestRunner(config=cfg, strategy_actor=BuyHoldingActor("ES.FUT"))
        runner_b = EventBacktestRunner(config=cfg, strategy_actor=BuyHoldingActor("ES.FUT"))
        hyp_sha, cfg_sha = "a" * 64, "b" * 64

        def run_with(runner: EventBacktestRunner, ppy: Decimal) -> Any:
            return runner.run_backtest(
                events=events,
                hypothesis_id="HYP_SR_EMIT_0002",
                hypothesis_spec_sha256=hyp_sha,
                strategy_config_hash=cfg_sha,
                pyproject_toml_sha256="c" * 64,
                git_commit_hash="a" * 40,
                periods_per_year=ppy,
                canonical_data_hashes=["d" * 64],
            )[0]

        manifest_a = run_with(runner_a, Decimal("1.0"))
        manifest_b = run_with(runner_b, Decimal("252.0"))

        assert manifest_a.execution_summary.sharpe_ratio != manifest_b.execution_summary.sharpe_ratio
        # manifest_id is content-derived and MUST NOT depend on the annualization frequency.
        assert manifest_a.manifest_id == manifest_b.manifest_id

    def test_manifest_id_matches_content_derived_identity(self) -> None:
        closes = [Decimal("5000.00"), Decimal("5002.00"), Decimal("5004.00"), Decimal("5008.00"), Decimal("5006.00")]
        manifest, _ = _run(closes, BuyHoldingActor("ES.FUT"), _PPY)
        expected_id = calculate_backtest_manifest_id(
            hypothesis_spec_sha256="a" * 64,
            canonical_data_hashes=["d" * 64],
            engine_config_hash=manifest.engine_config_hash,
            strategy_config_hash="b" * 64,
            prng_seed=42,
        )
        assert manifest.manifest_id == expected_id


class TestEmissionFailClosed:
    def test_single_observation_fails_closed(self) -> None:
        with pytest.raises(DataContractError, match="at least 2"):
            _run([Decimal("5000.00")], BuyHoldingActor("ES.FUT"), _PPY)

    def test_zero_variance_fails_closed(self) -> None:
        # Constant prices and no orders -> flat equity -> zero-variance return series.
        closes = [Decimal("5000.00"), Decimal("5000.00"), Decimal("5000.00")]
        with pytest.raises(DataContractError, match="zero-variance"):
            _run(closes, NoTradeActor(), _PPY)

    def test_invalid_periods_per_year_fails_closed(self) -> None:
        closes = [Decimal("5000.00"), Decimal("5002.00"), Decimal("5004.00")]
        with pytest.raises(DataContractError, match="invalid periods_per_year"):
            _run(closes, BuyHoldingActor("ES.FUT"), Decimal("0.0"))

    def test_omitted_periods_per_year_raises_type_error(self) -> None:
        events = CanonicalDataAdapter.from_bars_table(
            _bars_table([Decimal("5000.00"), Decimal("5002.00"), Decimal("5004.00")]), symbol="ES.FUT"
        )
        runner = EventBacktestRunner(
            config=BacktestEngineConfig(engine_id="BKT-SR-REQ", symbol="ES.FUT"),
            strategy_actor=BuyHoldingActor("ES.FUT"),
        )
        with pytest.raises(TypeError, match="periods_per_year"):
            runner.run_backtest(  # type: ignore[call-arg]
                events=events,
                hypothesis_id="HYP_SR_EMIT_0003",
                hypothesis_spec_sha256="a" * 64,
                strategy_config_hash="b" * 64,
                pyproject_toml_sha256="c" * 64,
                git_commit_hash="a" * 40,
                canonical_data_hashes=["d" * 64],
            )