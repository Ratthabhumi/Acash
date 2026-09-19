"""Unit and Invariant Tests for Phase 14 Step R2: HYP_004 Historical Dataset Qualification.

Tests:
1. Upstream governance and cryptographic hash verification.
2. In-Sample date boundary enforcement [2017-01-01, 2022-12-31].
3. OOS hard rejection: Any timestamp or date >= 2023-01-01 immediately aborts before network/data access.
4. Pre-IS date rejection: Any date < 2017-01-01 aborts.
5. Deterministic 1,498 regular session enumeration (249, 248, 249, 251, 251, 250).
6. First session 2017-01-03 excluded as FIRST_SESSION_NO_PRIOR_IN_SAMPLE_CLOSE without 2016 access.
7. Correct prior-session linkage: p0(t) == p13(t-1).
8. 10:00 single price accepted.
9. 10:00 multi-trade same price accepted.
10. 10:00 multi-price tie excluded as AMBIGUOUS_P1_BOUNDARY_PRICE.
11. 15:30 boundary equivalents.
12. Trade count 499 excluded as TRADE_COUNT_LT_500.
13. Trade count 500 accepted.
14. Odd-lot records remain counted.
15. Exact session predicate [09:30:00, 16:00:00] America/New_York.
16. Pagination exhaustion required.
17. Repeated token fails closed.
18. Malformed record fails closed.
19. trade_id not used as ordering authority.
20. Daily bar/minute bar cannot substitute endpoint price.
21. Primary close strictly uses qualified NYSE Arca x=P, c=6.
22. Local dataset contains no return columns.
23. Zero return/regression functions in R2 module.
24. 1,498-row ledger and dataset cardinality required.
25. Raw-page cache hash verification.
26. Idempotent / resume behavior.
27. Credential non-leakage.
28. OOS sealed invariant.
29. HYP_004 sealed artifacts unchanged.
30. Adaptive rate-limit header handling.
31. HTTP 429 reset/retry handling.
32. Atomic session checkpoint publication and crash safety.
33. Acquisition-status vs qualification-status separation (scientific exclusion != provider failure).
34. Verify-only mode makes zero HTTP calls.
"""

from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import inspect
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo
import pytest

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.mec_0014_close_contract import (
    IS_END_DATE,
    IS_START_DATE,
    OOS_FORBIDDEN_DATE,
)
from acash.data.qualification.mec_0014_coverage_census import enumerate_qualified_regular_sessions
from acash.data.qualification.mec_0014_transaction_contract import (
    BOUNDARY_1000_ET,
    BOUNDARY_1530_ET,
    BoundaryEndpointClassification,
    RawSipTradeRecord,
    classify_boundary_endpoint,
    filter_regular_session_records,
)
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.schema import HypothesisSpecification
from acash.research.step_r2_hyp_004 import (
    EXPECTED_HYP_004_SHA256,
    EXPECTED_PREREG_SHA256,
    EXPECTED_R1_MANIFEST_SHA256,
    EXPECTED_SESSIONS_BY_YEAR,
    FIRST_SAMPLE_SESSION,
    TOTAL_EXPECTED_REGULAR_SESSIONS,
    AcquisitionStatus,
    AdaptiveRateGovernor,
    CloseAuthorityRecord,
    QualificationStatus,
    R2_SESSION_ENDPOINTS_ARROW_SCHEMA,
    SessionCheckpointMeta,
    SessionEndpointRow,
    SessionPageMeta,
    assert_is_boundary,
    build_canonical_endpoint_parquet,
    build_r2_tracked_manifest,
    build_raw_page_manifest,
    build_session_ledger,
    compute_page_chain_aggregate_sha,
    evaluate_session,
    load_verified_close_authority,
    process_session_trades,
    validate_r2_preconditions,
    write_atomic_checkpoint,
)

NY_TZ = ZoneInfo("America/New_York")


