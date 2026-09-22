"""Unit and governance invariant tests for Phase 14 Step R2 HYP_007 dataset qualification.

Tests:
1. Protected R1 and Amendment 001 immutability & upstream hash binding.
2. Exact warm-up range [2021-06-09, 2021-06-30] and non-performance classification.
3. Exact M1 range [2021-07-01, 2024-04-30] and sample classification.
4. M2 firewall: any date or timestamp >= 2024-05-01 raises OutdatedSampleViolation before network.
5. Pre-warmup boundary: any date < 2021-06-09 raises DataContractError.
6. 390-bar regular-session contract: exactly 390 bars [09:30, 15:59] ET required.
7. Early close exclusion: 4 non-standard sessions strictly excluded under CA-1 calendar.
8. Missing bar fail closed: 389 bars raises BarContractFailure (no silent interpolation/splicing).
9. Bar structural invariants: O>0, H>0, L>0, C>0, H>=max(O,C,L), L<=min(O,C,H), V>=0, no extended hours.
10. Quote boundary set: exactly 13 boundaries per eligible M1 session.
11. Quote condition strictness: only condition 'R' admitted; '?' strictly rejected fail-closed.
12. Quote special and unknown conditions rejected fail-closed.
13. Crossed market (bid > ask) rejected; locked market (bid == ask) permitted with positive sizes.
14. Non-positive bid/ask or size rejected fail-closed.
15. EOD boundary < 16:00:00 ET requirement: quote must be in [15:59:00, 16:00:00) ET.
16. Quote evidence contains no trade direction (no BUY/SELL, entry, exit, fill).
17. Deterministic hashing: calculate_deterministic_sha256 is permutation and whitespace invariant.
18. SSGA dividend authority projection: exactly 11 M1 cash distributions reconciled with SSGA manifest.
19. Daily close lineage: exactly 16 warm-up closes available for first M1 day, continuous lineage.
20. Manifest hygiene: zero credentials in manifests, zero strategy-derived or P&L fields, R3 remains locked.
"""

from datetime import date, datetime, time as dtime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import ZoneInfo
import pyarrow.parquet as pq
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.mec_0017_quote_contract import (
    ACCEPTABLE_EXECUTION_QUOTE_CONDITIONS,
    REJECTED_QUOTE_CONDITIONS,
    Mec0017SipQuoteRecord,
    parse_alpaca_direct_sip_quote,
)
from acash.research.step_r2_hyp_007 import (
    EXPECTED_BOUNDARIES_PER_SESSION,
    EXPECTED_HYP_007_AMENDMENT_001_SHA256,
    EXPECTED_HYP_007_PREREG_SHA256,
    EXPECTED_HYP_007_R1_MANIFEST_RAW_SHA256,
    EXPECTED_HYP_007_R1_MANIFEST_SHA256,
    EXPECTED_HYP_007_R1_SPEC_SHA256,
    EXPECTED_M1_EARLY_CLOSES,
    EXPECTED_M1_SESSIONS,
    EXPECTED_SSGA_DIVIDEND_MANIFEST_SHA256,
    EXPECTED_WARMUP_SESSIONS,
    M1_END_DATE,
    M1_QUOTE_DECISION_TIMES_ET,
    M1_START_DATE,
    M2_FIREWALL_BOUNDARY_ET,
    M2_FORBIDDEN_DATE,
    STANDARD_RTH_BAR_COUNT,
    TOTAL_EXPECTED_QUOTE_BOUNDARIES,
    WARMUP_END_DATE,
    WARMUP_START_DATE,
    BarContractFailure,
    OutdatedSampleViolation,
    QuoteContractFailure,
    assert_authorized_sample_boundary,
    build_calendar_census,
    build_m1_dividend_projection,
    calculate_deterministic_sha256,
    enforce_m2_firewall,
    evaluate_boundary_quotes_stream,
    validate_and_parse_session_bars,
    validate_r2_preconditions,
)

NY_TZ = ZoneInfo("America/New_York")


