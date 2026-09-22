"""Unit and governance invariant tests for Phase 14 Step R1 HYP_006 registration and sealing."""

from datetime import date, time
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.qualification.mec_0016_early_quote_contract import (
    ACCEPTABLE_QUOTE_CONDITIONS,
    REJECTED_QUOTE_CONDITIONS,
    parse_alpaca_quote,
)


def test_1_hyp_005_immutability_and_entitlement_block() -> None:
    """Verify HYP_005 original R1 remains 100% immutable and entitlement block is preserved."""
    # HYP_005 R1 manifest
    p14_man_005 = Path("docs/phase14/manifests/manifest_r1_HYP_005.json")
    assert p14_man_005.exists(), "HYP_005 R1 manifest must exist."

    # HYP_005 entitlement block doc & manifest
    block_doc = Path("docs/phase14/HYP_005_DATA_ENTITLEMENT_BLOCK_001.md")
    assert block_doc.exists(), "HYP_005 entitlement block document must exist."
    text = block_doc.read_text(encoding="utf-8")
    assert "BLOCKED_NON_FALSIFIED_BY_PRIMARY_DATA_ENTITLEMENT" in text
    assert "HYPOTHESIS_FALSIFIED: NO" in text
    assert "HYPOTHESIS_REJECTED: NO" in text
    assert "STRATEGY_PNL_OBSERVED: NO" in text
    assert "BACKTEST_STARTED: NO" in text
    assert "R2_DATASET_BUILD: NOT_STARTED" in text
    assert "RESUMABLE: TRUE" in text

    block_man = Path("docs/phase14/manifests/HYP_005_DATA_ENTITLEMENT_BLOCK_001.json")
    assert block_man.exists()
    man_data = json.loads(block_man.read_text(encoding="utf-8"))
    assert man_data["classification"] == "BLOCKED_NON_FALSIFIED_BY_PRIMARY_DATA_ENTITLEMENT"
    assert man_data["resumable"] is True


def test_2_pre_r1_discrepancy_reconciled() -> None:
    """Verify report-vs-manifest discrepancy is resolved with canonical manifest as sole authority."""
    manifest_path = Path("docs/research/manifests/MEC-0016-alpaca-early-quote-contract-manifest.json")
    assert manifest_path.exists(), "Early quote manifest must exist."
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    evals = data["boundary_evaluations"]
    assert len(evals) == 9, "Must evaluate exactly 9 boundaries."

    for ev in evals:
        first_q = ev["first_quote_at_or_after"]
        assert Decimal(first_q["bid_price"]) > 0
        assert Decimal(first_q["ask_price"]) > 0
        assert first_q["bid_size"] > 0
        assert first_q["ask_size"] > 0
        assert Decimal(first_q["ask_price"]) >= Decimal(first_q["bid_price"])
        assert first_q["conditions"] == ["?"], "All early Alpaca SIP historical quotes carry condition ['?']."
        assert first_q["tape"] == "B"
        assert ev["is_valid"] is True


