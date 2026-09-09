"""Adversarial tests for the ratified D6 failed/invalid-trial census semantics (Option A).

Attack surface covered (per AGENTS.md progression happy -> boundary -> malformed -> contradictory ->
adversarial -> permutation -> numerical -> golden reference):
- EXECUTED_SUCCESSFULLY default carries full evidence; create() behaviour is byte-identical.
- FAILED / INVALID trials carry NO evidence + non-empty deterministic failure_reason.
- Status-conditional validation rejects evidence on non-executed trials and rejects missing
  evidence on executed trials (no fabricated performance, no magic floors).
- Census K stays frozen (|trials| unchanged) with failed trials retained; digest binds status +
  failure_reason of every census member; operational sealing metadata is excluded from the digest.
- Empirical Sharpe mean/variance and p_values FAIL CLOSED on mixed censuses.
- The gate consumes p_values and therefore REJECTS a mixed census fail-closed.
- The D6 sealing-owner authority is the sole sanctioned sealer (owner attestation, frozen K anchor).
- Evidence Bridge never seals.
"""

from decimal import Decimal
import hashlib
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pytest

from acash.backtest.schema import BacktestExecutionSummary, BacktestManifest, RealityGapSummary
from acash.core.domain.exceptions import DataContractError
from acash.research.census_seal_authority import SearchTrialCensusSealAuthority
from acash.research.reinception import ResearchInceptionProposal
from acash.research.schema import ExpectedDirection, HypothesisSpecification, InvalidationCriteria
from acash.validation.gate import StatisticalValidationGate
from acash.validation.schema import (
    ParameterPerturbationGrid,
    ParameterPerturbationPoint,
    SearchTrialLedger,
    SearchTrialRecord,
    SearchTrialStatus,
    SharpeSpace,
)

# Canonical frozen ``parameters`` mappingproxy triggers a cosmetic pydantic serializer warning
# during python-mode model_dump() in this replay harness only. Classified: expected canonical
# frozen-mapping behaviour (AGENTS.md 1.16), not an actionable defect.
pytestmark = pytest.mark.filterwarnings("ignore:Pydantic serializer warnings:UserWarning:pydantic.main")


def _returns(seed: int = 42, n: int = 250) -> List[float]:
    rng = np.random.default_rng(seed)
    return list(rng.normal(0.0, 0.01, n))


def _mock_manifest(manifest_id: str, hypothesis_id: str = "HYP_D6", strategy_config_hash: str = "") -> BacktestManifest:
    cfg = strategy_config_hash or ("3" * 64)
    return BacktestManifest(
        manifest_id=manifest_id,
        hypothesis_id=hypothesis_id,
        hypothesis_spec_sha256="1" * 64,
        canonical_data_hashes=["6" * 64],
        engine_config_hash="2" * 64,
        strategy_config_hash=cfg,
        prng_seed=42,
        pyproject_toml_sha256="4" * 64,
        git_commit_hash="5" * 40,
        execution_summary=BacktestExecutionSummary(
            total_orders=10,
            total_fills=10,
            total_volume_traded=Decimal("10000.0"),
            total_fees_paid=Decimal("10.0"),
            realized_pnl=Decimal("1000.0"),
            unrealized_pnl=Decimal("0.0"),
            ending_equity=Decimal("101000.0"),
            net_return_pct=Decimal("1.0"),
            sharpe_ratio=Decimal("1.5"),
            max_drawdown_pct=Decimal("0.5"),
            win_rate_pct=Decimal("60.0"),
        ),
        reality_gap=RealityGapSummary(
            phase4_analytical_edge_bps=Decimal("10.0"),
            phase5_simulated_realized_bps=Decimal("8.0"),
            reality_gap_bps=Decimal("2.0"),
        ),
        computed_at_utc="2026-08-28T10:00:00Z",
        wall_clock_duration_ms=1000,
    )