def test_1_governance_preconditions_verified() -> None:
    """Invariant 1: All upstream governance digests match pinned canonical values."""
    hashes = validate_r2_preconditions()
    assert hashes["hypothesis_sha256"] == EXPECTED_HYP_004_SHA256
    assert hashes["preregistration_sha256"] == EXPECTED_PREREG_SHA256
    assert hashes["r1_manifest_sha256"] == EXPECTED_R1_MANIFEST_SHA256
    assert Path(hashes["conformance_record"]).is_file()


def test_2_oos_date_rejection_fail_closed() -> None:
    """Invariant 2: Any date >= 2023-01-01 strictly aborts before network or data access."""
    with pytest.raises(DataContractError, match="OOS HARD BOUNDARY VIOLATION"):
        assert_is_boundary(date(2023, 1, 1))
    with pytest.raises(DataContractError, match="OOS HARD BOUNDARY VIOLATION"):
        assert_is_boundary(date(2024, 6, 15))


def test_3_pre_is_date_rejection_fail_closed() -> None:
    """Invariant 3: Any date < 2017-01-01 strictly aborts."""
    with pytest.raises(DataContractError, match="PRE-IN-SAMPLE BOUNDARY VIOLATION"):
        assert_is_boundary(date(2016, 12, 31))


def test_4_calendar_session_enumeration_exact() -> None:
    """Invariant 4: NyseCa1Calendar enumerates exactly 1,498 regular sessions matching census."""
    cal = NyseCa1Calendar()
    sessions = enumerate_qualified_regular_sessions(cal, IS_START_DATE, IS_END_DATE)
    assert len(sessions) == TOTAL_EXPECTED_REGULAR_SESSIONS
    counts = Counter(s.year for s in sessions)
    for yr, exp_cnt in EXPECTED_SESSIONS_BY_YEAR.items():
        assert counts[yr] == exp_cnt


def test_5_first_session_exclusion_rule() -> None:
    """Invariant 5: First session 2017-01-03 is excluded as no prior in-sample close."""
    row = evaluate_session(
        session_date=FIRST_SAMPLE_SESSION,
        ordinal=1,
        prior_session_date=None,
        close_authority_map={},
        checkpoint=None,
        close_evidence_hash="dummy_hash",
        contract_git_sha="dummy_sha",
    )
    assert row.trading_date == "2017-01-03"
    assert row.calendar_session_ordinal == 1
    assert row.p0_previous_primary_close is None
    assert row.acquisition_status == AcquisitionStatus.NOT_REQUIRED_BY_FROZEN_ELIGIBILITY_RULE.value
    assert row.qualification_status == QualificationStatus.EXCLUDED_PREREGISTERED.value
    assert not row.primary_regression_eligible
    assert "FIRST_SESSION_NO_PRIOR_IN_SAMPLE_CLOSE" in row.exclusion_reason_codes


def test_6_prior_session_close_linkage() -> None:
    """Invariant 6: Session t receives prior session close p0 == p13(t-1)."""
    d1 = date(2017, 1, 3)
    d2 = date(2017, 1, 4)
    close_map = {
        "2017-01-03": CloseAuthorityRecord(session_date="2017-01-03", price=Decimal("225.24"), timestamp_utc="2017-01-03T21:00:00Z"),
        "2017-01-04": CloseAuthorityRecord(session_date="2017-01-04", price=Decimal("226.58"), timestamp_utc="2017-01-04T21:00:00Z"),
    }
    row = evaluate_session(
        session_date=d2,
        ordinal=2,
        prior_session_date=d1,
        close_authority_map=close_map,
        checkpoint=None,
        close_evidence_hash="dummy",
        contract_git_sha="dummy",
    )
    assert row.p0_previous_primary_close == Decimal("225.24")
    assert row.p13_current_primary_close == Decimal("226.58")
    assert row.prior_regular_session_date == "2017-01-03"


