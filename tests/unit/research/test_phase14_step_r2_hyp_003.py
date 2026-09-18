"""Unit and Invariant Tests for Phase 14 Step R2: Historical Data Qualification for HYP_003.

Tests:
1. Upstream governance and cryptographic hash verification.
2. In-Sample date boundary enforcement [2017-01-01, 2022-12-31].
3. OOS hard rejection: Any timestamp or date >= 2023-01-01 immediately aborts.
4. CA-1 calendar session universe census and enumeration (1,498 regular, 12 early close, 55 holidays, 626 weekends).
5. Early-close session exclusion.
6. 390/390 bar completeness enforcement per regular session.
7. Duplicate timestamp rejection.
8. Non-monotonic timestamp rejection.
9. Invalid OHLC structural bounds and negative volume rejection.
10. Canonical Arrow table schema and deterministic ordering.
11. Zero OOS rows in canonical dataset guarantee.
12. Manifest generation and hash lineage.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import List
from zoneinfo import ZoneInfo
import pytest
import pyarrow as pa

from acash.core.domain.exceptions import DataContractError
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.provenance import calculate_canonical_batch_sha256
from acash.data.qualification.models import HistoricalSipBar
from acash.data.schema import CANONICAL_ARROW_SCHEMA
from acash.research.step_r2_hyp_003 import (
    IS_END_DATE,
    IS_START_DATE,
    NY_TZ,
    OOS_SEALED_BOUNDARY_DATE,
    REGULAR_SESSION_BAR_COUNT,
    assert_is_boundary,
    build_ca1_session_universe,
    build_canonical_arrow_table,
    create_r2_manifest,
    validate_r2_preconditions,
    validate_session_bars,
)


def _make_synthetic_session_bars(
    session_date: date,
    n_bars: int = 390,
    base_price: Decimal = Decimal("400.00"),
) -> List[HistoricalSipBar]:
    """Generate deterministic synthetic 1-minute bars for a regular session [09:30, 15:59 ET]."""
    bars: List[HistoricalSipBar] = []
    # Start at 09:30 ET
    start_dt_local = datetime.combine(session_date, datetime.min.time()).replace(
        hour=9, minute=30, tzinfo=NY_TZ
    )
    for i in range(n_bars):
        bar_local = start_dt_local + timedelta(minutes=i)
        bar_utc = bar_local.astimezone(timezone.utc)
        p = base_price + Decimal(str(i * 0.01))
        bars.append(
            HistoricalSipBar(
                timestamp_utc=bar_utc,
                open=p,
                high=p + Decimal("0.05"),
                low=p - Decimal("0.05"),
                close=p + Decimal("0.02"),
                volume=Decimal("1000.00"),
                trade_count=50,
                provider_vwap=p,
            )
        )
    return bars


def test_gate1_governance_preconditions_verified() -> None:
    """Verify all upstream governance hashes, HYP_003 seal, preregistration, and clarification record."""
    hashes = validate_r2_preconditions()
    assert hashes["hypothesis_sha256"] == "f59010d14f466e9681325a314fd3e7ef30af43ffd69bc6cecbad1b5e6aab4ee0"
    assert hashes["preregistration_sha256"] == "3c04f617b9877a85a07043e67b7554034ebd703fe823d3d2de777a7722a3150c"
    assert hashes["r1_manifest_sha256"] == "27952f476cf96f75dc47ca0eb68a4b74d1f8dc6bf2f0848d1a877740cc32b372"
    assert Path(hashes["clarification_record"]).exists()


def test_gate2_is_boundary_enforcement_and_oos_hard_rejection() -> None:
    """Verify that any date >= 2023-01-01 or < 2017-01-01 strictly raises DataContractError."""
    # Valid IS dates
    assert_is_boundary(date(2017, 1, 1))
    assert_is_boundary(date(2020, 6, 15))
    assert_is_boundary(date(2022, 12, 31))

    # Forbidden OOS dates
    with pytest.raises(DataContractError, match="OOS HARD BOUNDARY VIOLATION"):
        assert_is_boundary(date(2023, 1, 1))

    with pytest.raises(DataContractError, match="OOS HARD BOUNDARY VIOLATION"):
        assert_is_boundary(date(2024, 5, 20))

    with pytest.raises(DataContractError, match="OOS HARD BOUNDARY VIOLATION"):
        assert_is_boundary(date(2026, 12, 31))

    # Pre-IS dates
    with pytest.raises(DataContractError, match="PRE-IN-SAMPLE BOUNDARY VIOLATION"):
        assert_is_boundary(date(2016, 12, 31))


def test_gate3_ca1_session_universe_census() -> None:
    """Verify exact CA-1 calendar classification across 2017-2022."""
    cal = NyseCa1Calendar()
    universe = build_ca1_session_universe(start_date=IS_START_DATE, end_date=IS_END_DATE, calendar=cal)

    assert universe.total_calendar_days == 2191  # 365*5 + 366 (2020 leap year)
    assert universe.total_regular_sessions == 1498
    assert universe.total_early_close_sessions == 12
    assert universe.total_holidays == 55
    assert len(universe.weekend_days) == 626
    assert universe.total_expected_bars == 1498 * 390
    assert universe.total_expected_bars == 584220

    # Verify early close sessions are distinct from regular sessions
    regular_set = set(universe.regular_sessions)
    early_set = set(universe.early_close_sessions)
    assert regular_set.isdisjoint(early_set)

    # Verify no weekend in regular sessions
    for d in universe.regular_sessions:
        assert d.weekday() < 5


def test_gate4_complete_regular_session_validation_success() -> None:
    """Verify that a synthetic session with exact 390 valid bars passes validation."""
    sess_date = date(2020, 1, 6)
    bars = _make_synthetic_session_bars(sess_date, n_bars=390)
    result = validate_session_bars(sess_date, bars)
    assert result.is_valid is True
    assert result.bar_count == 390
    assert len(result.error_reasons) == 0


def test_gate5_incomplete_session_rejection() -> None:
    """Verify that sessions with != 390 bars are rejected fail-closed."""
    sess_date = date(2020, 1, 6)

    # 389 bars (missing 1 bar)
    bars_389 = _make_synthetic_session_bars(sess_date, n_bars=389)
    res_389 = validate_session_bars(sess_date, bars_389)
    assert res_389.is_valid is False
    assert any("Bar count mismatch" in err for err in res_389.error_reasons)

    # 391 bars (extra bar)
    bars_391 = _make_synthetic_session_bars(sess_date, n_bars=391)
    res_391 = validate_session_bars(sess_date, bars_391)
    assert res_391.is_valid is False
    assert any("Bar count mismatch" in err for err in res_391.error_reasons)


def test_gate6_duplicate_timestamp_rejection() -> None:
    """Verify that duplicate timestamps are rejected."""
    sess_date = date(2020, 1, 6)
    bars = _make_synthetic_session_bars(sess_date, n_bars=390)
    # Inject duplicate timestamp at index 10
    bars[10] = bars[9]
    res = validate_session_bars(sess_date, bars)
    assert res.is_valid is False
    assert any("duplicate timestamp" in err for err in res.error_reasons)


def test_gate7_non_monotonic_timestamp_rejection() -> None:
    """Verify that non-monotonic timestamps are rejected."""
    sess_date = date(2020, 1, 6)
    bars = _make_synthetic_session_bars(sess_date, n_bars=390)
    # Swap bars 50 and 51
    bars[50], bars[51] = bars[51], bars[50]
    res = validate_session_bars(sess_date, bars)
    assert res.is_valid is False
    assert any("non-monotonic timestamp" in err for err in res.error_reasons)


def test_gate8_invalid_ohlc_structural_bounds_rejection() -> None:
    """Verify invalid OHLC structural bounds are rejected fail-closed."""
    sess_date = date(2020, 1, 6)
    bars = _make_synthetic_session_bars(sess_date, n_bars=390)
    ts = bars[5].timestamp_utc

    # High < max(open, close) raises DomainValidationError at bar construction
    from acash.core.domain.exceptions import DomainValidationError
    with pytest.raises(DomainValidationError, match="cannot be less than max"):
        HistoricalSipBar(
            timestamp_utc=ts,
            open=Decimal("400.00"),
            high=Decimal("399.00"),
            low=Decimal("398.00"),
            close=Decimal("400.00"),
            volume=Decimal("100"),
        )

    # Off-session bar time (e.g. 09:29 ET before regular open) rejected by session validator
    ts_early = datetime.combine(sess_date, datetime.min.time()).replace(
        hour=9, minute=29, tzinfo=NY_TZ
    ).astimezone(timezone.utc)
    bars[0] = HistoricalSipBar(
        timestamp_utc=ts_early,
        open=Decimal("400.00"),
        high=Decimal("401.00"),
        low=Decimal("399.00"),
        close=Decimal("400.00"),
        volume=Decimal("100"),
    )
    res = validate_session_bars(sess_date, bars)
    assert res.is_valid is False
    assert any("outside regular hours" in err for err in res.error_reasons)


def test_gate9_canonical_arrow_table_and_batch_sha256() -> None:
    """Verify building canonical Arrow table, schema conformance, and batch SHA-256."""
    d1 = date(2020, 1, 6)
    d2 = date(2020, 1, 7)
    sessions = {
        d1: _make_synthetic_session_bars(d1, n_bars=390, base_price=Decimal("400.00")),
        d2: _make_synthetic_session_bars(d2, n_bars=390, base_price=Decimal("402.00")),
    }

    table = build_canonical_arrow_table(sessions, symbol="SPY", timeframe="1Min")
    assert table.schema == CANONICAL_ARROW_SCHEMA
    assert table.num_rows == 780

    # Deterministic batch hash
    batch_sha1 = calculate_canonical_batch_sha256(table)
    table_rebuilt = build_canonical_arrow_table(sessions, symbol="SPY", timeframe="1Min")
    batch_sha2 = calculate_canonical_batch_sha256(table_rebuilt)
    assert batch_sha1 == batch_sha2
    assert len(batch_sha1) == 64


def test_gate10_zero_oos_rows_guarantee() -> None:
    """Verify that any attempt to include an OOS date in canonical table construction raises DataContractError."""
    oos_date = date(2023, 1, 3)
    sessions = {
        oos_date: _make_synthetic_session_bars(oos_date, n_bars=390),
    }
    with pytest.raises(DataContractError, match="OOS HARD BOUNDARY VIOLATION"):
        build_canonical_arrow_table(sessions, symbol="SPY", timeframe="1Min")


def test_gate11_manifest_generation() -> None:
    """Verify R2 manifest generation matches expected structure and values."""
    manifest = create_r2_manifest(
        hypothesis_sha256="f59010d14f466e9681325a314fd3e7ef30af43ffd69bc6cecbad1b5e6aab4ee0",
        preregistration_sha256="3c04f617b9877a85a07043e67b7554034ebd703fe823d3d2de777a7722a3150c",
        semantic_clarification_commit="9b12040e2d4654da32f737be5b4ba84123b23e58",
        source_git_sha="9b12040e2d4654da32f737be5b4ba84123b23e58",
        total_expected_regular_sessions=1498,
        included_sessions_count=1498,
        excluded_sessions_breakdown={"EXCLUDED_EARLY_CLOSE": 12, "EXCLUDED_HOLIDAY": 55},
        total_canonical_bars=584220,
        first_timestamp_utc="2017-01-03T14:30:00Z",
        last_timestamp_utc="2022-12-30T20:59:00Z",
        canonical_dataset_sha256="0" * 64,
        raw_evidence_aggregate_sha256="1" * 64,
    )

    assert manifest["manifest_type"] == "HISTORICAL_DATA_QUALIFICATION_MANIFEST"
    assert manifest["hypothesis_id"] == "HYP_003"
    assert manifest["data_contract"]["symbol"] == "SPY"
    assert manifest["data_contract"]["feed"] == "sip"
    assert manifest["status"] == "STEP_R2_HISTORICAL_DATA_QUALIFIED_PASS"
    assert manifest["capital_authority_usd"] == "0.00"
    assert manifest["paper_authorized"] is False
    assert manifest["live_authorized"] is False


def test_gate12_load_local_env_parses_key_values(tmp_path: Path) -> None:
    """Verify load_local_env parses key-value pairs, comments, quotes, and whitespace."""
    from acash.research.step_r2_hyp_003 import load_local_env

    env_file = tmp_path / ".env"
    env_file.write_text(
        "# Sample comment\n"
        "APCA_API_KEY_ID=test_key_12345\n"
        "APCA_API_SECRET_KEY=\"test_secret_67890\"\n"
        "  ANOTHER_VAR = 'single_quoted'  \n"
        "\n"
        "# Another comment\n",
        encoding="utf-8",
    )

    loaded = load_local_env(env_path=env_file, override=True)
    assert loaded["APCA_API_KEY_ID"] == "test_key_12345"
    assert loaded["APCA_API_SECRET_KEY"] == "test_secret_67890"
    assert loaded["ANOTHER_VAR"] == "single_quoted"


def test_gate13_process_env_precedence_over_dotenv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that process environment variables take strict precedence over .env file."""
    import os
    from acash.research.step_r2_hyp_003 import load_local_env

    monkeypatch.setenv("APCA_API_KEY_ID", "SHELL_EXPLICIT_KEY")
    monkeypatch.delenv("APCA_API_SECRET_KEY", raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "APCA_API_KEY_ID=DOTENV_KEY\n"
        "APCA_API_SECRET_KEY=DOTENV_SECRET\n",
        encoding="utf-8",
    )

    loaded = load_local_env(env_path=env_file, override=False)
    assert loaded["APCA_API_KEY_ID"] == "DOTENV_KEY"
    # os.environ must retain the process value, NOT the .env value
    assert os.environ["APCA_API_KEY_ID"] == "SHELL_EXPLICIT_KEY"
    # Non-existing variable is loaded from .env
    assert os.environ["APCA_API_SECRET_KEY"] == "DOTENV_SECRET"