def test_3_quote_conditions_and_validity_filtering() -> None:
    """Verify quote parser enforces strict sizes, non-crossed, locked, and authoritative condition codes."""
    # Tape B conditions manifest exists
    cond_path = Path("docs/research/manifests/MEC-0016-alpaca-quote-conditions-tape-b.json")
    assert cond_path.exists(), "Alpaca Tape B conditions manifest must exist."
    cond_data = json.loads(cond_path.read_text(encoding="utf-8"))
    assert "R" in cond_data["official_conditions"]
    assert "?" in cond_data["legacy_historical_conditions"]

    # Valid quote with '?'
    valid_raw_legacy = {
        "t": "2016-06-17T14:00:00.002Z",
        "bp": "206.91",
        "ap": "206.92",
        "bs": 2,
        "as": 24,
        "bx": "K",
        "ax": "P",
        "c": ["?"],
        "z": "B",
    }
    q1 = parse_alpaca_quote(valid_raw_legacy)
    assert q1.bid_price == Decimal("206.91")
    assert q1.ask_price == Decimal("206.92")
    assert q1.is_locked is False
    assert q1.is_crossed is False

    # Valid quote with 'R'
    valid_raw_r = dict(valid_raw_legacy, c=["R"])
    q2 = parse_alpaca_quote(valid_raw_r)
    assert q2.conditions == ["R"]

    # Non-positive price
    bad_price = dict(valid_raw_legacy, bp="0.00")
    with pytest.raises(DataContractError, match="NONPOSITIVE_NBBO_QUOTE"):
        parse_alpaca_quote(bad_price)

    # Non-positive size
    bad_size = dict(valid_raw_legacy, bs=0)
    with pytest.raises(DataContractError, match="NONPOSITIVE_QUOTE_SIZE"):
        parse_alpaca_quote(bad_size)

    # Crossed market
    crossed = dict(valid_raw_legacy, bp="206.95", ap="206.92")
    with pytest.raises(DataContractError, match="CROSSED_NBBO_QUOTE"):
        parse_alpaca_quote(crossed)

    # Locked market (admitted for execution if positive sizes)
    locked = dict(valid_raw_legacy, bp="206.92", ap="206.92")
    q_locked = parse_alpaca_quote(locked)
    assert q_locked.is_locked is True
    assert q_locked.spread == Decimal("0.00")

    # Unacceptable condition (e.g. 'N' Non-firm, 'C' Closing, '4' Auction)
    for bad_c in ["N", "C", "L", "4", "A"]:
        bad_cond = dict(valid_raw_legacy, c=[bad_c])
        with pytest.raises(DataContractError, match="UNACCEPTABLE_QUOTE_CONDITION"):
            parse_alpaca_quote(bad_cond)

    # Unknown/unmapped condition fails closed
    unknown_cond = dict(valid_raw_legacy, c=["XYZ"])
    with pytest.raises(DataContractError, match="UNKNOWN_QUOTE_CONDITION"):
        parse_alpaca_quote(unknown_cond)


def test_4_exact_eod_execution_semantics_frozen() -> None:
    """Verify EOD execution semantics are frozen with continuous 15:59 NBBO execution."""
    decisions_doc = Path("docs/research/MEC-0016-HYP-006-open-decisions.md")
    text = decisions_doc.read_text(encoding="utf-8")
    assert "MEC-0016-D09" in text
    assert "Exact EOD Execution Semantics" in text
    assert "RESOLVED_PASS" in text
    assert "15:59:00 ET" in text
    assert "[15:59, 16:00)" in text
    assert "auction/MOC excluded" in text
    assert "bar close prohibited" in text


def test_5_hyp_006_r1_spec_and_manifest_sealed() -> None:
    """Verify HYP_006 R1 specification and manifest are properly sealed and mirror-verified."""
    p85_spec = Path("docs/phase8.5/hypotheses/HYP_006.json")
    p14_spec = Path("docs/phase14/hypotheses/HYP_006.json")
    p14_man = Path("docs/phase14/manifests/manifest_r1_HYP_006.json")

    assert p85_spec.exists(), "Phase 8.5 HYP_006 spec must exist."
    assert p14_spec.exists(), "Phase 14 HYP_006 spec must exist."
    assert p14_man.exists(), "Phase 14 HYP_006 R1 manifest must exist."

    # Mirror equality
    assert p85_spec.read_bytes() == p14_spec.read_bytes(), "HYP_006 spec mirrors must be byte-identical."

    spec_data = json.loads(p14_spec.read_text(encoding="utf-8"))
    assert spec_data["hypothesis_id"] == "HYP_006"
    assert spec_data["target_symbol"] == "SPY"

    def _val(x: Any) -> Any:
        if isinstance(x, dict) and "__type__" in x and "value" in x:
            return x["value"]
        return x

    cfg = json.loads(spec_data["parameter_config_json"])
    assert cfg["mechanism_id"] == "MEC-0016"
    assert _val(cfg["hypothesis_ordinal"]) == 6
    assert _val(cfg["search_space"]["search_trial_count_k"]) == 1

    # Partitions
    parts = cfg["partition_policy"]
    assert parts["m1_replication_sample"]["start_date"] == "2016-01-01"
    assert parts["m1_replication_sample"]["end_date"] == "2024-04-30"
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

    # Market data
    md = cfg["market_data_contract"]
    assert md["primary_bar_provider"] == "ALPACA_HISTORICAL_SIP"
    assert md["primary_quote_provider"] == "ALPACA_HISTORICAL_SIP"
    assert md["missing_bar_policy"] == "FAIL_CLOSED_SESSION_EXCLUSION"
    assert md["secondary_bar_role"] == "SECONDARY_INDEPENDENT_BAR_CROSS_CHECK_ONLY"

    # R1 manifest assertions
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