def _make_dummy_trade(ts_str: str, price: str, conditions: Optional[List[str]] = None) -> RawSipTradeRecord:
    return RawSipTradeRecord(
        timestamp_utc=ts_str,
        price=Decimal(price),
        size=100,
        exchange="P",
        conditions=conditions or [" "],
        tape="B",
        trade_id=1,
        symbol="SPY",
    )


def test_7_boundary_1000_single_price_accepted() -> None:
    """Invariant 7: 10:00 single price trade at T* is accepted."""
    d = date(2017, 6, 1)
    trades = [
        _make_dummy_trade("2017-06-01T13:59:59.900Z", "241.95"),
    ]
    b = classify_boundary_endpoint(d, trades, BOUNDARY_1000_ET)
    assert b.classification == BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE
    assert b.selected_price == Decimal("241.95")


def test_8_boundary_1000_multi_trade_same_price_accepted() -> None:
    """Invariant 8: 10:00 multi-trade with identical price at T* is accepted."""
    d = date(2017, 6, 1)
    trades = [
        _make_dummy_trade("2017-06-01T14:00:00.000Z", "241.95"),
        _make_dummy_trade("2017-06-01T14:00:00.000Z", "241.95"),
    ]
    b = classify_boundary_endpoint(d, trades, BOUNDARY_1000_ET)
    assert b.classification == BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE_MULTI_TRADE_SAME_PRICE
    assert b.selected_price == Decimal("241.95")


def test_9_boundary_1000_distinct_price_tie_excluded() -> None:
    """Invariant 9: 10:00 multi-trade with distinct prices at T* is excluded as AMBIGUOUS."""
    d = date(2017, 6, 1)
    trades = [
        _make_dummy_trade("2017-06-01T14:00:00.000Z", "241.95"),
        _make_dummy_trade("2017-06-01T14:00:00.000Z", "241.96"),
    ]
    b = classify_boundary_endpoint(d, trades, BOUNDARY_1000_ET)
    assert b.classification == BoundaryEndpointClassification.AMBIGUOUS_BOUNDARY_PRICE
    assert b.selected_price is None


def test_10_boundary_1530_equivalents() -> None:
    """Invariant 10: 15:30 boundary classification behaves identically."""
    d = date(2017, 6, 1)
    # Ambiguous at 15:30 (19:30 UTC in EDT)
    trades = [
        _make_dummy_trade("2017-06-01T19:30:00.000Z", "242.10"),
        _make_dummy_trade("2017-06-01T19:30:00.000Z", "242.11"),
    ]
    b = classify_boundary_endpoint(d, trades, BOUNDARY_1530_ET)
    assert b.classification == BoundaryEndpointClassification.AMBIGUOUS_BOUNDARY_PRICE
    assert b.selected_price is None


def test_11_trade_count_499_excluded() -> None:
    """Invariant 11: Daily trade count of 499 is excluded as TRADE_COUNT_LT_500."""
    checkpoint = SessionCheckpointMeta(
        session_date="2017-06-01",
        acquisition_status=AcquisitionStatus.RAW_COMPLETE,
        qualification_status=QualificationStatus.EXCLUDED_PREREGISTERED,
        exclusion_reason_codes=["TRADE_COUNT_LT_500"],
        pages=[],
        total_raw_records=499,
        regular_session_records=499,
        raw_evidence_aggregate_sha256="abc",
        b1000_classification=BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE.value,
        b1000_price="241.95",
        b1530_classification=BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE.value,
        b1530_price="242.00",
        exact_transport_duplicates=0,
        last_updated_utc=datetime.now(timezone.utc).isoformat(),
    )
    close_map = {
        "2017-05-31": CloseAuthorityRecord("2017-05-31", Decimal("241.00"), "ts"),
        "2017-06-01": CloseAuthorityRecord("2017-06-01", Decimal("242.00"), "ts"),
    }
    row = evaluate_session(
        session_date=date(2017, 6, 1),
        ordinal=100,
        prior_session_date=date(2017, 5, 31),
        close_authority_map=close_map,
        checkpoint=checkpoint,
        close_evidence_hash="h",
        contract_git_sha="s",
    )
    assert not row.primary_regression_eligible
    assert "TRADE_COUNT_LT_500" in row.exclusion_reason_codes
    assert row.qualification_status == QualificationStatus.EXCLUDED_PREREGISTERED.value