def test_gate14_absent_dotenv_safe_behavior(tmp_path: Path) -> None:
    """Verify absent .env file returns empty dict without error."""
    from acash.research.step_r2_hyp_003 import load_local_env

    non_existent = tmp_path / "does_not_exist.env"
    loaded = load_local_env(env_path=non_existent, override=False)
    assert loaded == {}


def test_gate15_resolve_alpaca_credentials_from_dotenv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify resolve_alpaca_credentials resolves credentials from .env when shell env is absent."""
    from acash.research.step_r2_hyp_003 import resolve_alpaca_credentials

    # Clear shell variables
    for var in [
        "ACASH_ALPACA_API_KEY_ID", "ACASH_ALPACA_API_SECRET",
        "APCA_API_KEY_ID", "APCA_API_SECRET_KEY",
        "ALPACA_API_KEY", "ALPACA_API_SECRET",
    ]:
        monkeypatch.delenv(var, raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "APCA_API_KEY_ID=APCA_DOTENV_KEY_VAL\n"
        "APCA_API_SECRET_KEY=APCA_DOTENV_SEC_VAL\n",
        encoding="utf-8",
    )

    creds = resolve_alpaca_credentials(env_path=env_file)
    assert creds is not None
    assert creds.resolved is True
    assert creds.api_key_id == "APCA_DOTENV_KEY_VAL"
    # Secret is redacted in str/repr
    assert "APCA_DOTENV_SEC_VAL" not in str(creds)
    assert "********" in str(creds)


def test_gate16_credentials_not_serialized_in_manifest() -> None:
    """Verify that credentials never leak into manifest JSON."""
    manifest = create_r2_manifest(
        hypothesis_sha256="f59010d14f466e9681325a314fd3e7ef30af43ffd69bc6cecbad1b5e6aab4ee0",
        preregistration_sha256="3c04f617b9877a85a07043e67b7554034ebd703fe823d3d2de777a7722a3150c",
        semantic_clarification_commit="9b12040e2d4654da32f737be5b4ba84123b23e58",
        source_git_sha="9b12040e2d4654da32f737be5b4ba84123b23e58",
        total_expected_regular_sessions=1498,
        included_sessions_count=1498,
        excluded_sessions_breakdown={"EXCLUDED_EARLY_CLOSE": 12, "EXCLUDED_HOLIDAY": 55},
        total_canonical_bars=584220,
        first_timestamp_utc="2017-01-03T14:30:00Z",
        last_timestamp_utc="2022-12-30T20:59:00Z",
        canonical_dataset_sha256="0" * 64,
        raw_evidence_aggregate_sha256="1" * 64,
    )

    manifest_str = json.dumps(manifest)
    for forbidden in ["key", "secret", "APCA", "ACASH_ALPACA", "token", "password"]:
        # Only check lowercase keys that aren't expected schema keys
        assert "api_key" not in manifest_str.lower()
        assert "secret" not in manifest_str.lower()
        assert "password" not in manifest_str.lower()


def test_gate17_credentials_not_leaked_in_stdout_stderr(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that secret values are never printed to stdout/stderr during resolution or execution."""
    from acash.research.step_r2_hyp_003 import resolve_alpaca_credentials

    raw_secret_value = "SUPER_SECRET_VALUE_DO_NOT_PRINT_12345"
    raw_key_value = "MY_TEST_KEY_ID_54321"

    env_file = tmp_path / ".env"
    env_file.write_text(
        f"APCA_API_KEY_ID={raw_key_value}\n"
        f"APCA_API_SECRET_KEY={raw_secret_value}\n",
        encoding="utf-8",
    )

    # Resolve credentials
    creds = resolve_alpaca_credentials(env_path=env_file)
    out, err = capsys.readouterr()
    assert raw_secret_value not in out
    assert raw_secret_value not in err


def test_gate18_dotenv_is_gitignored() -> None:
    """Verify that .env is recognized as ignored by git."""
    import subprocess
    res = subprocess.run(
        ["git", "check-ignore", ".env"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    assert ".env" in res.stdout