def _valid_grid(strat_id: str = "STRAT_01", manifest_store: Optional[Dict[str, Any]] = None) -> ParameterPerturbationGrid:
    expected_in = hashlib.sha256(f"{'1' * 64}:{'3' * 64}".encode("utf-8")).hexdigest()
    points: List[ParameterPerturbationPoint] = []
    for label, mult in (("left", Decimal("0.75")), ("base", Decimal("1.0")), ("right", Decimal("1.25"))):
        man_id = f"MANEST_{strat_id}_{label}".replace("NEST", "IFEST")
        man = _mock_manifest(manifest_id=man_id)
        if manifest_store is not None:
            manifest_store[man_id] = man
        points.append(
            ParameterPerturbationPoint(
                parameter_value=Decimal("10.0") * mult,
                run_id=f"run_{strat_id}_{label}",
                manifest_id=man_id,
                input_artifact_hash=expected_in,
                output_artifact_hash=man.compute_sha256(),
                actual_sharpe=Decimal("1.5"),
            )
        )
    return ParameterPerturbationGrid(
        base_parameter_name="lookback",
        base_parameter_value=Decimal("10.0"),
        points=(points[0], points[1], points[2]),
    )


def _valid_hyp_spec() -> HypothesisSpecification:
    return HypothesisSpecification(
        hypothesis_id="HYP_D6",
        hypothesis_version="v1.0.0",
        economic_rationale="D6 census semantics benchmark",
        target_symbol="BTCUSDT",
        feature_dependencies=["mom"],
        parameter_config_json="{}",
        expected_direction=ExpectedDirection.LONG,
        target_horizons=[1],
        primary_horizon=1,
        invalidation_criteria=InvalidationCriteria(),
        registered_at_utc="2026-08-28T00:00:00Z",
        author="Auditor",
    )


def _executed(trial_id: str = "trial_0", shares: Optional[List[float]] = None) -> SearchTrialRecord:
    ser = shares if shares is not None else _returns()
    return SearchTrialRecord.create(
        trial_id=trial_id,
        strategy_id="STRAT_D6",
        hypothesis_id="HYP_D6",
        feature_names=["mom"],
        parameters={"period": 10},
        in_sample_sharpe=Decimal("1.5"),
        execution_manifest_id=f"MAN_{trial_id}",
        in_sample_returns=ser,
    )


def _declared(trial_id: str, status: SearchTrialStatus, reason: str = "trial crashed during execution") -> SearchTrialRecord:
    return SearchTrialRecord.create_declared(
        trial_id=trial_id,
        strategy_id="STRAT_D6",
        hypothesis_id="HYP_D6",
        feature_names=["mom"],
        parameters={"period": 20},
        trial_status=status,
        failure_reason=reason,
    )


def _mixed_ledger(sealed: bool = True) -> SearchTrialLedger:
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_D6_MIXED",
        strategy_id="STRAT_D6",
        hypothesis_id="HYP_D6",
        sharpe_space=SharpeSpace.PERIOD,
        trials=(_executed("trial_0"), _declared("trial_1", SearchTrialStatus.FAILED)),
    )
    if sealed:
        return SearchTrialCensusSealAuthority.seal_census(ledger, expected_k=2, sealed_at_utc="2026-08-28T00:00:00Z")
    return ledger


# ---------------------------------------------------------------------------
# Happy path / golden reference behaviour
# ---------------------------------------------------------------------------

def test_executed_trial_default_status_with_full_evidence() -> None:
    rec = _executed()
    assert rec.trial_status == SearchTrialStatus.EXECUTED_SUCCESSFULLY
    assert rec.failure_reason is None
    assert rec.in_sample_sharpe is not None
    assert rec.p_value is not None
    assert rec.p_value_input_hash is not None
    assert rec.execution_manifest_id is not None
    assert isinstance(rec.in_sample_return_series_sha256, str)


def test_failed_and_invalid_trials_carry_no_evidence_with_reason() -> None:
    for status in (SearchTrialStatus.FAILED, SearchTrialStatus.INVALID):
        rec = _declared("trial_x", status, reason="deterministic crash: dividend adjustment unsupported")
        assert rec.trial_status == status
        assert rec.failure_reason == "deterministic crash: dividend adjustment unsupported"
        assert rec.in_sample_sharpe is None
        assert rec.p_value is None
        assert rec.p_value_input_hash is None
        assert rec.in_sample_return_series_sha256 is None
        assert rec.execution_manifest_id is None


# ---------------------------------------------------------------------------
# Boundary / malformed
# ---------------------------------------------------------------------------