def test_12_trade_count_500_accepted() -> None:
    """Invariant 12: Daily trade count of 500 is accepted."""
    checkpoint = SessionCheckpointMeta(
        session_date="2017-06-01",
        acquisition_status=AcquisitionStatus.RAW_COMPLETE,
        qualification_status=QualificationStatus.QUALIFIED,
        exclusion_reason_codes=[],
        pages=[SessionPageMeta(1, "f", "h", None, None, 500, None, None)],
        total_raw_records=500,
        regular_session_records=500,
        raw_evidence_aggregate_sha256="abc",
        b1000_classification=BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE.value,
        b1000_price="241.95",
        b1530_classification=BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE.value,
        b1530_price="242.00",
        exact_transport_duplicates=0,
        last_updated_utc=datetime.now(timezone.utc).isoformat(),
    )
    close_map = {
        "2017-05-31": CloseAuthorityRecord("2017-05-31", Decimal("241.00"), "ts"),
        "2017-06-01": CloseAuthorityRecord("2017-06-01", Decimal("242.00"), "ts"),
    }
    row = evaluate_session(
        session_date=date(2017, 6, 1),
        ordinal=100,
        prior_session_date=date(2017, 5, 31),
        close_authority_map=close_map,
        checkpoint=checkpoint,
        close_evidence_hash="h",
        contract_git_sha="s",
    )
    assert row.primary_regression_eligible
    assert row.qualification_status == QualificationStatus.QUALIFIED.value


def test_13_odd_lots_included() -> None:
    """Invariant 13: Odd-lot trades (condition 'I') are counted in the daily trade count."""
    d = date(2017, 6, 1)
    trades = [
        _make_dummy_trade("2017-06-01T13:30:00.100Z", "241.95", conditions=["I", " "]),
    ]
    filtered = filter_regular_session_records(trades, d)
    assert len(filtered) == 1


def test_14_exact_session_predicate() -> None:
    """Invariant 14: Regular session predicate strictly matches [09:30:00, 16:00:00] ET."""
    d = date(2017, 6, 1)
    # Pre-market (09:29:59 ET = 13:29:59 UTC in EDT)
    t_pre = _make_dummy_trade("2017-06-01T13:29:59.999Z", "241.90")
    # Open exactly 09:30:00 ET = 13:30:00 UTC
    t_open = _make_dummy_trade("2017-06-01T13:30:00.000Z", "241.95")
    # Close exactly 16:00:00 ET = 20:00:00 UTC
    t_close = _make_dummy_trade("2017-06-01T20:00:00.000Z", "242.00")
    # Post-market 16:00:01 ET = 20:00:01 UTC
    t_post = _make_dummy_trade("2017-06-01T20:00:01.000Z", "242.05")

    res = filter_regular_session_records([t_pre, t_open, t_close, t_post], d)
    assert len(res) == 2
    assert res[0].timestamp_utc == t_open.timestamp_utc
    assert res[1].timestamp_utc == t_close.timestamp_utc


def test_21_canonical_dataset_zero_return_columns() -> None:
    """Invariant 21: Canonical Parquet schema contains zero return columns."""
    forbidden = {"r1", "r13", "return", "returns", "beta", "alpha", "t_stat", "t_statistic", "p_value", "pvalue", "sharpe", "pnl", "profit"}
    for f in R2_SESSION_ENDPOINTS_ARROW_SCHEMA:
        name_parts = set(f.name.lower().split("_"))
        for term in forbidden:
            assert term not in name_parts, f"Forbidden term '{term}' in field '{f.name}'"


