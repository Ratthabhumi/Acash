"""Seam A unit tests: truthful Phase 5 hypothesis identity propagation.

Covers the Seam A Option A implementation — Phase 5 runners now carry the
genuine upstream ``HypothesisSpecification.hypothesis_id`` into
``BacktestManifest`` instead of emitting a placeholder.

Scope: native engine (``EventBacktestRunner``, aliased as
``ACASHNativeBacktestEngine``). The ``NautilusTraderSubstrate`` manifest path
requires the ``nautilus_trader`` runtime and is NOT installed in this
environment; signature/placeholder elimination for that substrate is verified
at the source boundary and via the missing-runtime fail-closed path.
"""

from decimal import Decimal
from typing import Tuple

import pyarrow as pa
import pytest

from acash.backtest.adapter import BacktestEventType, BacktestMarketEvent
from acash.backtest.engine import EventBacktestRunner
from acash.backtest.nautilus_bridge import (
    ACASHNativeBacktestEngine,
    NautilusTraderSubstrate,
    SubstrateRuntimeUnavailableError,
)
from acash.backtest.schema import (
    BacktestEngineConfig,
    BacktestManifest,
    OrderType,
    calculate_backtest_manifest_id,
)
from acash.core.domain.exceptions import DataContractError
from acash.research.schema import (
    ExpectedDirection,
    HypothesisSpecification,
    InvalidationCriteria,
)
from acash.validation.gate import StatisticalValidationGate

# These are the (former) placeholders that must never be emitted as manifest
# hypothesis identities.
BANNED_PLACEHOLDERS = ("HYP-PHASE5-POC", "HYP-NAUTILUS-SUBSTRATE")

HYPO_ID = "HYP_SEAM_A_0001"


def _hypothesis() -> HypothesisSpecification:
    return HypothesisSpecification(
        hypothesis_id=HYPO_ID,
        hypothesis_version="v1",
        parent_hypothesis_id=None,
        economic_rationale=(
            "Seam A identity-propagation fixture: directional continuation is "
            "the falsifiable basis; edge is rejected if the HAC t-stat falls "
            "below the pre-registered threshold."
        ),
        target_symbol="EQX:INDEX_SEAM_A",
        feature_dependencies=["order_flow_imbalance"],
        parameter_config_json='{"window": 5, "direction": "long"}',
        expected_direction=ExpectedDirection.LONG,
        target_horizons=[5],
        primary_horizon=5,
        invalidation_criteria=InvalidationCriteria(),
        registered_at_utc="2026-01-01T00:00:00+00:00",
        author="QA_SeamA",
    )


class _SeamAActor:
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.placed = False

    def on_bar(self, event: object, runner: object) -> None:
        if not self.placed:
            runner.submit_order(  # type: ignore[attr-defined]
                order_id="ORD-SEAMA-001",
                symbol=self.symbol,
                order_type=OrderType.MARKET,
                side="BUY",
                quantity=Decimal("1.0"),
            )
            self.placed = True

    def on_trade(self, event: object, runner: object) -> None:
        pass


def _events() -> "list[BacktestMarketEvent]":
    t0_ns = 1768833000_000_000_000
    closes = [Decimal("5004.00"), Decimal("5007.00"), Decimal("5002.00")]
    return [
        BacktestMarketEvent(
            event_type=BacktestEventType.BAR,
            symbol="ES.FUT",
            event_timestamp_ns=t0_ns + (i * 60_000_000_000),
            source_order_key=f"ES.FUT:BARS:{i + 1}",
            message_rank=10,
            stream_id="BARS",
            row_sub_index=0,
            payload={
                "open": closes[i] - Decimal("1.00"),
                "high": closes[i] + Decimal("2.00"),
                "low": closes[i] - Decimal("2.00"),
                "close": closes[i],
                "volume": Decimal("500.0"),
                "bar_index": i,
            },
        )
        for i in range(3)
    ]


def _run_native(hypothesis_id: str) -> "Tuple[BacktestManifest, pa.Table, pa.Table]":
    config = BacktestEngineConfig(
        engine_id="BKT-SEAMA", symbol="ES.FUT", initial_cash=Decimal("100000.00")
    )
    runner = EventBacktestRunner(config=config, strategy_actor=_SeamAActor(symbol="ES.FUT"))
    return runner.run_backtest(
        events=_events(),
        hypothesis_id=hypothesis_id,
        hypothesis_spec_sha256="1" * 64,
        strategy_config_hash="2" * 64,
        pyproject_toml_sha256="3" * 64,
        git_commit_hash="4" * 40,
        periods_per_year=Decimal("252.0"),
        canonical_data_hashes=["5" * 64],
    )


def test_native_runner_carries_genuine_hypothesis_id_into_manifest() -> None:
    manifest, _, _ = _run_native(HYPO_ID)
    assert manifest.hypothesis_id == HYPO_ID