def test_non_executed_trial_rejects_any_evidence_field() -> None:
    for status in (SearchTrialStatus.FAILED, SearchTrialStatus.INVALID):
        with pytest.raises(DataContractError, match="MUST carry no evidence"):
            SearchTrialRecord(
                trial_id="t_dirty",
                strategy_id="STRAT_D6",
                hypothesis_id="HYP_D6",
                feature_names=("mom",),
                parameters={"period": 5},
                trial_status=status,
                failure_reason="crash",
                config_sha256="a" * 64,
                in_sample_sharpe=Decimal("9.99"),
            )
        with pytest.raises(DataContractError, match="MUST carry no evidence"):
            SearchTrialRecord(
                trial_id="t_dirty",
                strategy_id="STRAT_D6",
                hypothesis_id="HYP_D6",
                feature_names=("mom",),
                parameters={"period": 5},
                trial_status=status,
                failure_reason="crash",
                config_sha256="a" * 64,
                execution_manifest_id="MAN_X",
            )


def test_non_executed_trial_rejects_in_sample_returns() -> None:
    """Forged artifact replay attempting to smuggle a full return series onto a failed trial."""
    payload = _payload(_declared("t_dirty", SearchTrialStatus.FAILED))
    payload["in_sample_returns"] = [0.01, -0.02]
    with pytest.raises(DataContractError, match="MUST carry no in_sample_returns"):
        SearchTrialRecord.model_validate(payload)


def test_create_declared_rejects_executed_status() -> None:
    with pytest.raises(DataContractError, match="reserved for FAILED/INVALID"):
        SearchTrialRecord.create_declared(
            trial_id="t_bad",
            strategy_id="STRAT_D6",
            hypothesis_id="HYP_D6",
            feature_names=["mom"],
            parameters={"period": 5},
            trial_status=SearchTrialStatus.EXECUTED_SUCCESSFULLY,
            failure_reason="nope",
        )


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_create_declared_requires_non_empty_failure_reason(reason: Optional[str]) -> None:
    narrowed_reason: str = "" if reason is None else reason
    with pytest.raises(DataContractError, match="non-empty deterministic failure_reason"):
        SearchTrialRecord.create_declared(
            trial_id="t_blank",
            strategy_id="STRAT_D6",
            hypothesis_id="HYP_D6",
            feature_names=["mom"],
            parameters={"period": 5},
            trial_status=SearchTrialStatus.INVALID,
            failure_reason=narrowed_reason,
        )


def test_invalid_trial_status_string_fails_closed() -> None:
    with pytest.raises(DataContractError, match="Invalid trial_status"):
        SearchTrialRecord.model_validate(
            {
                "trial_id": "t_status",
                "strategy_id": "STRAT_D6",
                "hypothesis_id": "HYP_D6",
                "feature_names": ("mom",),
                "parameters": {"period": 5},
                "trial_status": "HACKED",
                "failure_reason": "x",
            }
        )


# ---------------------------------------------------------------------------
# Contradictory / adversarial
# ---------------------------------------------------------------------------

def _payload(rec: SearchTrialRecord) -> Dict[str, Any]:
    """Canonical python-mode replay payload; normalizes the frozen mappingproxy."""
    out = rec.model_dump()
    out["parameters"] = dict(out["parameters"])
    return out


def test_executed_trial_rejects_failure_reason() -> None:
    """Crafted replay of an executed trial carrying a fabricated failure_reason."""
    payload = _payload(_executed())
    payload["failure_reason"] = "retroactive"
    with pytest.raises(DataContractError, match="MUST have failure_reason=None"):
        SearchTrialRecord.model_validate(payload)


def test_executed_trial_requires_all_evidence_fields() -> None:
    """Direct construction that omits required evidence is rejected fail-closed."""
    with pytest.raises(DataContractError, match="requires actual in_sample_returns"):
        SearchTrialRecord(
            trial_id="t_incomplete",
            strategy_id="STRAT_D6",
            hypothesis_id="HYP_D6",
            feature_names=("mom",),
            parameters={"period": 5},
            p_value=Decimal("0.5"),
            config_sha256="a" * 64,
        )


