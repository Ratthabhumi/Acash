"""Governance tests for HYP_009 pre-R1 semantic conformance.

Implementation-only invariants. No network calls, no market-data reads, no
return calculations, no signal generation. Asserts exclusively on committed
governance artifacts.
"""

import json
from pathlib import Path
from typing import Any, Dict, cast

REPO_ROOT = Path(__file__).resolve().parents[3]
HYPOTHESIS_RECORD = REPO_ROOT / "docs" / "phase14" / "hypotheses" / "HYP_009.json"
CONFORMANCE_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "phase14"
    / "manifests"
    / "HYP_009_PRE_R1_SEMANTIC_CONFORMANCE.json"
)
CONFORMANCE_DOC = (
    REPO_ROOT
    / "docs"
    / "phase14"
    / "phase14_pre_r1_semantic_conformance_record_HYP_009.md"
)
INCEPTION_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "phase14"
    / "manifests"
    / "CORE_001_HYP_009_RESEARCH_INCEPTION.json"
)


def _load(path: Path) -> Dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_hyp_009_r1_sealed_state_recorded() -> None:
    # Superseded by the R1 seal (manifest_r1_HYP_009.json): the hypothesis record
    # transitioned PROPOSED_NOT_PREREGISTERED -> R1_PREREGISTERED_SEALED, while the
    # pre-R1 conformance manifest itself remains a historical PROPOSED-era record.
    h = _load(HYPOTHESIS_RECORD)
    m = _load(CONFORMANCE_MANIFEST)
    assert h["state"] == "R1_PREREGISTERED_SEALED"
    assert m["state"] == "PROPOSED_NOT_PREREGISTERED"
    assert m["semantic_conformance_status"] == (
        "PASS_WITH_NON_BINDING_LEGACY_SCHEMA_ADAPTERS"
    )


def test_stub_values_preserved_verbatim() -> None:
    h = _load(HYPOTHESIS_RECORD)
    assert h["target_horizons"] == [21]
    assert h["primary_horizon"] == 21
    assert h["expected_direction"] == "LONG"


def test_conformance_manifest_classifies_stubs_as_non_binding() -> None:
    m = _load(CONFORMANCE_MANIFEST)
    assert (
        m["non_binding_classification"]
        == "NON_BINDING_SCHEMA_COMPATIBILITY_METADATA_ONLY"
    )
    assert set(m["non_binding_fields"]) == {
        "expected_direction",
        "target_horizons",
        "primary_horizon",
    }
    assert m["target_horizons_stub_value"] == [21]
    assert m["primary_horizon_stub_value"] == 21
    assert m["expected_direction_stub_value"] == "LONG"
    assert m["hypothesis_record_mutated"] is False


def test_binding_authority_remains_core_inception_contract() -> None:
    m = _load(CONFORMANCE_MANIFEST)
    assert "docs/phase14/CORE_001_HYP_009_RESEARCH_INCEPTION.md" in (
        m["binding_strategy_authority"]
    )
    assert "docs/phase14/manifests/CORE_001_HYP_009_RESEARCH_INCEPTION.json" in (
        m["binding_strategy_authority"]
    )
    assert "docs/phase14/hypotheses/HYP_009.json:parameter_config_json" in (
        m["binding_strategy_authority"]
    )


def test_monthly_cadence_and_state_change_rebalance_binding() -> None:
    m = _load(CONFORMANCE_MANIFEST)
    assert m["monthly_signal_cadence"] is True
    assert m["state_persists_until_next_state_change"] is True
    inc = _load(INCEPTION_MANIFEST)
    assert inc["frequency"] == "MONTHLY"
    assert inc["rebalance_rule"] == "TRADE_ONLY_ON_STATE_CHANGE"


def test_no_fixed_holding_period_or_21_day_semantics() -> None:
    m = _load(CONFORMANCE_MANIFEST)
    assert m["fixed_holding_period"] is False
    assert m["fixed_21_day_exit"] is False
    assert m["fixed_21_day_prediction_target"] is False


def test_long_cash_remain_only_strategy_states() -> None:
    inc = _load(INCEPTION_MANIFEST)
    assert inc["direction_states"] == ["LONG", "CASH"]
    assert inc["short_state"] is False


def test_parameter_config_json_semantically_unchanged() -> None:
    h = _load(HYPOTHESIS_RECORD)
    params = json.loads(h["parameter_config_json"])
    assert params["signal_name"] == "10_MONTH_SIMPLE_MOVING_AVERAGE"
    assert params["lookback_month_ends"] == 10
    assert params["equality_behavior"] == "CASH"
    assert params["max_gross_leverage"] == 1.0
    assert params["volatility_targeting"] is False
    assert params["cash_return"] == 0.0
    assert params["execution_timing"] == (
        "NEXT_ELIGIBLE_REGULAR_SESSION_OPEN_AFTER_SIGNAL"
    )


def test_no_r1_no_backtest_no_performance_fields() -> None:
    m = _load(CONFORMANCE_MANIFEST)
    assert m["r1_opened"] is False
    assert m["backtest_authorized"] is False
    assert m["backtest_executed"] is False
    assert m["historical_signals_computed"] is False
    assert m["performance_fields_added"] is False


def test_no_m3_access_and_capital_locked() -> None:
    m = _load(CONFORMANCE_MANIFEST)
    assert m["m3_accessed"] is False
    assert m["paper_authorized"] is False
    assert m["live_authorized"] is False
    assert m["capital_authority_usd"] == "0.00"
    assert m["no_real_orders"] is True


def test_conformance_doc_states_binding() -> None:
    assert CONFORMANCE_DOC.is_file(), "conformance doc missing"
    text = CONFORMANCE_DOC.read_text(encoding="utf-8")
    assert "PASS_WITH_NON_BINDING_LEGACY_SCHEMA_ADAPTERS" in text
    assert "NON_BINDING_SCHEMA_COMPATIBILITY_METADATA_ONLY" in text
    assert "AUTHORIZE_CORE_001_HYP_009_SCHEMA_SEMANTIC_CONFORMANCE_PATCH" in text
    assert "REVIEW_CORE_001_HYP_009_PROPOSAL_AND_AUTHORIZE_R1_PREREGISTRATION" in text