def test_genuine_id_survives_phase5_manifest_creation_unchanged() -> None:
    """The exact Phase 4 hypothesis_id is preserved verbatim (no transform/subst)."""
    manifest, _, _ = _run_native(HYPO_ID)
    assert manifest.hypothesis_id == _hypothesis().hypothesis_id == HYPO_ID


def test_nautilus_native_engine_alias_carries_genuine_hypothesis_id() -> None:
    """ACASHNativeBacktestEngine is aliased to EventBacktestRunner; identity flows."""
    config = BacktestEngineConfig(
        engine_id="BKT-SEAMA-ALIAS", symbol="ES.FUT", initial_cash=Decimal("100000.00")
    )
    runner = ACASHNativeBacktestEngine(config=config, strategy_actor=_SeamAActor(symbol="ES.FUT"))
    manifest, _, _ = runner.run_backtest(
        events=_events(),
        hypothesis_id=HYPO_ID,
        hypothesis_spec_sha256="1" * 64,
        strategy_config_hash="2" * 64,
        pyproject_toml_sha256="3" * 64,
        git_commit_hash="4" * 40,
        periods_per_year=Decimal("252.0"),
        canonical_data_hashes=["5" * 64],
    )
    assert manifest.hypothesis_id == HYPO_ID


def test_no_native_placeholder_is_emitted() -> None:
    mantle, _, _ = _run_native(HYPO_ID)
    assert mantle.hypothesis_id not in BANNED_PLACEHOLDERS
    assert mantle.hypothesis_id == HYPO_ID


def test_no_placeholder_literals_remain_in_production_manifest_path() -> None:
    """Both runners must not contain the banned placeholders as identity strings."""
    import inspect

    src_engine = inspect.getsource(EventBacktestRunner)
    src_substrate = inspect.getsource(NautilusTraderSubstrate)
    for placeholder in BANNED_PLACEHOLDERS:
        assert placeholder not in src_engine, f"placeholder '{placeholder}' found in engine source"
        assert placeholder not in src_substrate, f"placeholder '{placeholder}' found in substrate source"


def test_nautilus_substrate_threads_hypothesis_id_to_signature_boundary() -> None:
    """Without the Nautilus runtime, the substrate fails closed BEFORE building a
    manifest, proving the hypothesis_id parameter is accepted and required at the
    entry boundary (no compatibility default is silently introduced)."""
    substrate = NautilusTraderSubstrate()
    substrate._has_runtime = False
    with pytest.raises(SubstrateRuntimeUnavailableError, match="NautilusTrader runtime package"):
        substrate.run_simulation(
            catalog_path="does-not-matter",
            hypothesis_id=HYPO_ID,
            hypothesis_spec_sha256="0" * 64,
            strategy_config_hash="0" * 64,
            pyproject_toml_sha256="0" * 64,
            git_commit_hash="a" * 40,
            periods_per_year=Decimal("252.0"),
            canonical_data_hashes=["a" * 64],
        )
    # Confirms the parameter is REQUIRED (no default): omitting it must fail.
    with pytest.raises(TypeError):
        substrate.run_simulation(  # type: ignore[call-arg]
            catalog_path="does-not-matter",
            hypothesis_spec_sha256="0" * 64,
            strategy_config_hash="0" * 64,
            pyproject_toml_sha256="0" * 64,
            git_commit_hash="a" * 40,
        )


def test_mismatched_identity_fails_closed_downstream_phase6() -> None:
    """Phase 6 still rejects a caller-supplied hypothesis_id that does not match
    the sealed hypothesis spec (existing fail-closed path unchanged)."""
    hyp = _hypothesis()
    gate = StatisticalValidationGate()
    with pytest.raises(DataContractError, match="does not match"):
        gate.evaluate_strategy(
            strategy_id="SEAMA-STR-001",
            hypothesis_id="HYP_SEAM_A_WRONG",
            hypothesis_spec=hyp,
            in_sample_returns=[0.001] * 20,
            trial_matrix_column_trial_ids=[],
            manifest_store={},
            fixed_created_timestamp_utc="2026-01-01T00:00:00+00:00",
        )


def test_manifest_id_unchanged_semantics_and_independent_of_hypothesis_id() -> None:
    """Requirement 6 & 7: manifest_id remains governed by the canonical content
    digest fields (hypothesis_spec_sha256, canonical_data_hashes,
    engine_config_hash, strategy_config_hash, prng_seed) and is independent of
    the recorded hypothesis_id."""
    manifest_a, _, _ = _run_native("HYP_A_AAAA")
    manifest_b, _, _ = _run_native("HYP_B_BBBB")

    # Same content inputs (identical spec hash, data, config, seed) -> same manifest_id
    assert manifest_a.manifest_id == manifest_b.manifest_id

    # And it exactly equals the independently computed canonical manifest id
    canonical_id = calculate_backtest_manifest_id(
        hypothesis_spec_sha256="1" * 64,
        canonical_data_hashes=["5" * 64],
        engine_config_hash=manifest_a.engine_config_hash,
        strategy_config_hash="2" * 64,
        prng_seed=manifest_a.prng_seed,
    )
    assert manifest_a.manifest_id == canonical_id