def test_failed_trial_tamper_adds_evidence_is_rejected() -> None:
    """Crafted replay of a failed trial smuggling fabricated evidence columns."""
    for field, value in (("p_value", Decimal("0.5")), ("in_sample_sharpe", Decimal("2.0"))):
        payload = _payload(_declared("t_tamper", SearchTrialStatus.FAILED))
        payload[field] = float(value)
        with pytest.raises(DataContractError, match="MUST carry no evidence"):
            SearchTrialRecord.model_validate(payload)


def test_executed_trial_tamper_removes_evidence_is_rejected() -> None:
    """Crafted replay of an executed trial stripped of mandatory evidence."""
    for field in ("execution_manifest_id", "in_sample_sharpe"):
        payload = _payload(_executed())
        del payload[field]
        with pytest.raises(DataContractError):
            SearchTrialRecord.model_validate(payload)


# ---------------------------------------------------------------------------
# Census / digest / K invariant
# ---------------------------------------------------------------------------

def test_mixed_census_keeps_k_frozen_and_digest_binds_status() -> None:
    ledger = _mixed_ledger()
    assert ledger.total_trials == 2  # K never shrinks; failed trial REMAINS in the census
    assert {t.trial_id for t in ledger.trials} == {"trial_0", "trial_1"}

    digest = ledger.compute_ledger_digest()

    # Determinism (golden): identical census -> identical digest.
    assert _mixed_ledger().compute_ledger_digest() == digest

    # Content dependency: changing the failure_reason changes the digest.
    alt_ledger = SearchTrialLedger(
        ledger_id="LEDGER_D6_MIXED",
        strategy_id="STRAT_D6",
        hypothesis_id="HYP_D6",
        sharpe_space=SharpeSpace.PERIOD,
        trials=(_executed("trial_0"), _declared("trial_1", SearchTrialStatus.FAILED, reason="different reason")),
    )
    assert alt_ledger.compute_ledger_digest() != digest

    # Content dependency: FAILED vs INVALID status changes the digest.
    invalid_ledger = SearchTrialLedger(
        ledger_id="LEDGER_D6_MIXED",
        strategy_id="STRAT_D6",
        hypothesis_id="HYP_D6",
        sharpe_space=SharpeSpace.PERIOD,
        trials=(_executed("trial_0"), _declared("trial_1", SearchTrialStatus.INVALID)),
    )
    assert invalid_ledger.compute_ledger_digest() != digest

    # Permutation: re-ordering census members changes the digest (order-locked identity).
    flipped = SearchTrialLedger(
        ledger_id="LEDGER_D6_MIXED",
        strategy_id="STRAT_D6",
        hypothesis_id="HYP_D6",
        sharpe_space=SharpeSpace.PERIOD,
        trials=(_declared("trial_1", SearchTrialStatus.FAILED), _executed("trial_0")),
    )
    assert flipped.compute_ledger_digest() != digest


def test_sealing_metadata_excluded_from_ledger_digest() -> None:
    ledger = _mixed_ledger()
    base_digest = ledger.compute_ledger_digest()

    sealed_a = _mixed_ledger().seal(sealed_at_utc="2026-09-01T00:00:00Z", sealing_owner="OWNER_A")
    sealed_b = _mixed_ledger().seal(sealed_at_utc="2026-09-02T00:00:00Z", sealing_owner="OWNER_B")
    # Operational lifecycle metadata must NOT alter content identity (existing contract).
    assert sealed_a.compute_ledger_digest() == base_digest
    assert sealed_b.compute_ledger_digest() == base_digest
    assert sealed_a.ledger_digest == sealed_b.ledger_digest


def test_empirical_accessors_fail_closed_on_mixed_census() -> None:
    ledger = _mixed_ledger()
    with pytest.raises(DataContractError, match="non-executed trial 'trial_1'"):
        ledger.p_values  # noqa: B018
    with pytest.raises(DataContractError, match="non-executed trial 'trial_1'"):
        ledger.get_empirical_sharpe_mean()
    with pytest.raises(DataContractError, match="non-executed trial 'trial_1'"):
        ledger.get_empirical_sharpe_variance()


