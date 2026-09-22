"""Unit and governance invariant tests for Phase 14 Step R1 HYP_007 registration and sealing."""

from datetime import date, time
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.mec_0017_quote_contract import (
    ACCEPTABLE_EXECUTION_QUOTE_CONDITIONS,
    REJECTED_QUOTE_CONDITIONS,
    parse_alpaca_direct_sip_quote,
)
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.schema import HypothesisSpecification


def test_1_hyp_005_and_hyp_006_immutability_and_blocked_states() -> None:
    """Invariant 1: HYP_005 and HYP_006 remain strictly immutable and blocked non-falsified."""
    # HYP_005 R1
    p14_spec_005 = Path("docs/phase14/hypotheses/HYP_005.json").read_bytes()
    p85_spec_005 = Path("docs/phase8.5/hypotheses/HYP_005.json").read_bytes()
    assert p14_spec_005 == p85_spec_005
    spec_005 = HypothesisSpecification(**json.loads(p14_spec_005.decode("utf-8")))
    assert calculate_hypothesis_spec_sha256(spec_005) == "ec4679751fa1c4d82e2a3a871ca6dc2f7d6bfbc1e1691518ab6261059e14603f"

    # HYP_005 Entitlement Block
    block_man_005 = json.loads(Path("docs/phase14/manifests/HYP_005_DATA_ENTITLEMENT_BLOCK_001.json").read_text(encoding="utf-8"))
    assert block_man_005["classification"] == "BLOCKED_NON_FALSIFIED_BY_PRIMARY_DATA_ENTITLEMENT"
    assert block_man_005["resumable"] is True
    assert block_man_005["strategy_pnl_observed"] is False

    # HYP_006 R1
    p14_spec_006 = Path("docs/phase14/hypotheses/HYP_006.json").read_bytes()
    p85_spec_006 = Path("docs/phase8.5/hypotheses/HYP_006.json").read_bytes()
    assert p14_spec_006 == p85_spec_006
    spec_006 = HypothesisSpecification(**json.loads(p14_spec_006.decode("utf-8")))
    assert calculate_hypothesis_spec_sha256(spec_006) == "aba1dfa9bd54e42722c7cd160214632aea7eb0c5545808e8fe03208996478a30"

    # HYP_006 Amendment 001 Provenance Block
    block_man_006 = json.loads(Path("docs/phase14/manifests/HYP_006_R1_QUOTE_PROVENANCE_AMENDMENT_001.json").read_text(encoding="utf-8"))
    assert block_man_006["hypothesis_status"] == "BLOCKED_NON_FALSIFIED_BY_EXECUTION_DATA_PROVENANCE"
    assert block_man_006["hypothesis_falsified"] is False
    assert block_man_006["strategy_pnl_observed"] is False
    assert block_man_006["r2_dataset_status"] == "NOT_STARTED"
    assert block_man_006["resumable"] is True


def test_2_hyp_007_start_date_provenance_and_census() -> None:
    """Invariant 2: HYP_007 start date 2021-07-01 is established strictly from direct-SIP provenance census."""
    census_path = Path("docs/research/manifests/MEC-0017-alpaca-direct-sip-transition-manifest.json")
    assert census_path.exists()
    data = json.loads(census_path.read_text(encoding="utf-8"))

    findings = data["transition_findings"]
    assert findings["last_observed_question_mark_date"] == "2021-04-23"
    assert findings["first_observed_direct_sip_date"] == "2021-04-26"
    assert findings["selected_conservative_m1_start_date"] == "2021-07-01"
    assert "PROVENANCE_BOUNDARY" in findings["selection_rationale"]

    census = data["probe_dates_census"]
    # Pre-transition has 100% '?'
    assert census["2021-04-23"]["question_mark_count"] == 100
    assert census["2021-04-23"]["r_count"] == 0

    # Post-transition has 100% 'R'
    assert census["2021-04-26"]["question_mark_count"] == 0
    assert census["2021-04-26"]["r_count"] == 100
    assert census["2021-07-01"]["question_mark_count"] == 0
    assert census["2021-07-01"]["r_count"] == 100


def test_3_hyp_007_quote_contract_and_strict_condition_rejection() -> None:
    """Invariant 3: MEC-0017 strictly rejects '?' fail-closed, rejects unmapped conditions, accepts 'R'."""
    raw_quote_r = {
        "t": "2021-07-01T14:00:00.13147136Z",
        "bp": "429.34",
        "ap": "429.34",
        "bs": 1,
        "as": 1,
        "bx": "P",
        "ax": "T",
        "c": ["R"],
        "z": "B",
    }
    q = parse_alpaca_direct_sip_quote(raw_quote_r)
    assert q.bid_price == Decimal("429.34")
    assert q.ask_price == Decimal("429.34")
    assert q.is_locked is True
    assert q.conditions == ["R"]

    # Condition '?' is strictly prohibited and raises DataContractError
    raw_quote_qmark = dict(raw_quote_r, c=["?"])
    with pytest.raises(DataContractError, match="UNRESOLVED_QUOTE_CONDITION_PROVENANCE"):
        parse_alpaca_direct_sip_quote(raw_quote_qmark)

    # Special conditions rejected
    for bad_c in ["N", "C", "L", "A", "B", "H", "E", "F", "U", "W", "4"]:
        raw_bad = dict(raw_quote_r, c=[bad_c])
        with pytest.raises(DataContractError, match="UNACCEPTABLE_QUOTE_CONDITION"):
            parse_alpaca_direct_sip_quote(raw_bad)

    # Unknown conditions fail closed
    raw_unknown = dict(raw_quote_r, c=["ZZZ"])
    with pytest.raises(DataContractError, match="UNKNOWN_QUOTE_CONDITION"):
        parse_alpaca_direct_sip_quote(raw_unknown)


