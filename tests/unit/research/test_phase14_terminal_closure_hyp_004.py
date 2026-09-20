"""Unit Tests: Phase 14 HYP_004 / MEC-0014A Terminal Research Closure.

Enforces:
    1. HYP_004 appears in terminal registry.
    2. HYP_004 resurrection is rejected.
    3. HYP_003 terminal behavior remains unchanged.
    4. Terminal manifest binds exact upstream hashes.
    5. Terminal manifest records primary NOT_ACCEPTED.
    6. Terminal manifest records R2_OS exactly.
    7. Terminal manifest records log robustness result exactly.
    8. External holdout consumed = false.
    9. Paper false.
    10. Live false.
    11. Capital = 0.00.
    12. NO_REAL_ORDERS = true.
    13. No future research step is auto-authorized.
    14. No empirical calculations occur in closure code.
    15. No network access exists in closure path.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, cast
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.research.reinception import (
    ResearchInceptionProposal,
    ResearchReInceptionGate,
    TERMINAL_HYPOTHESIS_REGISTRY,
)
from acash.research.schema import (
    CostModelConfig,
    ExpectedDirection,
    InvalidationCriteria,
    SplitPolicy,
)

BASE_DIR = Path(__file__).resolve().parents[3]
TERMINAL_MANIFEST_PATH = BASE_DIR / "docs/phase14/manifests/terminal_decision_HYP_004.json"
TERMINAL_DOSSIER_PATH = BASE_DIR / "docs/phase14/hyp_004_terminal_closure_dossier.md"


@pytest.fixture
def valid_proposal() -> ResearchInceptionProposal:
    """Construct a structurally valid candidate inception proposal."""
    return ResearchInceptionProposal(
        candidate_hypothesis_id="HYP_TEST_CLOSURE_001",
        candidate_hypothesis_version="1.0.0",
        economic_rationale="Empirical mean-reversion following orderbook liquidity imbalance depletion.",
        target_symbol="EURUSD",
        target_timeframe="M5",
        feature_dependencies=["orderbook_microstructure_imbalance"],
        parameter_search_grid={"lookback": [3, 5, 8], "threshold": [1.0, 2.0]},
        planned_trial_count=6,
        target_horizons=[1, 6],
        primary_horizon=1,
        expected_direction=ExpectedDirection.SHORT,
        invalidation_criteria=InvalidationCriteria(
            min_in_sample_rank_ic=Decimal("0.025"),
            min_hac_t_stat=Decimal("2.00"),
        ),
        cost_model=CostModelConfig(
            quoted_spread_bps=Decimal("1.0"),
            roundtrip_broker_fee_bps=Decimal("0.5"),
            fixed_slippage_bps=Decimal("0.5"),
        ),
        proposed_dataset_id="DS_EURUSD_M5_2025_DE_NOVO_001",
        proposed_data_window=("2025-01-01T00:00:00+00:00", "2025-06-30T23:59:00+00:00"),
        proposed_split_policy=SplitPolicy(),
        author="ResearchAgent",
    )


def _unpack_canonical(obj: Any) -> Any:
    if isinstance(obj, dict):
        if "__type__" in obj and "value" in obj:
            return _unpack_canonical(obj["value"])
        return {k: _unpack_canonical(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_unpack_canonical(x) for x in obj]
    return obj


@pytest.fixture
def terminal_manifest_data() -> Dict[str, Any]:
    with open(TERMINAL_MANIFEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    unpacked = _unpack_canonical(data)
    assert isinstance(unpacked, dict)
    return cast(Dict[str, Any], unpacked)


def test_01_hyp_004_in_terminal_registry() -> None:
    """1. Verify that HYP_004 is explicitly registered in TERMINAL_HYPOTHESIS_REGISTRY."""
    assert "HYP_004" in TERMINAL_HYPOTHESIS_REGISTRY


def test_02_hyp_004_resurrection_rejected(
    valid_proposal: ResearchInceptionProposal,
    tmp_path: Path,
) -> None:
    """2. Verify that attempting to re-register or resurrect HYP_004 fails closed immediately."""
    proposal = valid_proposal.model_copy(update={"candidate_hypothesis_id": "HYP_004"})
    with pytest.raises(DataContractError, match="BLOCKED_MUTATION_VIOLATION.*permanently TERMINALLY_FALSIFIED"):
        ResearchReInceptionGate.evaluate_reinception_proposal(
            proposal=proposal,
            hypotheses_dir=tmp_path,
        )


def test_03_hyp_003_terminal_behavior_unchanged(
    valid_proposal: ResearchInceptionProposal,
    tmp_path: Path,
) -> None:
    """3. Verify that HYP_003 remains in terminal registry and is strictly rejected."""
    assert "HYP_003" in TERMINAL_HYPOTHESIS_REGISTRY
    proposal = valid_proposal.model_copy(update={"candidate_hypothesis_id": "HYP_003"})
    with pytest.raises(DataContractError, match="BLOCKED_MUTATION_VIOLATION.*permanently TERMINALLY_FALSIFIED"):
        ResearchReInceptionGate.evaluate_reinception_proposal(
            proposal=proposal,
            hypotheses_dir=tmp_path,
        )


def test_04_terminal_manifest_binds_exact_upstream_hashes(terminal_manifest_data: Dict[str, Any]) -> None:
    """4. Verify that the terminal manifest binds exact upstream hashes."""
    lineage = terminal_manifest_data["upstream_governance_lineage"]
    assert lineage["hypothesis_sha256"] == "fc07b8aff8c580edd437a299be704a5d19b0cb3dcce65024d01a0dc3f771667d"
    assert lineage["preregistration_sha256"] == "1e5100f6733951c61d52494028b347164c7ae457794df23fa3766b7a738782ce"
    assert lineage["r1_manifest_sha256"] == "eacd98963f51b759b43ba8565aecbc43432f93acd9386b3c20bec8184712bd5b"
    assert lineage["r2_manifest_sha256"] == "25b5ae6c4769064459709bb09bbc759e02f7b340c4d4e94b4ff9442e3082ef71"
    assert lineage["r3_manifest_sha256"] == "56d4f79c1e563a81c0b601f695023a5da54cac58e5b9a19a0be9108b3ca4ef40"
    assert lineage["r4_manifest_sha256"] == "d3e5298ccf66da9854bc84c1ca64aeec112c8e907b96f5fd36a2d8e3f194b9a7"
    assert lineage["log_robustness_manifest_sha256"] == "f749a0d39a88d9ff670023e3eaa0db75744656e2b79516921c4d7a3727d04fb6"
    assert lineage["lineage_reconciliation_commit"] == "38310091a2a8588ee22aea139b606e0e6d02df6d"


def test_05_terminal_manifest_records_primary_not_accepted(terminal_manifest_data: Dict[str, Any]) -> None:
    """5. Verify that the primary outcome is recorded as PRIMARY_REPLICATION_NOT_ACCEPTED."""
    primary = terminal_manifest_data["sealed_empirical_evidence"]["primary_simple_return_replication"]
    assert primary["outcome"] == "PRIMARY_REPLICATION_NOT_ACCEPTED"
    assert primary["sample_size_t"] == 1489
    assert primary["beta_hat"] == "0.022488683629000000"
    assert primary["two_sided_p_value"] == "0.523533251922000000"
    assert primary["r_squared"] == "0.002641292938333817"


def test_06_terminal_manifest_records_r2_os_exactly(terminal_manifest_data: Dict[str, Any]) -> None:
    """6. Verify that the internal OOS diagnostic R2_OS is recorded exactly."""
    oos = terminal_manifest_data["sealed_empirical_evidence"]["internal_oos_diagnostic"]
    assert oos["r2_os"] == "-0.048358069265733747"
    assert oos["sample_size_train"] == 739
    assert oos["sample_size_eval"] == 750


def test_07_terminal_manifest_records_log_robustness_result_exactly(terminal_manifest_data: Dict[str, Any]) -> None:
    """7. Verify that the log robustness result is recorded exactly."""
    log_rob = terminal_manifest_data["sealed_empirical_evidence"]["log_return_robustness"]
    assert log_rob["beta_log"] == "0.023451449509000000"
    assert log_rob["two_sided_p_value"] == "0.508408655057000000"
    assert log_rob["r_squared"] == "0.002909813254966642"
    assert log_rob["classification"] == "ROBUSTNESS_CONSISTENT_WITH_PRIMARY_NON_ACCEPTANCE"


def test_08_external_holdout_consumed_is_false(terminal_manifest_data: Dict[str, Any]) -> None:
    """8. Verify that external_holdout_consumed is False and state is SEALED."""
    invariants = terminal_manifest_data["holdout_and_governance_invariants"]
    assert invariants["external_holdout_consumed"] is False
    assert invariants["external_holdout_state"] == "SEALED"
    assert invariants["external_holdout_window"] == ["2023-01-01", "2026-12-31"]


def test_09_paper_false(terminal_manifest_data: Dict[str, Any]) -> None:
    """9. Verify paper trading authority is false."""
    invariants = terminal_manifest_data["holdout_and_governance_invariants"]
    assert invariants["paper_authorized"] is False


def test_10_live_false(terminal_manifest_data: Dict[str, Any]) -> None:
    """10. Verify live trading authority is false."""
    invariants = terminal_manifest_data["holdout_and_governance_invariants"]
    assert invariants["live_authorized"] is False


def test_11_capital_zero(terminal_manifest_data: Dict[str, Any]) -> None:
    """11. Verify capital authority is exactly $0.00."""
    invariants = terminal_manifest_data["holdout_and_governance_invariants"]
    assert invariants["capital_authority_usd"] == "0.00"


def test_12_no_real_orders_true(terminal_manifest_data: Dict[str, Any]) -> None:
    """12. Verify NO_REAL_ORDERS is true."""
    invariants = terminal_manifest_data["holdout_and_governance_invariants"]
    assert invariants["NO_REAL_ORDERS"] is True


def test_13_no_future_research_step_auto_authorized(terminal_manifest_data: Dict[str, Any]) -> None:
    """13. Verify that next research action returns to new mechanism inception."""
    invariants = terminal_manifest_data["holdout_and_governance_invariants"]
    assert invariants["further_rescue_analysis_authorized"] is False
    assert invariants["MEC_0014B_authorized"] is False
    assert invariants["next_research_action"] == "RETURN_TO_NEW_MECHANISM_INCEPTION"


def test_14_no_empirical_calculations_occur_in_closure_code() -> None:
    """14. Verify that closure dossier and manifest do not contain execution logic."""
    assert TERMINAL_DOSSIER_PATH.is_file()
    content = TERMINAL_DOSSIER_PATH.read_text(encoding="utf-8")
    assert "def " not in content
    assert "import " not in content


def test_15_no_network_access_in_closure_path() -> None:
    """15. Verify that no network client or request calls exist in closure manifest."""
    assert TERMINAL_MANIFEST_PATH.is_file()
    text = TERMINAL_MANIFEST_PATH.read_text(encoding="utf-8")
    assert "http://" not in text
    assert "https://" not in text
    assert "alpaca" not in text.lower()