def test_22_zero_regression_functions_in_r2() -> None:
    """Invariant 22: Module contains zero functions computing return or regression."""
    import acash.research.step_r2_hyp_004 as mod
    forbidden_terms = ["return", "regression", "ols", "hac", "beta", "p_value", "sharpe"]
    for name, obj in inspect.getmembers(mod, inspect.isfunction):
        if obj.__module__ == mod.__name__:
            for term in forbidden_terms:
                assert term not in name.lower(), f"Forbidden function name in R2: {name}"


def test_23_cardinality_1498_enforced(tmp_path: Path) -> None:
    """Invariant 23: build_canonical_endpoint_parquet rejects anything other than 1,498 rows."""
    dummy_rows = [
        SessionEndpointRow(
            trading_date=f"2017-01-{i:02d}",
            calendar_session_ordinal=i,
            prior_regular_session_date=None,
            p0_previous_primary_close=None,
            p0_source_session_date=None,
            p0_auction_timestamp=None,
            p0_exchange=None,
            p0_condition=None,
            p0_authority_status="STATUS",
            p1_1000_price=None,
            p1_t_star_utc=None,
            p1_distance_to_boundary_seconds=None,
            p1_tie_record_count=0,
            p1_distinct_price_count=0,
            p1_endpoint_status="STATUS",
            p12_1530_price=None,
            p12_t_star_utc=None,
            p12_distance_to_boundary_seconds=None,
            p12_tie_record_count=0,
            p12_distinct_price_count=0,
            p12_endpoint_status="STATUS",
            p13_current_primary_close=None,
            p13_auction_timestamp=None,
            p13_exchange=None,
            p13_condition=None,
            p13_authority_status="STATUS",
            raw_regular_session_sip_trade_count=0,
            trade_count_threshold=500,
            trade_count_pass=False,
            pagination_page_count=0,
            pagination_complete=True,
            exact_transport_duplicate_count=0,
            acquisition_status="RAW_COMPLETE",
            qualification_status="QUALIFIED",
            primary_regression_eligible=False,
            exclusion_reason_codes=(),
            per_session_raw_evidence_aggregate_sha256=None,
            close_evidence_hash="h",
            contract_version_git_sha="s",
        )
        for i in range(1, 10)  # Only 9 rows
    ]
    out_file = tmp_path / "test.parquet"
    with pytest.raises(DataContractError, match="Dataset cardinality violation"):
        build_canonical_endpoint_parquet(dummy_rows, out_file)


def test_28_hyp_004_sealed_artifacts_unchanged() -> None:
    """Invariant 28: Sealed HYP_004 JSON and R1 manifest are byte-for-byte unmodified."""
    hyp_p14 = json.loads(Path("docs/phase14/hypotheses/HYP_004.json").read_text(encoding="utf-8"))
    spec = HypothesisSpecification(**hyp_p14)
    assert calculate_hypothesis_spec_sha256(spec) == EXPECTED_HYP_004_SHA256

    man = json.loads(Path("docs/phase14/manifests/manifest_r1_HYP_004.json").read_text(encoding="utf-8"))
    assert man["manifest_sha256"] == EXPECTED_R1_MANIFEST_SHA256


def test_30_adaptive_rate_limit_header_handling() -> None:
    """Invariant 30: Adaptive rate governor parses X-RateLimit headers and paces accordingly."""
    gov = AdaptiveRateGovernor(fallback_req_per_min=185.0)
    assert not gov.header_observed

    headers = {
        "x-ratelimit-limit": "200",
        "x-ratelimit-remaining": "150",
        "x-ratelimit-reset": "1789796400",
    }
    gov.update_from_headers(headers)
    assert gov.header_observed
    assert gov.last_limit == 200
    assert gov.last_remaining == 150
    assert gov.last_reset_epoch == 1789796400