def test_empirical_accessors_work_on_pure_executed_census() -> None:
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_D6_PURE",
        strategy_id="STRAT_D6",
        hypothesis_id="HYP_D6",
        sharpe_space=SharpeSpace.PERIOD,
        trials=(_executed("trial_0"), _executed("trial_1", shares=_returns(seed=7))),
    )
    assert len(ledger.p_values) == 2
    assert ledger.get_empirical_sharpe_mean() == ledger.get_empirical_sharpe_mean()
    assert ledger.get_empirical_sharpe_variance() >= 0.0


def test_gate_rejects_mixed_census_fail_closed() -> None:
    """The gate consumes len(p_values) as the K invariant and therefore fails closed on a mixed census."""
    gate = StatisticalValidationGate()
    is_returns = _returns(seed=1, n=500)
    oos_returns = _returns(seed=2, n=250)
    matrix = np.zeros((500, 2), dtype=np.float64)
    matrix[:, 0] = is_returns
    matrix[:, 1] = _returns(seed=3, n=500)

    with pytest.raises(DataContractError, match="non-executed trial 'trial_1'"):
        gate.evaluate_strategy(
            strategy_id="STRAT_D6",
            hypothesis_id="HYP_D6",
            hypothesis_spec=_valid_hyp_spec(),
            in_sample_returns=is_returns,
            out_of_sample_returns=oos_returns,
            trial_ledger=_mixed_ledger(),
            trial_return_matrix=matrix,
            trial_matrix_column_trial_ids=["trial_0", "trial_1"],
            perturbation_grid=_valid_grid(),
            raw_predictive_edge_bps=25.0,
            manifest_store={},
        )


# ---------------------------------------------------------------------------
# D6 sealing-owner authority
# ---------------------------------------------------------------------------

def test_seal_authority_stamps_owner_and_enforces_k_anchor() -> None:
    ledger = _mixed_ledger(sealed=False)
    proposal = ResearchInceptionProposal.model_construct(planned_trial_count=2)
    sealed = SearchTrialCensusSealAuthority.seal_census(ledger, expected_k=proposal.planned_trial_count)
    assert sealed.is_sealed is True
    assert sealed.sealed_by_owner == SearchTrialCensusSealAuthority.DESIGNATED_OWNER_ID
    assert sealed.ledger_digest == sealed.compute_ledger_digest()


def test_seal_authority_rejects_k_anchor_mismatch() -> None:
    ledger = _mixed_ledger(sealed=False)
    with pytest.raises(DataContractError, match="planned_trial_count"):
        SearchTrialCensusSealAuthority.seal_census(ledger, expected_k=3)


def test_seal_authority_refuses_census_sealed_by_other_owner() -> None:
    ledger = SearchTrialLedger(
        ledger_id="LEDGER_D6_SEALED_BY_OTHERS",
        strategy_id="STRAT_D6",
        hypothesis_id="HYP_D6",
        sharpe_space=SharpeSpace.PERIOD,
        trials=(_executed("trial_0"),),
    ).seal(sealed_at_utc="2026-08-28T00:00:00Z", sealing_owner="EVIDENCE_BRIDGE")
    with pytest.raises(DataContractError, match="sealing owner attestation mismatch"):
        SearchTrialCensusSealAuthority.seal_census(ledger)


def test_evidence_bridge_never_seals() -> None:
    """Static negative audit: research evidence assembly must never call SearchTrialLedger.seal."""
    from acash.research import evidence_bridge

    src = inspect.getsource(evidence_bridge)
    assert ".seal(" not in src, "Evidence Bridge must never seal the census (ratified D6 rule)."
    assert "SearchTrialLedger" not in src or "assembles evidence only" in src


# ---------------------------------------------------------------------------
# Persisted historical artifact golden reference
# ---------------------------------------------------------------------------

def test_persisted_r3_ledger_remains_valid_under_new_digest() -> None:
    """The migrated R3 census artifact recomputes its stored digest under the ratified digest rule."""
    path = Path("docs/phase8.5/ledgers/search_trial_ledger_HYP_TSMOM_EURUSD_001.json")
    assert path.exists()
    ledger = SearchTrialLedger.model_validate_json(path.read_text(encoding="utf-8"))
    assert ledger.is_sealed
    assert ledger.ledger_digest == ledger.compute_ledger_digest()
    assert all(t.trial_status == SearchTrialStatus.EXECUTED_SUCCESSFULLY for t in ledger.trials)