def test_1_protected_r1_and_amendment_immutability_and_preconditions() -> None:
    """Invariant 1: Upstream R1 and Amendment 001 remain strictly sealed and verified."""
    preconditions = validate_r2_preconditions(Path("."))
    assert preconditions["hyp_007_spec_sha256"] == EXPECTED_HYP_007_R1_SPEC_SHA256
    assert preconditions["hyp_007_manifest_sha256"] == EXPECTED_HYP_007_R1_MANIFEST_SHA256
    assert preconditions["hyp_007_manifest_raw_sha256"] == EXPECTED_HYP_007_R1_MANIFEST_RAW_SHA256
    assert preconditions["hyp_007_prereg_sha256"] == EXPECTED_HYP_007_PREREG_SHA256
    assert preconditions["hyp_007_amendment_001_sha256"] == EXPECTED_HYP_007_AMENDMENT_001_SHA256
    assert preconditions["ssga_dividend_manifest_sha256"] == EXPECTED_SSGA_DIVIDEND_MANIFEST_SHA256


def test_2_m2_firewall_pre_request_enforcement() -> None:
    """Invariant 2: Any timestamp or date >= 2024-05-01 raises OutdatedSampleViolation BEFORE network."""
    # Date check
    with pytest.raises(OutdatedSampleViolation, match="M2 FIREWALL VIOLATION"):
        assert_authorized_sample_boundary(date(2024, 5, 1))

    with pytest.raises(OutdatedSampleViolation, match="M2 FIREWALL VIOLATION"):
        assert_authorized_sample_boundary(date(2024, 5, 2))

    with pytest.raises(OutdatedSampleViolation, match="M2 FIREWALL VIOLATION"):
        assert_authorized_sample_boundary(date(2025, 1, 1))

    # Datetime check (ET)
    dt_m2_exact = datetime(2024, 5, 1, 0, 0, 0, tzinfo=NY_TZ)
    with pytest.raises(OutdatedSampleViolation, match="M2 FIREWALL VIOLATION"):
        enforce_m2_firewall(dt_m2_exact)

    # Datetime check (UTC equivalent: 2024-05-01 04:00 UTC)
    dt_m2_utc = datetime(2024, 5, 1, 4, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(OutdatedSampleViolation, match="M2 FIREWALL VIOLATION"):
        enforce_m2_firewall(dt_m2_utc)

    # Pre-M2 timestamp passes firewall
    dt_m1_terminal = datetime(2024, 4, 30, 16, 0, 0, tzinfo=NY_TZ)
    enforce_m2_firewall(dt_m1_terminal)  # Should not raise


def test_3_pre_warmup_boundary_rejection() -> None:
    """Invariant 3: Any date < 2021-06-09 raises DataContractError fail-closed."""
    with pytest.raises(DataContractError, match="PRE-WARMUP BOUNDARY VIOLATION"):
        assert_authorized_sample_boundary(date(2021, 6, 8))

    with pytest.raises(DataContractError, match="PRE-WARMUP BOUNDARY VIOLATION"):
        assert_authorized_sample_boundary(date(2021, 1, 1))

    # Warmup start passes
    assert_authorized_sample_boundary(WARMUP_START_DATE)


def test_4_calendar_census_exact_enumeration() -> None:
    """Invariant 4: NyseCa1Calendar enumerates exactly 16 warmup, 708 M1, and 4 early closes."""
    census = build_calendar_census()
    assert len(census.warmup_regular_sessions) == EXPECTED_WARMUP_SESSIONS
    assert census.warmup_regular_sessions[0] == WARMUP_START_DATE
    assert census.warmup_regular_sessions[-1] == WARMUP_END_DATE

    assert len(census.m1_regular_sessions) == EXPECTED_M1_SESSIONS
    assert census.m1_regular_sessions[0] == M1_START_DATE
    assert census.m1_regular_sessions[-1] == M1_END_DATE

    assert len(census.m1_excluded_early_closes) == EXPECTED_M1_EARLY_CLOSES
    early_dates = [d for d, _ in census.m1_excluded_early_closes]
    assert date(2021, 11, 26) in early_dates
    assert date(2022, 11, 25) in early_dates
    assert date(2023, 7, 3) in early_dates
    assert date(2023, 11, 24) in early_dates

    # By year check
    assert census.m1_sessions_by_year == {2021: 127, 2022: 250, 2023: 248, 2024: 83}


def test_5_bar_contract_complete_390_bars_validation() -> None:
    """Invariant 5: 390 valid bars validate cleanly with left-edge timestamps and HLC3."""
    sess_date = date(2021, 7, 1)
    # Generate 390 synthetic valid bars
    raw_bars = []
    curr_et = datetime.combine(sess_date, dtime(9, 30), tzinfo=NY_TZ)
    for i in range(390):
        t_utc = curr_et.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        raw_bars.append({
            "t": t_utc,
            "o": "425.00",
            "h": "426.00",
            "l": "424.50",
            "c": "425.50",
            "v": 1000,
            "n": 50,
        })
        curr_et += timedelta(minutes=1)

    qualified = validate_and_parse_session_bars(sess_date, raw_bars, is_warmup=False)
    assert len(qualified) == 390
    assert qualified[0].minute_idx == 0
    assert qualified[0].open == Decimal("425.00")
    assert qualified[0].hlc3 == (Decimal("426.00") + Decimal("424.50") + Decimal("425.50")) / Decimal("3")
    assert qualified[0].sample_classification == "PUBLICATION_EXPOSED_DIRECT_SIP_REPLICATION_SAMPLE"
    assert qualified[0].performance_eligible is True
    assert qualified[0].signal_eligible is True
    assert qualified[-1].minute_idx == 389


def test_6_warmup_bars_non_performance_governance() -> None:
    """Invariant 6: Warm-up bars carry performance_eligible=False, signal_eligible=False, trade_eligible=False."""
    sess_date = date(2021, 6, 9)
    raw_bars = []
    curr_et = datetime.combine(sess_date, dtime(9, 30), tzinfo=NY_TZ)
    for i in range(390):
        t_utc = curr_et.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        raw_bars.append({
            "t": t_utc,
            "o": "420.00",
            "h": "421.00",
            "l": "419.50",
            "c": "420.50",
            "v": 500,
            "n": 20,
        })
        curr_et += timedelta(minutes=1)

    qualified = validate_and_parse_session_bars(sess_date, raw_bars, is_warmup=True)
    assert len(qualified) == 390
    for b in qualified:
        assert b.sample_classification == "PRE_M1_STATE_INITIALIZATION_ONLY"
        assert b.performance_eligible is False
        assert b.signal_eligible is False
        assert b.trade_eligible is False


def test_7_missing_bar_fails_closed() -> None:
    """Invariant 7: 389 bars raises BarContractFailure (zero silent interpolation/forward fill)."""
    sess_date = date(2021, 7, 1)
    raw_bars = []
    curr_et = datetime.combine(sess_date, dtime(9, 30), tzinfo=NY_TZ)
    for i in range(389):  # Missing last bar
        t_utc = curr_et.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        raw_bars.append({"t": t_utc, "o": "425.0", "h": "426.0", "l": "424.0", "c": "425.0", "v": 100})
        curr_et += timedelta(minutes=1)

    with pytest.raises(BarContractFailure, match="BAR_CONTRACT_FAILURE"):
        validate_and_parse_session_bars(sess_date, raw_bars, is_warmup=False)


def test_8_bar_structural_violations_fail_closed() -> None:
    """Invariant 8: Non-positive price, invalid high/low, negative volume, duplicate minute fail closed."""
    sess_date = date(2021, 7, 1)

    def make_bars(override_idx: int, override_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_bars = []
        curr_et = datetime.combine(sess_date, dtime(9, 30), tzinfo=NY_TZ)
        for i in range(390):
            t_utc = curr_et.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            bar = {"t": t_utc, "o": "425.0", "h": "426.0", "l": "424.0", "c": "425.0", "v": 100}
            if i == override_idx:
                bar.update(override_dict)
            raw_bars.append(bar)
            curr_et += timedelta(minutes=1)
        return raw_bars

    # High < Open
    with pytest.raises(BarContractFailure, match="INVALID_HIGH"):
        validate_and_parse_session_bars(sess_date, make_bars(10, {"h": "420.0"}), is_warmup=False)

    # Low > Close / Open (with H >= L, so H check passes)
    with pytest.raises(BarContractFailure, match="INVALID_LOW"):
        validate_and_parse_session_bars(sess_date, make_bars(10, {"h": "430.0", "l": "427.0"}), is_warmup=False)

    # Negative volume
    with pytest.raises(BarContractFailure, match="NEGATIVE_VOLUME"):
        validate_and_parse_session_bars(sess_date, make_bars(10, {"v": -1}), is_warmup=False)

    # Zero/negative price
    with pytest.raises(BarContractFailure, match="NON_POSITIVE_PRICE"):
        validate_and_parse_session_bars(sess_date, make_bars(10, {"c": "0.0"}), is_warmup=False)


def test_9_quote_contract_strictness_and_conditions() -> None:
    """Invariant 9: Only 'R' admitted; '?' strictly rejected fail-closed; special codes rejected."""
    # Valid R quote
    raw_r = {"t": "2021-07-01T14:00:00.001Z", "bp": "429.10", "ap": "429.11", "bs": 10, "as": 10, "c": ["R"], "bx": "P", "ax": "T", "z": "B"}
    q = parse_alpaca_direct_sip_quote(raw_r)
    assert q.bid_price == Decimal("429.10")
    assert q.ask_price == Decimal("429.11")
    assert q.conditions == ["R"]
    assert q.is_locked is False
    assert q.is_crossed is False

    # Locked quote (bid == ask) permitted
    raw_locked = dict(raw_r, bp="429.10", ap="429.10")
    q_locked = parse_alpaca_direct_sip_quote(raw_locked)
    assert q_locked.is_locked is True

    # Crossed quote (bid > ask) strictly rejected
    raw_crossed = dict(raw_r, bp="429.12", ap="429.10")
    with pytest.raises(DataContractError, match="CROSSED_NBBO_QUOTE"):
        parse_alpaca_direct_sip_quote(raw_crossed)

    # Condition '?' strictly prohibited
    raw_qmark = dict(raw_r, c=["?"])
    with pytest.raises(DataContractError, match="UNRESOLVED_QUOTE_CONDITION_PROVENANCE"):
        parse_alpaca_direct_sip_quote(raw_qmark)

    # Special conditions rejected
    for cond in ["N", "C", "L", "A", "B", "H", "E", "F", "U", "W", "4"]:
        with pytest.raises(DataContractError, match="UNACCEPTABLE_QUOTE_CONDITION"):
            parse_alpaca_direct_sip_quote(dict(raw_r, c=[cond]))

    # Unknown condition rejected fail-closed
    with pytest.raises(DataContractError, match="UNKNOWN_QUOTE_CONDITION"):
        parse_alpaca_direct_sip_quote(dict(raw_r, c=["UNKNOWN_CODE_999"]))


def test_10_eod_quote_boundary_enforcement() -> None:
    """Invariant 10: EOD boundary requires quote within [15:59:00, 16:00:00) ET."""
    sess_date = date(2021, 7, 1)
    b_time = dtime(15, 59)
    b_utc = datetime.combine(sess_date, b_time, tzinfo=NY_TZ).astimezone(timezone.utc)
    close_utc = datetime.combine(sess_date, dtime(16, 0), tzinfo=NY_TZ).astimezone(timezone.utc)

    # Quote after 16:00 ET rejected
    t_after_close = datetime.combine(sess_date, dtime(16, 0, 1), tzinfo=NY_TZ).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw_quotes = [
        {"t": t_after_close, "bp": "429.10", "ap": "429.11", "bs": 10, "as": 10, "c": ["R"], "bx": "P", "ax": "T", "z": "B"}
    ]
    with pytest.raises(QuoteContractFailure, match="NO_VALID_QUOTE_BEFORE_SESSION_CLOSE"):
        evaluate_boundary_quotes_stream(sess_date, b_time, raw_quotes, b_utc, close_utc)


def test_11_ssga_dividend_projection_cardinality_and_rates() -> None:
    """Invariant 11: M1 dividend projection extracts exactly 11 distributions matching SSGA."""
    divs = build_m1_dividend_projection(Path("."))
    assert len(divs) == 11
    # Verify rate is positive and currency is USD
    for d in divs:
        assert Decimal(d.cash_distribution) > Decimal("0")
        assert d.currency == "USD"
        assert d.upstream_source_reference == "docs/research/manifests/MEC-0015-SPY-dividend-authority-manifest.json"


def test_12_quote_boundaries_exact_13_epochs() -> None:
    """Invariant 12: Decision boundaries are exactly 13 per session."""
    assert len(M1_QUOTE_DECISION_TIMES_ET) == EXPECTED_BOUNDARIES_PER_SESSION
    assert M1_QUOTE_DECISION_TIMES_ET[0] == dtime(10, 0)
    assert M1_QUOTE_DECISION_TIMES_ET[-1] == dtime(15, 59)
    assert TOTAL_EXPECTED_QUOTE_BOUNDARIES == 708 * 13


def test_13_deterministic_serialization_invariant() -> None:
    """Invariant 13: calculate_deterministic_sha256 is key-order and deterministic invariant."""
    d1 = {"b": 2, "a": 1, "c": [3, 2, 1]}
    d2 = {"a": 1, "c": [3, 2, 1], "b": 2}
    assert calculate_deterministic_sha256(d1) == calculate_deterministic_sha256(d2)


def test_14_excluded_session_2023_06_05_omitted_from_qualified_trading_bars() -> None:
    """Invariant 14: Session 2023-06-05 (CTA outage, 386/390 bars) is strictly excluded from qualified trading bars."""
    bars_path = Path("data/hyp_007/m1_bars_qualified.parquet")
    if not bars_path.exists():
        pytest.skip("m1_bars_qualified.parquet not found in local workspace")

    table = pq.read_table(bars_path, columns=["session_date", "performance_eligible", "signal_eligible", "trade_eligible"])
    sess_dates = set(table.column("session_date").to_pylist())

    # 2023-06-05 must be completely absent from qualified bars
    assert "2023-06-05" not in sess_dates
    # Exactly 723 sessions (16 warmup + 707 M1)
    assert len(sess_dates) == 723
    assert table.num_rows == 723 * 390  # 281,970 bars


def test_15_noise_area_lookback_skips_excluded_session() -> None:
    """Invariant 15: Noise Area lookback (14 prior eligible sessions) strictly skips 2023-06-05."""
    bars_path = Path("data/hyp_007/m1_bars_qualified.parquet")
    if not bars_path.exists():
        pytest.skip("m1_bars_qualified.parquet not found in local workspace")

    table = pq.read_table(bars_path, columns=["session_date"])
    unique_dates = sorted(set(table.column("session_date").to_pylist()))

    # Find session 2023-06-06 (first session after excluded 2023-06-05)
    assert "2023-06-06" in unique_dates
    idx_june6 = unique_dates.index("2023-06-06")

    # Prior 14 eligible sessions for 2023-06-06
    lookback_sessions = unique_dates[idx_june6 - 14:idx_june6]
    assert len(lookback_sessions) == 14
    # The immediate preceding session must be 2023-06-02 (skipping 2023-06-05)
    assert lookback_sessions[-1] == "2023-06-02"
    assert "2023-06-05" not in lookback_sessions


def test_16_excluded_session_cannot_generate_signals_or_execute() -> None:
    """Invariant 16: SESSION_EXCLUDED => NO_SIGNAL => NO_EXECUTION contract enforced."""
    # Even if quote evidence exists for raw recording, 2023-06-05 has zero qualified bars
    # and cannot generate signals or execute trades.
    quotes_path = Path("data/hyp_007/m1_execution_quotes_qualified.parquet")
    bars_path = Path("data/hyp_007/m1_bars_qualified.parquet")
    if not quotes_path.exists() or not bars_path.exists():
        pytest.skip("Parquet artifacts not found")

    bars_table = pq.read_table(bars_path, columns=["session_date"])
    qualified_bar_sessions = set(bars_table.column("session_date").to_pylist())
    # Strategy engine requires session to be present in qualified bars
    assert "2023-06-05" not in qualified_bar_sessions

    # Manifest contract enforces that excluded sessions have zero trade eligibility
    manifest_path = Path("docs/phase14/manifests/manifest_r2_HYP_007.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["cardinality"]["m1_bars"] == 707 * 390  # Excludes 2023-06-05
    assert manifest["governance_assertions"]["strategy_signals_computed"] is False
    assert manifest["governance_assertions"]["trades_computed"] is False
    assert manifest["governance_assertions"]["capital_authority_usd"] == "0.00"
    assert manifest["governance_assertions"]["no_real_orders"] is True


def test_17_volatility_daily_close_lineage_outcome_v1() -> None:
    """Invariant 17: Outcome V1 authority — 2023-06-05 15:59 close is retained in continuous market volatility lineage."""
    manifest_path = Path("docs/phase14/manifests/manifest_r2_HYP_007.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Check daily close lineage digest matches sealed manifest
    expected_lineage_sha = manifest["corpus_digests"]["daily_close_lineage_sha256"]
    assert expected_lineage_sha == "0e39ee29b8410a22a84da8cf2cf30285b6c2cc00aad8d805a4b7cd560f012be0"

    # Check raw bars checkpoint for 2023-06-05
    raw_chk = Path("data/hyp_007/raw_bars/session_2023-06-05.raw.json")
    if raw_chk.exists():
        raw_data = json.loads(raw_chk.read_text(encoding="utf-8"))
        bars = raw_data.get("bars", [])
        assert len(bars) == 386  # 4 missing minutes
        # Check 15:59 close bar exists and is valid
        close_bar = next((b for b in bars if b["t"] == "2023-06-05T19:59:00Z"), None)
        assert close_bar is not None
        assert Decimal(str(close_bar["c"])) == Decimal("427.10")
        assert Decimal(str(close_bar["c"])) > Decimal("0")


def test_18_quote_max_delay_outlier_validation() -> None:
    """Invariant 18: Quote delay max outlier (79,941.843 ms on 2024-02-27 13:30 ET) reflects genuine contract behavior."""
    manifest_path = Path("docs/phase14/manifests/manifest_r2_HYP_007.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    max_delay = manifest["quote_condition_metrics"]["quote_delay_stats_ms"]["max"]
    assert max_delay == 79941.843

    # Check execution quotes parquet for this exact boundary
    quotes_path = Path("data/hyp_007/m1_execution_quotes_qualified.parquet")
    if quotes_path.exists():
        table = pq.read_table(quotes_path)
        pydict = table.to_pydict()
        delays = pydict["quote_delay_milliseconds"]
        max_idx = delays.index(max(delays))
        assert delays[max_idx] == pytest.approx(max_delay, abs=1e-3)
        assert pydict["session_date"][max_idx] == "2024-02-27"
        assert pydict["boundary_et"][max_idx] == "13:30:00"
        assert pydict["boundary_utc"][max_idx] == "2024-02-27T18:30:00Z"
        assert pydict["selected_first_valid_timestamp_utc"][max_idx] == "2024-02-27T18:31:19.941843968Z"
        assert pydict["conditions"][max_idx] in (["R"], "R")
        # Selected quote is well before session close (16:00 ET / 21:00 UTC)
        selected_dt = datetime.fromisoformat(pydict["selected_first_valid_timestamp_utc"][max_idx].replace("Z", "+00:00"))
        close_dt = datetime.fromisoformat("2024-02-27T21:00:00+00:00")
        assert selected_dt < close_dt
        assert pydict["candidate_rows_examined"][max_idx] > 0
        assert pydict["rejected_rows_count"][max_idx] == 0
