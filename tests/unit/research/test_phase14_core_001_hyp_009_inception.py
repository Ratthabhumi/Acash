"""Governance tests for CORE-001 / HYP_009 research inception.

Implementation-only invariants. No market-data network calls, no signal
computation, no performance evaluation. Asserts exclusively on committed
governance artifacts.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, cast

REPO_ROOT = Path(__file__).resolve().parents[3]
INCEPTION_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "phase14"
    / "manifests"
    / "CORE_001_HYP_009_RESEARCH_INCEPTION.json"
)
INCEPTION_DOC = REPO_ROOT / "docs" / "phase14" / "CORE_001_HYP_009_RESEARCH_INCEPTION.md"
HYPOTHESIS_RECORD = REPO_ROOT / "docs" / "phase14" / "hypotheses" / "HYP_009.json"


def _load_manifest() -> Dict[str, Any]:
    assert INCEPTION_MANIFEST.is_file(), "inception manifest missing"
    return cast(Dict[str, Any], json.loads(INCEPTION_MANIFEST.read_text(encoding="utf-8")))


def _load_hypothesis() -> Dict[str, Any]:
    assert HYPOTHESIS_RECORD.is_file(), "HYP_009 hypothesis record missing"
    return cast(Dict[str, Any], json.loads(HYPOTHESIS_RECORD.read_text(encoding="utf-8")))


def test_core_identity_and_state() -> None:
    m = _load_manifest()
    assert m["core_id"] == "CORE-001"
    assert m["hypothesis_id"] == "HYP_009"
    assert m["state"] == "PROPOSED_NOT_PREREGISTERED"
    assert m["formal_r1_registration"] is False
    assert m["research_re_inception_gate_invoked"] is False


def test_instrument_frequency_decision_date() -> None:
    m = _load_manifest()
    assert m["instrument"] == "SPY"
    assert m["frequency"] == "MONTHLY"
    assert (
        m["decision_date_rule"]
        == "LAST_REGULAR_TRADING_SESSION_OF_EACH_CALENDAR_MONTH"
    )


def test_signal_is_10_month_sma_with_cash_on_equality() -> None:
    m = _load_manifest()
    assert m["signal_name"] == "10_MONTH_SIMPLE_MOVING_AVERAGE"
    assert m["lookback_month_ends"] == 10
    assert m["equality_behavior"] == "CASH"
    assert m["tolerance_band"] is False
    assert m["hysteresis"] is False


def test_long_cash_only_no_short_no_stop() -> None:
    m = _load_manifest()
    assert m["direction_states"] == ["LONG", "CASH"]
    assert m["short_state"] is False
    assert m["stop_loss"] is False
    assert m["trailing_stop"] is False
    assert m["confirmation_indicator"] is False
    assert m["secondary_filter"] is False
    assert m["volatility_filter"] is False
    assert m["liquidity_filter"] is False
    assert m["macro_filter"] is False
    assert m["machine_learning"] is False
    assert m["discretionary_override"] is False


def test_position_sizing_no_leverage_no_vol_targeting() -> None:
    m = _load_manifest()
    sizing = m["position_sizing"]
    assert m["position_sizing"]["max_gross_leverage"] == 1.0
    assert sizing["volatility_targeting"] is False
    assert sizing["margin_leverage"] is False
    assert sizing["leveraged_etf"] is False
    assert sizing["synthetic_leverage"] is False
    assert sizing["short_exposure"] is False


def test_cash_return_zero_and_benchmark() -> None:
    m = _load_manifest()
    assert m["cash_return"] == 0.0
    assert m["benchmark"] == "SPY_BUY_AND_HOLD"
    assert m["numerical_gates_authorized"] is False


def test_signal_vs_execution_series_roles() -> None:
    m = _load_manifest()
    assert (
        m["signal_series_role"]
        == "TOTAL_RETURN_OR_EQUIVALENT_CAUSALLY_RECONSTRUCTED_SERIES"
    )
    assert m["execution_price_role"] == "RAW_MARKET_PRICES"


def test_timing_contract_next_session_open() -> None:
    m = _load_manifest()
    assert (
        m["execution_timing"]
        == "NEXT_ELIGIBLE_REGULAR_SESSION_OPEN_AFTER_SIGNAL"
    )
    assert m["same_close_execution"] is False


def test_warmup_and_rebalance_rule() -> None:
    m = _load_manifest()
    assert m["warmup_completed_month_end_observations"] == 10
    assert m["pre_warmup_behavior"] == "NO_SIGNAL_FAIL_CLOSED"
    assert m["rebalance_rule"] == "TRADE_ONLY_ON_STATE_CHANGE"
    assert m["expected_turnover_class"] == "LOW"


def test_no_performance_metrics_stored_and_backtest_locked() -> None:
    m = _load_manifest()
    assert m["performance_metrics_stored"] is False
    assert m["backtest_authorized"] is False
    assert m["backtest_executed"] is False
    assert m["sample_dates_selected"] is False


def test_m3_quarantine_paper_live_capital_locked() -> None:
    m = _load_manifest()
    assert m["m3_accessed"] is False
    assert m["quarantine_gap_accessed"] is False
    assert m["paper_authorized"] is False
    assert m["live_authorized"] is False
    assert m["capital_authority_usd"] == "0.00"
    assert m["no_real_orders"] is True


def test_open_before_r1_items_recorded() -> None:
    m = _load_manifest()
    open_items: List[str] = m["open_before_r1"]
    for item in (
        "OPEN_BEFORE_R1_TOTAL_RETURN_SIGNAL_CONSTRUCTION",
        "OPEN_BEFORE_R1_EXECUTION_COST_MODEL",
        "OPEN_BEFORE_R1_SAMPLE_PARTITION_DATES",
        "OPEN_BEFORE_R1_LOCKED_OOS_BOUNDARY",
        "OPEN_BEFORE_R1_PROSPECTIVE_BOUNDARY",
    ):
        assert item in open_items, f"missing {item}"


def test_predecessor_hyp_008_not_reused() -> None:
    m = _load_manifest()
    pred = m["predecessor_lineage"]
    assert pred["hypothesis_id"] == "HYP_008"
    assert pred["mechanism_id"] == "MEC-0018"
    assert pred["state"] == "RETIRED_BEFORE_PREREGISTRATION"
    assert pred["reused"] is False


def test_hypothesis_record_matches_manifest() -> None:
    # Superseded by the R1 seal (manifest_r1_HYP_009.json): the hypothesis record
    # transitioned to R1_PREREGISTERED_SEALED with gate lineage, while the inception
    # manifest itself remains a historical PROPOSED-era record.
    h = _load_hypothesis()
    m = _load_manifest()
    assert h["hypothesis_id"] == "HYP_009"
    assert h["core_id"] == "CORE-001"
    assert h["state"] == "R1_PREREGISTERED_SEALED"
    assert m["state"] == "PROPOSED_NOT_PREREGISTERED"
    assert h["registered_at_utc"] == "2026-09-23T22:41:00Z"
    assert h["r1_manifest"] == "docs/phase14/manifests/manifest_r1_HYP_009.json"
    assert h["target_symbol"] == "SPY"
    params = json.loads(h["parameter_config_json"])
    assert params["signal_name"] == "10_MONTH_SIMPLE_MOVING_AVERAGE"
    assert params["lookback_month_ends"] == 10
    assert params["equality_behavior"] == "CASH"
    assert params["max_gross_leverage"] == 1.0
    assert params["volatility_targeting"] is False
    assert params["cash_return"] == 0.0


def test_inception_doc_encodes_spec() -> None:
    assert INCEPTION_DOC.is_file(), "inception doc missing"
    text = INCEPTION_DOC.read_text(encoding="utf-8")
    assert "PROPOSED_NOT_PREREGISTERED" in text
    assert "10-Month SMA Long/Cash" in text
    assert "NEXT_ELIGIBLE_REGULAR_SESSION_OPEN_AFTER_SIGNAL" in text
    assert "OPEN_BEFORE_R1_TOTAL_RETURN_SIGNAL_CONSTRUCTION" in text
    assert "OPEN_BEFORE_R1_EXECUTION_COST_MODEL" in text
    assert "AUTHORIZE_RETIRE_HYP_008_AND_OPEN_CORE_001_HYP_009_IMPLEMENTATION" in text
    assert "REVIEW_CORE_001_HYP_009_PROPOSAL_AND_AUTHORIZE_R1_PREREGISTRATION" in text