def test_4_hyp_007_r1_spec_and_manifest_sealed() -> None:
    """Invariant 4: HYP_007 R1 specification mirrors and manifest are sealed and match canonical hashes."""
    p85_spec = Path("docs/phase8.5/hypotheses/HYP_007.json")
    p14_spec = Path("docs/phase14/hypotheses/HYP_007.json")
    p14_man = Path("docs/phase14/manifests/manifest_r1_HYP_007.json")

    assert p85_spec.exists()
    assert p14_spec.exists()
    assert p14_man.exists()
    assert p85_spec.read_bytes() == p14_spec.read_bytes()

    spec_dict = json.loads(p14_spec.read_text(encoding="utf-8"))
    assert spec_dict["hypothesis_id"] == "HYP_007"
    assert spec_dict["target_symbol"] == "SPY"

    spec_obj = HypothesisSpecification(**spec_dict)
    hyp_sha = calculate_hypothesis_spec_sha256(spec_obj)
    assert hyp_sha == "e6821bed806cadef6c129f02c45cd244c0e720fca1715fcc480315c95186df7d"

    def _val(x: Any) -> Any:
        if isinstance(x, dict) and "__type__" in x and "value" in x:
            return x["value"]
        return x

    cfg = json.loads(spec_dict["parameter_config_json"])
    assert cfg["mechanism_id"] == "MEC-0017"
    assert _val(cfg["hypothesis_ordinal"]) == 7
    assert _val(cfg["search_space"]["search_trial_count_k"]) == 1

    # Partitions & Provenance
    parts = cfg["partition_policy"]
    assert parts["m1_replication_sample"]["start_date"] == "2021-07-01"
    assert parts["m1_replication_sample"]["end_date"] == "2024-04-30"
    assert parts["m1_replication_sample"]["role"] == "PUBLICATION_EXPOSED_DIRECT_SIP_REPLICATION_SAMPLE"
    assert parts["m2_stress_sample"]["access_state"] == "LOCKED_ZERO_ACCESS"

    # Strategy rules
    strat = cfg["strategy_rules"]
    assert _val(strat["noise_area_contract"]["lookback_completed_sessions"]) == 14
    assert strat["noise_area_contract"]["current_session_leakage"] == "PROHIBITED"
    assert Decimal(str(_val(strat["noise_area_contract"]["noise_multiplier"]))) == Decimal("1.0")
    assert _val(strat["volatility_sizing"]["window_returns_count"]) == 15
    assert _val(strat["volatility_sizing"]["annualization_used"]) is False
    assert Decimal(str(_val(strat["volatility_sizing"]["target_volatility"]))) == Decimal("0.02")
    assert Decimal(str(_val(strat["volatility_sizing"]["max_leverage"]))) == Decimal("4.0")
    assert strat["volatility_sizing"]["shares_rounding"] == "NEAREST_INTEGER"

    # EOD contract
    assert strat["eod_contract"]["overnight_exposure"] == "STRICTLY_ZERO"
    assert strat["eod_contract"]["final_signal_epoch"] == "15:30:00 ET"
    assert strat["eod_contract"]["forced_flatten_boundary"] == "15:59:00 ET"
    assert strat["eod_contract"]["closing_auction_cross_participation"] == "EXCLUDED"
    assert strat["eod_contract"]["bar_close_fills"] == "PROHIBITED"

    # Friction model
    assert _val(cfg["friction_model"]["friction_stress_contract"]["stress_multiplier"]) == 2.0
    assert _val(cfg["friction_model"]["friction_stress_contract"]["stressed_short_borrow_bps"]) == 50

    # Manifest assertions
    man_data = json.loads(p14_man.read_text(encoding="utf-8"))
    assert man_data["status"] == "SEALED_STEP_R1_PASS"
    assert man_data["capital_authority_usd"] == "0.00"
    assert man_data["no_real_orders"] is True
    assert man_data["market_data_access"] == "ZERO"
    assert man_data["m1_data_access"] == "ZERO"
    assert man_data["m2_data_access"] == "ZERO"
    assert man_data["is_paper_authorized"] is False
    assert man_data["is_live_authorized"] is False
    assert "STEP_R2" in man_data["next_required_step"]
    assert man_data["manifest_sha256"] == "f48a57333675ebeb5a47cfff40108b13abec000ba958a42ba54fc714c30adc02"