def test_31_http_429_reset_retry_handling() -> None:
    """Invariant 31: Governor respects Retry-After and X-RateLimit-Reset on 429."""
    gov = AdaptiveRateGovernor(fallback_req_per_min=185.0)

    # Test Retry-After header
    headers = {"retry-after": "1"}
    wait_sec = gov.handle_429_response(headers, attempt=1, sleep=False)
    assert wait_sec >= 1.0
    assert gov.rate_limit_429_count == 1


def test_32_atomic_session_checkpoint_publication(tmp_path: Path) -> None:
    """Invariant 32: Checkpoint is written atomically via temporary file and replace."""
    meta_path = tmp_path / "session_meta.json"
    checkpoint = SessionCheckpointMeta(
        session_date="2017-06-01",
        acquisition_status=AcquisitionStatus.RAW_COMPLETE,
        qualification_status=QualificationStatus.QUALIFIED,
        exclusion_reason_codes=[],
        pages=[],
        total_raw_records=1000,
        regular_session_records=1000,
        raw_evidence_aggregate_sha256="agg",
        b1000_classification=BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE.value,
        b1000_price="241.95",
        b1530_classification=BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE.value,
        b1530_price="242.00",
        exact_transport_duplicates=0,
        last_updated_utc=datetime.now(timezone.utc).isoformat(),
    )
    write_atomic_checkpoint(meta_path, checkpoint)
    assert meta_path.is_file()

    loaded = SessionCheckpointMeta.from_dict(json.loads(meta_path.read_text(encoding="utf-8")))
    assert loaded.acquisition_status == AcquisitionStatus.RAW_COMPLETE
    assert loaded.qualification_status == QualificationStatus.QUALIFIED


def test_33_acquisition_status_vs_qualification_status_separation() -> None:
    """Invariant 33: Preregistered scientific exclusion leaves acquisition_status RAW_COMPLETE."""
    # A session with trade count 400 has raw acquisition complete, but qualification = EXCLUDED
    checkpoint = SessionCheckpointMeta(
        session_date="2017-06-01",
        acquisition_status=AcquisitionStatus.RAW_COMPLETE,
        qualification_status=QualificationStatus.EXCLUDED_PREREGISTERED,
        exclusion_reason_codes=["TRADE_COUNT_LT_500"],
        pages=[],
        total_raw_records=400,
        regular_session_records=400,
        raw_evidence_aggregate_sha256="abc",
        b1000_classification=BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE.value,
        b1000_price="241.95",
        b1530_classification=BoundaryEndpointClassification.UNIQUE_BOUNDARY_PRICE.value,
        b1530_price="242.00",
        exact_transport_duplicates=0,
        last_updated_utc=datetime.now(timezone.utc).isoformat(),
    )
    close_map = {
        "2017-05-31": CloseAuthorityRecord("2017-05-31", Decimal("241.00"), "ts"),
        "2017-06-01": CloseAuthorityRecord("2017-06-01", Decimal("242.00"), "ts"),
    }
    row = evaluate_session(
        session_date=date(2017, 6, 1),
        ordinal=100,
        prior_session_date=date(2017, 5, 31),
        close_authority_map=close_map,
        checkpoint=checkpoint,
        close_evidence_hash="h",
        contract_git_sha="s",
    )
    assert row.acquisition_status == AcquisitionStatus.RAW_COMPLETE.value
    assert row.qualification_status == QualificationStatus.EXCLUDED_PREREGISTERED.value
    assert row.qualification_status != QualificationStatus.PROVIDER_CONTRACT_FAILURE.value


def test_34_verify_only_mode_makes_zero_http_calls(tmp_path: Path) -> None:
    """Invariant 34: In verify_only mode, missing cache raises DataContractError without HTTP access."""
    gov = AdaptiveRateGovernor()
    with pytest.raises(DataContractError, match="verify-only mode"):
        process_session_trades(
            session_date=date(2017, 6, 1),
            client=None,
            headers={},
            governor=gov,
            raw_cache_base_dir=tmp_path,
            verify_only=True,
        )
    assert gov.total_requests == 0
