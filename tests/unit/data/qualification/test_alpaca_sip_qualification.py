"""Comprehensive unit test suite for Alpaca historical SIP data qualification foundation."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import ZoneInfo
import httpx
import pytest

from acash.core.domain.enums import BarTimeframe
from acash.core.domain.market_data import Bar
from acash.execution.alpaca.credentials import (
    AlpacaCredentialError,
    AlpacaCredentials,
    EnvAlpacaCredentialProvider,
)
from acash.data.qualification.client import (
    AlpacaAccessDeniedError,
    AlpacaAuthenticationError,
    AlpacaHistoricalSipClient,
    AlpacaRateLimitExceededError,
    SipContractViolationError,
)
from acash.data.qualification.engine import HistoricalSipQualificationEngine
from acash.data.qualification.guard import (
    FifteenMinuteAccessGuard,
    ProtectedWindowViolationError,
)
from acash.data.qualification.manifest import (
    compute_canonical_bars_sha256,
    compute_framed_composite_sha256,
    compute_page_sha256,
    save_evidence_package,
    serialize_manifest_to_json,
    verify_persisted_evidence_package,
)
from acash.data.qualification.models import (
    HistoricalSipBar,
    MarketDataFeed,
    OFFICIAL_CONTRACT_FEED,
    OFFICIAL_CONTRACT_PROVIDER,
    PriceAdjustment,
    ProvenanceBasis,
    QualificationCheckStatus,
    QualityFinding,
    QualityRuleCode,
    QualitySeverity,
    SipProvenanceManifest,
    SourceQualificationReport,
    SourceQualificationStatus,
    VwapAuthorityStatus,
)
from acash.data.qualification.session import (
    RthSessionBounds,
    VerifiedSessionSchedule,
)
from acash.data.qualification.validator import HistoricalBarValidator

NY_TZ = ZoneInfo("America/New_York")


# =============================================================================
# Mock Transports & Test Fixtures
# =============================================================================

class MockCredentialProvider(EnvAlpacaCredentialProvider):
    def __init__(self, key_id: str = "FAKE_KEY_ID_123", secret: str = "FAKE_SECRET_XYZ") -> None:
        super().__init__(
            venue="ALPACA_PAPER",
            api_key_id=key_id,
            api_secret=secret,
        )


def make_single_page_bars_json(symbol: str = "SPY", count: int = 5, start_hour_utc: int = 14) -> str:
    bars = []
    for i in range(count):
        dt = datetime(2024, 1, 2, start_hour_utc, 30 + i, 0, tzinfo=timezone.utc)
        bars.append({
            "t": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "o": 470.0 + i * 0.1,
            "h": 470.5 + i * 0.1,
            "l": 469.8 + i * 0.1,
            "c": 470.3 + i * 0.1,
            "v": 1000 + i * 10,
            "n": 150 + i,
            "vw": 470.25 + i * 0.1,
        })
    return json.dumps({"bars": bars, "symbol": symbol, "next_page_token": None})


# =============================================================================
# 1. FifteenMinuteAccessGuard Tests
# =============================================================================

def test_guard_rejects_timestamp_within_15_minutes() -> None:
    fixed_now = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
    guard = FifteenMinuteAccessGuard(minimum_age_minutes=15, clock=lambda: fixed_now)

    # 10 minutes ago (too recent)
    too_recent = fixed_now - timedelta(minutes=10)
    with pytest.raises(ProtectedWindowViolationError) as exc_info:
        guard.validate_requested_end(too_recent)
    assert "violates the 15-minute free SIP access guard" in str(exc_info.value)


def test_guard_accepts_timestamp_older_than_15_minutes() -> None:
    fixed_now = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
    guard = FifteenMinuteAccessGuard(minimum_age_minutes=15, clock=lambda: fixed_now)

    # Exactly 15 minutes ago
    boundary_15m = fixed_now - timedelta(minutes=15)
    guard.validate_requested_end(boundary_15m)

    # 1 day ago
    safe_historical = fixed_now - timedelta(days=1)
    guard.validate_requested_end(safe_historical)


# =============================================================================
# 2. Historical SIP Request Contract & Client Tests
# =============================================================================

def test_client_enforces_explicit_feed_and_adjustment_contract() -> None:
    client = AlpacaHistoricalSipClient(credential_provider=MockCredentialProvider())
    start_utc = datetime(2024, 1, 2, 14, 30, 0, tzinfo=timezone.utc)
    end_utc = datetime(2024, 1, 2, 21, 0, 0, tzinfo=timezone.utc)

    # Rejects IEX feed
    with pytest.raises(SipContractViolationError) as exc:
        client.fetch_historical_bars("SPY", start_utc, end_utc, feed=MarketDataFeed.IEX)
    assert "feed='sip'" in str(exc.value)

    # Rejects split adjustment
    with pytest.raises(SipContractViolationError) as exc:
        client.fetch_historical_bars("SPY", start_utc, end_utc, adjustment=PriceAdjustment.SPLIT)
    assert "adjustment='raw'" in str(exc.value)

    # Rejects non-1Min timeframe
    with pytest.raises(SipContractViolationError) as exc:
        client.fetch_historical_bars("SPY", start_utc, end_utc, timeframe="5Min")
    assert "timeframe='1Min'" in str(exc.value)


def test_client_verifies_request_params_and_headers_sent() -> None:
    captured_requests: List[httpx.Request] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, text=make_single_page_bars_json("SPY", count=2))

    transport = httpx.MockTransport(mock_handler)
    client = AlpacaHistoricalSipClient(
        credential_provider=MockCredentialProvider(key_id="TEST_KEY", secret="TEST_SECRET"),
        transport=transport,
    )

    start_utc = datetime(2024, 1, 2, 14, 30, 0, tzinfo=timezone.utc)
    end_utc = datetime(2024, 1, 2, 21, 0, 0, tzinfo=timezone.utc)
    result = client.fetch_historical_bars("SPY", start_utc, end_utc)

    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.url.path == "/v2/stocks/SPY/bars"
    assert req.url.params["feed"] == "sip"
    assert req.url.params["adjustment"] == "raw"
    assert req.url.params["timeframe"] == "1Min"
    assert req.headers["APCA-API-KEY-ID"] == "TEST_KEY"
    assert req.headers["APCA-API-SECRET-KEY"] == "TEST_SECRET"
    assert len(result.bars) == 2
    assert result.bars[0].trade_count == 150
    assert result.bars[0].provider_vwap == Decimal("470.25")


def test_client_fail_closed_on_401_and_403() -> None:
    # 401 Unauthorized
    t_401 = httpx.MockTransport(lambda req: httpx.Response(401, json={"message": "Unauthorized"}))
    client_401 = AlpacaHistoricalSipClient(credential_provider=MockCredentialProvider(), transport=t_401)
    start_utc = datetime(2024, 1, 2, 14, 30, 0, tzinfo=timezone.utc)
    end_utc = datetime(2024, 1, 2, 21, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(AlpacaAuthenticationError):
        client_401.fetch_historical_bars("SPY", start_utc, end_utc)

    # 403 Forbidden (SIP Access Denied)
    t_403 = httpx.MockTransport(lambda req: httpx.Response(403, json={"message": "SIP feed forbidden"}))
    client_403 = AlpacaHistoricalSipClient(credential_provider=MockCredentialProvider(), transport=t_403)

    with pytest.raises(AlpacaAccessDeniedError) as exc:
        client_403.fetch_historical_bars("SPY", start_utc, end_utc)
    assert "SIP feed access denied" in str(exc.value)


def test_client_bounded_retry_on_429() -> None:
    attempt = 0

    def retry_handler(req: httpx.Request) -> httpx.Response:
        nonlocal attempt
        attempt += 1
        if attempt < 3:
            return httpx.Response(429, headers={"Retry-After": "0.01"})
        return httpx.Response(200, text=make_single_page_bars_json("SPY", count=1))

    client = AlpacaHistoricalSipClient(
        credential_provider=MockCredentialProvider(),
        transport=httpx.MockTransport(retry_handler),
        max_retries_429=3,
        retry_delay_seconds=0.01,
    )
    start_utc = datetime(2024, 1, 2, 14, 30, 0, tzinfo=timezone.utc)
    end_utc = datetime(2024, 1, 2, 21, 0, 0, tzinfo=timezone.utc)

    result = client.fetch_historical_bars("SPY", start_utc, end_utc)
    assert attempt == 3
    assert len(result.bars) == 1


# =============================================================================
# 3. Pagination & Framing Hashing Tests
# =============================================================================

def test_pagination_and_framed_composite_hashing() -> None:
    p1 = {
        "bars": [{"t": "2024-01-02T14:30:00Z", "o": 470, "h": 471, "l": 469, "c": 470.5, "v": 100, "n": 10, "vw": 470.2}],
        "symbol": "SPY",
        "next_page_token": "PAGE_2_TOKEN",
    }
    p2 = {
        "bars": [{"t": "2024-01-02T14:31:00Z", "o": 470.5, "h": 471.2, "l": 470.1, "c": 471.0, "v": 150, "n": 15, "vw": 470.8}],
        "symbol": "SPY",
        "next_page_token": None,
    }

    def page_handler(req: httpx.Request) -> httpx.Response:
        token = req.url.params.get("page_token")
        if not token:
            return httpx.Response(200, text=json.dumps(p1))
        elif token == "PAGE_2_TOKEN":
            return httpx.Response(200, text=json.dumps(p2))
        return httpx.Response(400)

    client = AlpacaHistoricalSipClient(
        credential_provider=MockCredentialProvider(),
        transport=httpx.MockTransport(page_handler),
    )
    start_utc = datetime(2024, 1, 2, 14, 30, 0, tzinfo=timezone.utc)
    end_utc = datetime(2024, 1, 2, 21, 0, 0, tzinfo=timezone.utc)

    result = client.fetch_historical_bars("SPY", start_utc, end_utc)
    assert len(result.bars) == 2
    assert len(result.pages_raw_bytes) == 2
    assert len(result.pages_metadata) == 2
    assert result.pages_metadata[0].next_page_token == "PAGE_2_TOKEN"
    assert result.pages_metadata[1].next_page_token is None

    # Length-prefixed framing check
    digest_12 = compute_framed_composite_sha256(result.pages_raw_bytes)
    # Permuting page order produces a different hash
    digest_21 = compute_framed_composite_sha256([result.pages_raw_bytes[1], result.pages_raw_bytes[0]])
    assert digest_12 != digest_21

    canonical_bars_hash = compute_canonical_bars_sha256(result.bars)
    assert isinstance(canonical_bars_hash, str) and len(canonical_bars_hash) == 64


# =============================================================================
# 4. Credential Safety & Redaction Tests
# =============================================================================

def test_credentials_redaction() -> None:
    creds = AlpacaCredentials(api_key_id="SECRET_API_KEY", api_secret_ref="SUPER_SECRET_VALUE", _resolved=True)
    assert str(creds) == "********"
    assert "SUPER_SECRET_VALUE" not in repr(creds)
    assert "SECRET_API_KEY" not in repr(creds)


def test_missing_credentials_fails_closed() -> None:
    empty_provider = EnvAlpacaCredentialProvider(environ={})
    client = AlpacaHistoricalSipClient(credential_provider=empty_provider)
    start_utc = datetime(2024, 1, 2, 14, 30, 0, tzinfo=timezone.utc)
    end_utc = datetime(2024, 1, 2, 21, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(AlpacaCredentialError) as exc:
        client.fetch_historical_bars("SPY", start_utc, end_utc)
    assert "fail-closed" in str(exc.value)


# =============================================================================
# 5. Data Integrity & Validation Tests
# =============================================================================

def test_validator_detects_monotonicity_and_duplicates() -> None:
    validator = HistoricalBarValidator()
    t1 = datetime(2024, 1, 2, 14, 30, 0, tzinfo=timezone.utc)
    t2 = datetime(2024, 1, 2, 14, 29, 0, tzinfo=timezone.utc)  # Backward step

    bar1 = HistoricalSipBar(timestamp_utc=t1, open=Decimal("470"), high=Decimal("471"), low=Decimal("469"), close=Decimal("470.5"), volume=Decimal("100"))
    bar2 = HistoricalSipBar(timestamp_utc=t2, open=Decimal("470"), high=Decimal("471"), low=Decimal("469"), close=Decimal("470.5"), volume=Decimal("100"))

    findings = validator.validate_bars([bar1, bar2])
    assert any(f.rule == QualityRuleCode.NON_MONOTONIC_TIMESTAMP and f.severity == QualitySeverity.ERROR for f in findings)
    assert validator.has_blocking_errors(findings) is True


def test_validator_detects_duplicate_timestamps() -> None:
    validator = HistoricalBarValidator()
    t1 = datetime(2024, 1, 2, 14, 30, 0, tzinfo=timezone.utc)

    bar1 = HistoricalSipBar(timestamp_utc=t1, open=Decimal("470"), high=Decimal("471"), low=Decimal("469"), close=Decimal("470.5"), volume=Decimal("100"))
    bar2 = HistoricalSipBar(timestamp_utc=t1, open=Decimal("470"), high=Decimal("471"), low=Decimal("469"), close=Decimal("470.5"), volume=Decimal("100"))

    findings = validator.validate_bars([bar1, bar2])
    assert any(f.rule == QualityRuleCode.DUPLICATE_TIMESTAMP and f.severity == QualitySeverity.ERROR for f in findings)


# =============================================================================
# 6. Calendar / Missing-Bar Semantics Tests (Human Correction 2)
# =============================================================================

def test_unverified_calendar_authority_emits_info_finding_without_false_missing_data() -> None:
    validator = HistoricalBarValidator()
    # 3 bars on 2024-01-02
    bars = [
        HistoricalSipBar(
            timestamp_utc=datetime(2024, 1, 2, 14, 30 + i, 0, tzinfo=timezone.utc),
            open=Decimal("470"),
            high=Decimal("471"),
            low=Decimal("469"),
            close=Decimal("470.5"),
            volume=Decimal("100"),
        )
        for i in range(3)
    ]

    # Run without verified session schedule
    findings = validator.validate_bars(bars, verified_schedules=None)

    # Must emit CALENDAR_AUTHORITY_UNVERIFIED (INFO severity)
    cal_findings = [f for f in findings if f.rule == QualityRuleCode.CALENDAR_AUTHORITY_UNVERIFIED]
    assert len(cal_findings) == 1
    assert cal_findings[0].severity == QualitySeverity.INFO

    # Must NOT emit MISSING_BAR or ERROR
    assert not any(f.rule == QualityRuleCode.MISSING_BAR for f in findings)
    assert validator.has_blocking_errors(findings) is False


def test_verified_session_schedule_detects_missing_bars_without_imputation() -> None:
    validator = HistoricalBarValidator()
    d = date(2024, 1, 2)
    # Expected 5 bars from 14:30 to 14:35 UTC, but we only supply 3 bars (missing 14:32 and 14:34)
    bars = [
        HistoricalSipBar(
            timestamp_utc=datetime(2024, 1, 2, 14, m, 0, tzinfo=timezone.utc),
            open=Decimal("470"),
            high=Decimal("471"),
            low=Decimal("469"),
            close=Decimal("470.5"),
            volume=Decimal("100"),
        )
        for m in (30, 31, 33)
    ]

    schedule = VerifiedSessionSchedule(
        trading_date=d,
        session_open_utc=datetime(2024, 1, 2, 14, 30, 0, tzinfo=timezone.utc),
        session_close_utc=datetime(2024, 1, 2, 14, 35, 0, tzinfo=timezone.utc),
        is_early_close=False,
        expected_bar_count=5,
    )

    findings = validator.validate_bars(bars, verified_schedules={d: schedule})
    missing_findings = [f for f in findings if f.rule == QualityRuleCode.MISSING_BAR]
    assert len(missing_findings) == 1
    assert missing_findings[0].details["missing_count"] == 2


def test_out_of_hours_bars_flagged() -> None:
    validator = HistoricalBarValidator()
    # 08:00 ET (13:00 UTC) is pre-market outside 09:30-16:00 ET
    bar_pre = HistoricalSipBar(
        timestamp_utc=datetime(2024, 1, 2, 13, 0, 0, tzinfo=timezone.utc),
        open=Decimal("470"),
        high=Decimal("471"),
        low=Decimal("469"),
        close=Decimal("470.5"),
        volume=Decimal("100"),
    )
    findings = validator.validate_bars([bar_pre])
    assert any(f.rule == QualityRuleCode.OUTSIDE_REGULAR_HOURS and f.severity == QualitySeverity.WARNING for f in findings)


def test_rth_session_query_interval_adapts_inclusive_provider_end() -> None:
    # 2026-09-15 is EDT (UTC-4)
    d_edt = date(2026, 9, 15)
    start_utc, end_utc = RthSessionBounds.get_rth_query_interval(d_edt)

    # 09:30:00 EDT -> 13:30:00Z
    assert start_utc == datetime(2026, 9, 15, 13, 30, 0, tzinfo=timezone.utc)
    # 16:00:00 EDT - 1s -> 15:59:59 EDT -> 19:59:59Z
    assert end_utc == datetime(2026, 9, 15, 19, 59, 59, tzinfo=timezone.utc)

    # In standard Alpaca RFC3339 serialization:
    start_str = start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = end_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert start_str == "2026-09-15T13:30:00Z"
    assert end_str == "2026-09-15T19:59:59Z"

    # Winter date (EST, UTC-5): 2024-01-16
    d_est = date(2024, 1, 16)
    start_est, end_est = RthSessionBounds.get_rth_query_interval(d_est)
    assert start_est == datetime(2024, 1, 16, 14, 30, 0, tzinfo=timezone.utc)
    assert end_est == datetime(2024, 1, 16, 20, 59, 59, tzinfo=timezone.utc)


def test_rth_logical_interval_and_390_continuous_minutes() -> None:
    # Verify exactly 390 1-minute buckets [09:30, 16:00) ET for 2026-09-15
    validator = HistoricalBarValidator()
    bars_390 = [
        HistoricalSipBar(
            timestamp_utc=datetime(2026, 9, 15, 13, 30, 0, tzinfo=timezone.utc) + timedelta(minutes=i),
            open=Decimal("760"),
            high=Decimal("761"),
            low=Decimal("759"),
            close=Decimal("760.5"),
            volume=Decimal("1000"),
        )
        for i in range(390)
    ]

    assert len(bars_390) == 390
    assert bars_390[0].timestamp_utc == datetime(2026, 9, 15, 13, 30, 0, tzinfo=timezone.utc)
    assert bars_390[-1].timestamp_utc == datetime(2026, 9, 15, 19, 59, 0, tzinfo=timezone.utc)

    # All 390 bars must be strictly within RTH
    for b in bars_390:
        assert RthSessionBounds.is_within_rth(b.timestamp_utc) is True
    findings = validator.validate_bars(bars_390)
    assert not any(f.rule == QualityRuleCode.OUTSIDE_REGULAR_HOURS for f in findings)

    # A 391st bar at 20:00:00Z (16:00 ET) is OUTSIDE continuous RTH
    bar_1600 = HistoricalSipBar(
        timestamp_utc=datetime(2026, 9, 15, 20, 0, 0, tzinfo=timezone.utc),
        open=Decimal("757.38"),
        high=Decimal("757.72"),
        low=Decimal("757.38"),
        close=Decimal("757.66"),
        volume=Decimal("1749372"),
    )
    assert RthSessionBounds.is_within_rth(bar_1600.timestamp_utc) is False
    findings_with_391 = validator.validate_bars([*bars_390, bar_1600])
    out_of_hours = [f for f in findings_with_391 if f.rule == QualityRuleCode.OUTSIDE_REGULAR_HOURS]
    assert len(out_of_hours) == 1
    assert out_of_hours[0].timestamp_utc == datetime(2026, 9, 15, 20, 0, 0, tzinfo=timezone.utc)


# =============================================================================
# 7. Qualification Ceiling & Engine Tests (Documented Contract & Persistence)
# =============================================================================

def test_engine_enforces_qualification_ceiling_when_provenance_is_unverified() -> None:
    # HTTP 200 OK but retrieval feed was not SIP (e.g. IEX fallback)
    raw_json = make_single_page_bars_json("SPY", count=5)
    t = httpx.MockTransport(lambda req: httpx.Response(200, text=raw_json))
    client = AlpacaHistoricalSipClient(credential_provider=MockCredentialProvider(), transport=t)

    # Monkeypatch client fetch to simulate non-SIP retrieval to verify ceiling
    original_fetch = client.fetch_historical_bars
    def mock_fetch(*args: Any, **kwargs: Any) -> Any:
        res = original_fetch(*args, **kwargs)
        object.__setattr__(res, "feed_requested", "iex")
        return res
    client.fetch_historical_bars = mock_fetch  # type: ignore[method-assign]

    engine = HistoricalSipQualificationEngine(client=client)

    start_utc = datetime(2024, 1, 2, 14, 30, 0, tzinfo=timezone.utc)
    end_utc = datetime(2024, 1, 2, 21, 0, 0, tzinfo=timezone.utc)

    report = engine.run_qualification("SPY", start_utc, end_utc)

    # Contract, Network, and Integrity are PASS
    assert report.request_contract_status == QualificationCheckStatus.PASS
    assert report.network_access_status == QualificationCheckStatus.PASS
    assert report.data_integrity_status == QualificationCheckStatus.PASS

    # Provider provenance is UNVERIFIED (feed was not SIP)
    assert report.provider_provenance_status == QualificationCheckStatus.UNVERIFIED
    assert report.manifest.provenance_basis == ProvenanceBasis.UNVERIFIED

    # Ceiling enforced: CANNOT be DATA_SOURCE_TECHNICALLY_QUALIFIED
    assert report.overall_status == SourceQualificationStatus.CONTRACT_VERIFIED
    assert report.vwap_authority_status == VwapAuthorityStatus.UNVERIFIED
    assert report.manifest.source_qualification_status == SourceQualificationStatus.CONTRACT_VERIFIED


def test_documented_contract_provenance_basis_pass(tmp_path: Path) -> None:
    # HTTP 200 OK WITHOUT response-side feed echo
    raw_json = make_single_page_bars_json("SPY", count=5)
    t = httpx.MockTransport(lambda req: httpx.Response(200, text=raw_json))
    client = AlpacaHistoricalSipClient(credential_provider=MockCredentialProvider(), transport=t)
    engine = HistoricalSipQualificationEngine(client=client)

    start_utc = datetime(2024, 1, 2, 14, 30, 0, tzinfo=timezone.utc)
    end_utc = datetime(2024, 1, 2, 21, 0, 0, tzinfo=timezone.utc)

    report = engine.run_qualification("SPY", start_utc, end_utc, output_dir=tmp_path)

    assert report.request_contract_status == QualificationCheckStatus.PASS
    assert report.network_access_status == QualificationCheckStatus.PASS
    assert report.data_integrity_status == QualificationCheckStatus.PASS
    assert report.provider_provenance_status == QualificationCheckStatus.PASS

    # Documented contract basis established
    assert report.manifest.provenance_basis == ProvenanceBasis.DOCUMENTED_API_CONTRACT
    assert report.manifest.feed_response_provenance == "UNVERIFIED"  # not faked
    assert report.manifest.source_contract_provider == OFFICIAL_CONTRACT_PROVIDER
    assert report.manifest.source_contract_feed == OFFICIAL_CONTRACT_FEED
    assert "https://docs.alpaca.markets/us/reference/stockbars" in report.manifest.source_contract_references

    # Promoted via documented contract
    assert report.overall_status == SourceQualificationStatus.DATA_SOURCE_TECHNICALLY_QUALIFIED
    assert report.vwap_authority_status == VwapAuthorityStatus.QUALIFIED


def test_response_side_feed_echo_promotes_to_response_explicit() -> None:
    # HTTP 200 OK WITH feed confirmed in header
    raw_json = make_single_page_bars_json("SPY", count=5)
    t = httpx.MockTransport(lambda req: httpx.Response(200, text=raw_json, headers={"X-Feed": "sip"}))
    client = AlpacaHistoricalSipClient(credential_provider=MockCredentialProvider(), transport=t)
    engine = HistoricalSipQualificationEngine(client=client)

    start_utc = datetime(2024, 1, 2, 14, 30, 0, tzinfo=timezone.utc)
    end_utc = datetime(2024, 1, 2, 21, 0, 0, tzinfo=timezone.utc)

    report = engine.run_qualification("SPY", start_utc, end_utc)

    assert report.manifest.provenance_basis == ProvenanceBasis.RESPONSE_EXPLICIT
    assert report.manifest.feed_response_provenance == "FEED_CONFIRMED_IN_HEADER"
    assert report.provider_provenance_status == QualificationCheckStatus.PASS
    assert report.overall_status == SourceQualificationStatus.DATA_SOURCE_TECHNICALLY_QUALIFIED
    assert report.vwap_authority_status == VwapAuthorityStatus.QUALIFIED


def test_raw_response_bytes_persisted_exactly_and_verified(tmp_path: Path) -> None:
    # Unique raw JSON with irregular spacing to prove exact un-reformatted byte persistence
    unique_raw = b'{\n  "bars": [\n    {"t": "2024-01-02T14:30:00Z", "o": 470.0, "h": 471.0, "l": 469.0, "c": 470.5, "v": 1000, "n": 100, "vw": 470.2}\n  ],\n  "symbol": "SPY",\n  "next_page_token": null\n}'
    t = httpx.MockTransport(lambda req: httpx.Response(200, content=unique_raw))
    client = AlpacaHistoricalSipClient(credential_provider=MockCredentialProvider(), transport=t)
    engine = HistoricalSipQualificationEngine(client=client)

    start_utc = datetime(2024, 1, 2, 14, 30, 0, tzinfo=timezone.utc)
    end_utc = datetime(2024, 1, 2, 21, 0, 0, tzinfo=timezone.utc)

    report = engine.run_qualification("SPY", start_utc, end_utc, output_dir=tmp_path)
    evidence_dir = tmp_path / report.manifest.manifest_id

    # Verify exact files exist
    assert evidence_dir.exists()
    page_file = evidence_dir / "page-0001.raw.json"
    manifest_file = evidence_dir / "manifest.json"
    assert page_file.exists()
    assert manifest_file.exists()

    # Exact bytes check (bit-for-bit, not re-serialized)
    persisted_bytes = page_file.read_bytes()
    assert persisted_bytes == unique_raw

    # Length and SHA-256 in manifest match
    assert report.manifest.pages[0].byte_length == len(unique_raw)
    assert report.manifest.pages[0].raw_sha256 == compute_page_sha256(unique_raw)
    assert report.manifest.pages[0].relative_artifact_path == "page-0001.raw.json"

    # Verification function passes
    is_valid, errors = verify_persisted_evidence_package(evidence_dir)
    assert is_valid is True, f"Validation errors: {errors}"
    assert errors == []


def test_verify_persisted_evidence_package_detects_tampering(tmp_path: Path) -> None:
    raw_json = make_single_page_bars_json("SPY", count=2).encode("utf-8")
    t = httpx.MockTransport(lambda req: httpx.Response(200, content=raw_json))
    client = AlpacaHistoricalSipClient(credential_provider=MockCredentialProvider(), transport=t)
    engine = HistoricalSipQualificationEngine(client=client)

    start_utc = datetime(2024, 1, 2, 14, 30, 0, tzinfo=timezone.utc)
    end_utc = datetime(2024, 1, 2, 21, 0, 0, tzinfo=timezone.utc)

    report = engine.run_qualification("SPY", start_utc, end_utc, output_dir=tmp_path)
    evidence_dir = tmp_path / report.manifest.manifest_id

    page_file = evidence_dir / "page-0001.raw.json"
    # Tamper with 1 byte
    page_file.write_bytes(raw_json + b" ")

    is_valid, errors = verify_persisted_evidence_package(evidence_dir)
    assert is_valid is False
    assert any("SHA-256 mismatch" in err or "length mismatch" in err for err in errors)


def test_secrets_absent_from_artifacts_manifest_and_errors(tmp_path: Path) -> None:
    secret_key = "TOP_SECRET_ALPACA_KEY_DO_NOT_LEAK"
    provider = MockCredentialProvider(key_id="KEY_123", secret=secret_key)
    raw_json = make_single_page_bars_json("SPY", count=2)
    t = httpx.MockTransport(lambda req: httpx.Response(200, text=raw_json))
    client = AlpacaHistoricalSipClient(credential_provider=provider, transport=t)
    engine = HistoricalSipQualificationEngine(client=client)

    start_utc = datetime(2024, 1, 2, 14, 30, 0, tzinfo=timezone.utc)
    end_utc = datetime(2024, 1, 2, 21, 0, 0, tzinfo=timezone.utc)

    report = engine.run_qualification("SPY", start_utc, end_utc, output_dir=tmp_path)
    evidence_dir = tmp_path / report.manifest.manifest_id

    for file_path in evidence_dir.iterdir():
        assert secret_key not in file_path.name
        content = file_path.read_text(encoding="utf-8")
        assert secret_key not in content


def test_asof_parameter_passed_in_client_and_manifest(tmp_path: Path) -> None:
    captured_requests: List[httpx.Request] = []
    raw_json = make_single_page_bars_json("SPY", count=2)

    def handle_request(req: httpx.Request) -> httpx.Response:
        captured_requests.append(req)
        return httpx.Response(200, text=raw_json)

    t = httpx.MockTransport(handle_request)
    client = AlpacaHistoricalSipClient(credential_provider=MockCredentialProvider(), transport=t)
    engine = HistoricalSipQualificationEngine(client=client)

    start_utc = datetime(2024, 1, 2, 14, 30, 0, tzinfo=timezone.utc)
    end_utc = datetime(2024, 1, 2, 21, 0, 0, tzinfo=timezone.utc)

    report = engine.run_qualification(
        "SPY", start_utc, end_utc, output_dir=tmp_path, asof="2026-09-15"
    )

    # Check query params sent to Alpaca
    assert len(captured_requests) == 1
    assert "asof=2026-09-15" in str(captured_requests[0].url)
    assert report.manifest.asof == "2026-09-15"


def test_qualification_ceiling_fail_closed_when_data_integrity_fails(tmp_path: Path) -> None:
    # Duplicate bar timestamps -> integrity FAIL
    t1 = datetime(2024, 1, 2, 14, 30, 0, tzinfo=timezone.utc)
    dup_bars_json = json.dumps({
        "bars": [
            {"t": t1.strftime("%Y-%m-%dT%H:%M:%SZ"), "o": 470.0, "h": 471.0, "l": 469.0, "c": 470.5, "v": 1000, "n": 100, "vw": 470.2},
            {"t": t1.strftime("%Y-%m-%dT%H:%M:%SZ"), "o": 470.0, "h": 471.0, "l": 469.0, "c": 470.5, "v": 1000, "n": 100, "vw": 470.2},
        ],
        "symbol": "SPY",
        "next_page_token": None,
    })
    t = httpx.MockTransport(lambda req: httpx.Response(200, text=dup_bars_json))
    client = AlpacaHistoricalSipClient(credential_provider=MockCredentialProvider(), transport=t)
    engine = HistoricalSipQualificationEngine(client=client)

    start_utc = datetime(2024, 1, 2, 14, 30, 0, tzinfo=timezone.utc)
    end_utc = datetime(2024, 1, 2, 21, 0, 0, tzinfo=timezone.utc)

    report = engine.run_qualification("SPY", start_utc, end_utc, output_dir=tmp_path)

    assert report.data_integrity_status == QualificationCheckStatus.FAIL
    # Provenance cannot PASS under DOCUMENTED_API_CONTRACT when integrity fails
    assert report.provider_provenance_status == QualificationCheckStatus.UNVERIFIED
    assert report.manifest.provenance_basis == ProvenanceBasis.UNVERIFIED
    assert report.overall_status == SourceQualificationStatus.REJECTED
    assert report.vwap_authority_status == VwapAuthorityStatus.UNVERIFIED


# =============================================================================
# 8. Conversion to Canonical Bar
# =============================================================================

def test_conversion_to_canonical_bar_preserves_invariants_without_mutating_core_bar() -> None:
    t = datetime(2024, 1, 2, 14, 30, 0, tzinfo=timezone.utc)
    sip_bar = HistoricalSipBar(
        timestamp_utc=t,
        open=Decimal("470.10"),
        high=Decimal("470.90"),
        low=Decimal("469.80"),
        close=Decimal("470.50"),
        volume=Decimal("123456"),
        trade_count=789,
        provider_vwap=Decimal("470.35"),
    )

    core_bar: Bar = sip_bar.to_canonical_bar("SPY", BarTimeframe.M1)
    assert core_bar.symbol == "SPY"
    assert core_bar.timeframe == BarTimeframe.M1
    assert core_bar.event_start_utc == t
    assert core_bar.event_end_utc == t + timedelta(seconds=60)
    assert core_bar.open == Decimal("470.10")
    assert core_bar.high == Decimal("470.90")
    assert core_bar.low == Decimal("469.80")
    assert core_bar.close == Decimal("470.50")
    assert core_bar.volume == Decimal("123456")


# =============================================================================
# 9. CLI Probe Safety & Dry-Run Tests
# =============================================================================

def test_cli_probe_defaults_to_dry_run_with_zero_network_calls() -> None:
    from acash.data.qualification.cli import parse_args, run_probe

    args = parse_args(["--symbol", "SPY", "--date", "2024-01-02"])
    assert args.execute_network is False

    # Dry-run returns 0 and performs zero network calls
    exit_code = run_probe(args)
    assert exit_code == 0
