"""Unit tests for HYP_007 Step R4 post-M1 governance freeze and partition invariants.

Enforces:
- M2 start is exactly 2024-05-01.
- M2 end is exactly 2026-08-14.
- 2026-08-15 is NOT M2 (is quarantined gap).
- Historical gap cannot be read by R4 (strict fail-closed).
- M3 start occurs strictly after Stage-A ratification timestamp.
- M3 cannot be accessed by R4 (firewall active).
- M2 simulated starting AUM is exactly $100,000.00.
- M2 market-state warm-up derives from sealed prior M1 history (14 noise area sessions, 16 volatility closes).
- All four R4 continuation gates match frozen thresholds.
- M2 cannot execute before governance freeze exists.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.research.step_r4_hyp_007_governance import (
    CANONICAL_STARTING_HEAD_SHA,
    EXPECTED_M1_R3_CORRECTED_PACKAGE_SHA256,
    EXPECTED_M1_R2_DATASET_SHA256,
    EFFECTIVE_M1_VERDICT,
    M2_START_DATE,
    M2_START_DATE_STR,
    M2_END_DATE,
    M2_END_DATE_STR,
    M2_ROLE,
    M2_CLASSIFICATION,
    QUARANTINE_START_DATE,
    QUARANTINE_START_DATE_STR,
    GAP_ROLE,
    M3_ROLE,
    M3_ACCESS_STATUS,
    M2_SIMULATED_STARTING_AUM_USD,
    M2_AUM_CLASSIFICATION,
    M2_WARMUP_SOURCE,
    M2_WARMUP_NOISE_AREA_SESSIONS,
    M2_WARMUP_VOLATILITY_CLOSES,
    M2_WARMUP_PERFORMANCE_CONTRIBUTION_USD,
    REAL_CAPITAL_AUTHORITY_USD,
    NO_REAL_ORDERS,
    PAPER_AUTHORIZED,
    LIVE_AUTHORIZED,
    R4_G1_NET_TOTAL_RETURN_MIN,
    R4_G2_NET_ANNUALIZED_SHARPE_MIN,
    R4_G3_MAX_DRAWDOWN_MAX,
    R4_G4_STRESS_TOTAL_RETURN_MIN,
    R4Verdict,
    evaluate_r4_gates,
    compute_prospective_m3_start_session,
    enforce_m2_market_data_range_guard,
    enforce_quarantine_firewall,
    enforce_m3_firewall,
)


def test_upstream_canonical_lineage() -> None:
    assert CANONICAL_STARTING_HEAD_SHA == "01345a2a98ddee1729045d366d9c9406448530ac"
    assert EXPECTED_M1_R3_CORRECTED_PACKAGE_SHA256 == "d4bf18bb80ec650e4c4c0600a8cb5aebb762a7169b8b89111e604adf91293a25"
    assert EXPECTED_M1_R2_DATASET_SHA256 == "4dcf8546b8583bc214684228e29b329226ece904404768bc921f55991f1777aa"
    assert EFFECTIVE_M1_VERDICT == "ACCEPTED_SUPPORTED_ON_REGISTERED_M1"


def test_m2_exact_date_bounds_and_role() -> None:
    assert M2_START_DATE_STR == "2024-05-01"
    assert M2_END_DATE_STR == "2026-08-14"
    assert M2_START_DATE == date(2024, 5, 1)
    assert M2_END_DATE == date(2026, 8, 14)
    assert M2_ROLE == "PUBLICLY_EXPOSED_POST_PUBLICATION_STRESS_SAMPLE"
    assert M2_CLASSIFICATION == "NOT_PRISTINE_OOS"


def test_2026_08_15_is_not_m2_and_range_guard() -> None:
    # 2026-08-14 is allowed
    enforce_m2_market_data_range_guard("2026-08-14")
    # 2024-05-01 is allowed
    enforce_m2_market_data_range_guard("2024-05-01")

    # 2026-08-15 must fail closed
    with pytest.raises(DataContractError, match="after M2_END"):
        enforce_m2_market_data_range_guard("2026-08-15")

    # Dates before M2_START must fail closed
    with pytest.raises(DataContractError, match="before M2_START"):
        enforce_m2_market_data_range_guard("2024-04-30")


def test_quarantine_gap_firewall() -> None:
    assert QUARANTINE_START_DATE_STR == "2026-08-15"
    assert QUARANTINE_START_DATE == date(2026, 8, 15)
    assert GAP_ROLE == "QUARANTINED_HISTORICAL_GAP"

    m3_start = date(2026, 9, 23)
    # Inside quarantine gap: 2026-08-15 through 2026-09-22
    with pytest.raises(DataContractError, match="Quarantine gap violation"):
        enforce_quarantine_firewall("2026-08-15", m3_start=m3_start)

    with pytest.raises(DataContractError, match="Quarantine gap violation"):
        enforce_quarantine_firewall("2026-09-01", m3_start=m3_start)

    with pytest.raises(DataContractError, match="Quarantine gap violation"):
        enforce_quarantine_firewall("2026-09-22", m3_start=m3_start)


def test_m3_prospective_start_and_firewall() -> None:
    cal = NyseCa1Calendar()
    # Ratification timestamp around 2026-09-23 00:30 UTC
    ratification_utc = datetime(2026, 9, 23, 0, 30, 0, tzinfo=timezone.utc)
    m3_date, m3_open = compute_prospective_m3_start_session(ratification_utc, calendar=cal)

    assert m3_date == date(2026, 9, 23)
    assert m3_open > ratification_utc
    assert M3_ROLE == "PROSPECTIVE_ONLY"
    assert M3_ACCESS_STATUS == "LOCKED_ZERO_ACCESS"

    # M3 firewall test
    with pytest.raises(DataContractError, match="M3 firewall violation"):
        enforce_m3_firewall("2026-09-23", m3_start=m3_date)

    with pytest.raises(DataContractError, match="M3 firewall violation"):
        enforce_m3_firewall("2026-09-24", m3_start=m3_date)


def test_m2_initial_accounting_and_warmup_invariants() -> None:
    assert M2_SIMULATED_STARTING_AUM_USD == Decimal("100000.00")
    assert M2_AUM_CLASSIFICATION == "PRE_RESULT_SEGMENT_ACCOUNTING_NORMALIZATION"
    assert M2_WARMUP_SOURCE == "SEALED_M1_R2_HISTORY"
    assert M2_WARMUP_NOISE_AREA_SESSIONS == 14
    assert M2_WARMUP_VOLATILITY_CLOSES == 16
    assert M2_WARMUP_PERFORMANCE_CONTRIBUTION_USD == Decimal("0.00")

    assert REAL_CAPITAL_AUTHORITY_USD == Decimal("0.00")
    assert NO_REAL_ORDERS is True
    assert PAPER_AUTHORIZED is False
    assert LIVE_AUTHORIZED is False


def test_exact_four_r4_gates() -> None:
    assert R4_G1_NET_TOTAL_RETURN_MIN == Decimal("0.0")
    assert R4_G2_NET_ANNUALIZED_SHARPE_MIN == Decimal("0.50")
    assert R4_G3_MAX_DRAWDOWN_MAX == Decimal("0.35")
    assert R4_G4_STRESS_TOTAL_RETURN_MIN == Decimal("0.0")

    # All pass case
    res_pass = evaluate_r4_gates(
        net_total_return=Decimal("0.10"),
        annualized_sharpe=Decimal("0.80"),
        max_drawdown=Decimal("0.15"),
        stress_total_return=Decimal("0.02"),
        contract_valid=True,
    )
    assert res_pass.verdict == R4Verdict.PASS_RECENT_STRESS_SUPPORTED
    assert res_pass.g1_pass and res_pass.g2_pass and res_pass.g3_pass and res_pass.g4_pass

    # G2 fail case (Sharpe < 0.50)
    res_fail_sharpe = evaluate_r4_gates(
        net_total_return=Decimal("0.10"),
        annualized_sharpe=Decimal("0.45"),
        max_drawdown=Decimal("0.15"),
        stress_total_return=Decimal("0.02"),
        contract_valid=True,
    )
    assert res_fail_sharpe.verdict == R4Verdict.FAIL_CURRENT_EDGE_NOT_SUPPORTED
    assert not res_fail_sharpe.g2_pass

    # G3 fail case (MDD > 0.35)
    res_fail_mdd = evaluate_r4_gates(
        net_total_return=Decimal("0.10"),
        annualized_sharpe=Decimal("0.80"),
        max_drawdown=Decimal("0.36"),
        stress_total_return=Decimal("0.02"),
        contract_valid=True,
    )
    assert res_fail_mdd.verdict == R4Verdict.FAIL_CURRENT_EDGE_NOT_SUPPORTED
    assert not res_fail_mdd.g3_pass

    # G4 fail case (stress return < 0)
    res_fail_stress = evaluate_r4_gates(
        net_total_return=Decimal("0.10"),
        annualized_sharpe=Decimal("0.80"),
        max_drawdown=Decimal("0.15"),
        stress_total_return=Decimal("-0.01"),
        contract_valid=True,
    )
    assert res_fail_stress.verdict == R4Verdict.FAIL_CURRENT_EDGE_NOT_SUPPORTED
    assert not res_fail_stress.g4_pass

    # Invalid contract boundary
    res_blocked = evaluate_r4_gates(
        net_total_return=Decimal("0.10"),
        annualized_sharpe=Decimal("0.80"),
        max_drawdown=Decimal("0.15"),
        stress_total_return=Decimal("0.02"),
        contract_valid=False,
        contract_failure_reason="Missing quote boundaries",
    )
    assert res_blocked.verdict == R4Verdict.BLOCKED_INVALID_DATA_OR_EXECUTION_CONTRACT


def test_manifest_and_doc_integrity() -> None:
    import json
    import hashlib
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[3]
    doc_path = repo_root / "docs" / "phase14" / "HYP_007_POST_M1_PARTITION_AND_R4_GOVERNANCE_FREEZE_001.md"
    manifest_path = repo_root / "docs" / "phase14" / "manifests" / "HYP_007_POST_M1_PARTITION_AND_R4_GOVERNANCE_FREEZE_001.json"

    assert doc_path.is_file(), f"Missing doc file: {doc_path}"
    assert manifest_path.is_file(), f"Missing manifest file: {manifest_path}"

    doc_bytes = doc_path.read_bytes()
    doc_sha256 = hashlib.sha256(doc_bytes).hexdigest()

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["governance_document"]["sha256"] == doc_sha256
    assert manifest_data["canonical_starting_head"] == CANONICAL_STARTING_HEAD_SHA
    assert manifest_data["partitions"]["M2"]["start_date"] == M2_START_DATE_STR
    assert manifest_data["partitions"]["M2"]["end_date"] == M2_END_DATE_STR
    assert manifest_data["partitions"]["QUARANTINED_GAP"]["start_date"] == QUARANTINE_START_DATE_STR
    assert manifest_data["partitions"]["M3"]["prospective_start_date"] == "2026-09-23"
    assert manifest_data["partitions"]["M2"]["simulated_starting_aum_usd"] == "100000.00"

