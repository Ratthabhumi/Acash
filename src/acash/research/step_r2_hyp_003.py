"""Phase 14 Step R2: Historical SPY 1-Minute SIP Data Qualification for HYP_003.

Strictly Enforces:
1. IS-Only Temporal Scope: 2017-01-01 through 2022-12-31 ONLY.
2. OOS Hard Boundary: Any query, timestamp, or date >= 2023-01-01 immediately aborts (FAIL-CLOSED).
3. CA-1 Calendar Authority: NyseCa1Calendar governs regular 390-minute sessions vs early close vs holidays.
4. Complete Session Invariant: 390/390 valid 1-minute bars per regular session (09:30 to 15:59 ET).
5. Zero Fabrication: No interpolation, forward-filling, synthetic bars, or coarser resampling.
6. Zero Strategy Logic: No indicators, breakout signals, trades, returns, Sharpe, or PnL calculated.
7. Pure Data Preparation & Qualification: Prepares canonical dataset, audit ledger, and durable manifest.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

import pyarrow as pa
import pyarrow.parquet as pq

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.provenance import (
    calculate_canonical_batch_sha256,
    calculate_raw_source_sha256,
)
from acash.data.qualification.client import AlpacaHistoricalSipClient
from acash.data.qualification.models import (
    HistoricalSipBar,
    MarketDataFeed,
    PriceAdjustment,
)
from acash.data.schema import (
    CANONICAL_ARROW_SCHEMA,
    validate_decimal128_bounds,
)
from acash.execution.alpaca.credentials import (
    AlpacaCredentials,
    EnvAlpacaCredentialProvider,
)
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.schema import HypothesisSpecification

NY_TZ: ZoneInfo = ZoneInfo("America/New_York")

# Exact In-Sample Bounds
IS_START_DATE: date = date(2017, 1, 1)
IS_END_DATE: date = date(2022, 12, 31)
OOS_SEALED_BOUNDARY_DATE: date = date(2023, 1, 1)

# Pinned Cryptographic Lineage Digests
EXPECTED_HYP_003_SHA256: str = "f59010d14f466e9681325a314fd3e7ef30af43ffd69bc6cecbad1b5e6aab4ee0"
EXPECTED_PREREG_SHA256: str = "3c04f617b9877a85a07043e67b7554034ebd703fe823d3d2de777a7722a3150c"
EXPECTED_R1_MANIFEST_SHA256: str = "27952f476cf96f75dc47ca0eb68a4b74d1f8dc6bf2f0848d1a877740cc32b372"

# Session Invariants
REGULAR_SESSION_BAR_COUNT: int = 390
REGULAR_SESSION_OPEN_TIME: time = time(9, 30)
REGULAR_SESSION_LAST_BAR_TIME: time = time(15, 59)


def assert_is_boundary(d: date) -> None:
    """Fail-closed assertion enforcing that a date is strictly within IS (2017-01-01..2022-12-31).

    Any date >= 2023-01-01 immediately aborts to preserve the Out-of-Sample seal.
    """
    if d >= OOS_SEALED_BOUNDARY_DATE:
        raise DataContractError(
            f"OOS HARD BOUNDARY VIOLATION: Date {d.isoformat()} lies within the sealed Out-of-Sample "
            f"window (>= {OOS_SEALED_BOUNDARY_DATE.isoformat()}). Access is strictly prohibited."
        )
    if d < IS_START_DATE:
        raise DataContractError(
            f"PRE-IN-SAMPLE BOUNDARY VIOLATION: Date {d.isoformat()} is prior to authorized IS start "
            f"({IS_START_DATE.isoformat()})."
        )


def validate_r2_preconditions(repo_root: Optional[Path] = None) -> Dict[str, str]:
    """Verify all upstream governance documents, hashes, and lineage before Step R2 execution."""
    root = repo_root or Path(".")

    # 1. Sealed HYP_003
    hyp_path = root / "docs/phase14/hypotheses/HYP_003.json"
    if not hyp_path.exists():
        raise DataContractError(f"Precondition failed: Sealed HYP_003 not found at {hyp_path}")
    with open(hyp_path, "r", encoding="utf-8") as f:
        hyp_data = json.load(f)
    spec = HypothesisSpecification.model_validate(hyp_data)
    computed_hyp_sha = calculate_hypothesis_spec_sha256(spec)
    if computed_hyp_sha != EXPECTED_HYP_003_SHA256:
        raise DataContractError(
            f"Precondition failed: HYP_003 SHA-256 mismatch: {computed_hyp_sha} != {EXPECTED_HYP_003_SHA256}"
        )

    # 2. Frozen Pre-registration
    prereg_path = root / "docs/phase14/mec_0013_price_only_preregistration.md"
    if not prereg_path.exists():
        raise DataContractError(f"Precondition failed: Pre-registration not found at {prereg_path}")
    computed_prereg_sha = hashlib.sha256(prereg_path.read_bytes()).hexdigest()
    if computed_prereg_sha != EXPECTED_PREREG_SHA256:
        raise DataContractError(
            f"Precondition failed: Pre-registration SHA-256 mismatch: {computed_prereg_sha} != {EXPECTED_PREREG_SHA256}"
        )

    # 3. Semantic Conformance Record
    clarification_path = root / "docs/phase14/phase14_r1_semantic_conformance_record_HYP_003.md"
    if not clarification_path.exists():
        raise DataContractError(
            f"Precondition failed: Semantic conformance clarification record not found at {clarification_path}"
        )

    # 4. R1 Manifest
    r1_manifest_path = root / "docs/phase14/manifests/manifest_r1_HYP_003.json"
    if not r1_manifest_path.exists():
        raise DataContractError(f"Precondition failed: R1 manifest not found at {r1_manifest_path}")
    with open(r1_manifest_path, "r", encoding="utf-8") as f:
        r1_man_data = json.load(f)
    manifest_digest = r1_man_data.get("manifest_sha256", "")
    payload_copy = {k: v for k, v in r1_man_data.items() if k != "manifest_sha256"}
    recalculated = hashlib.sha256(
        CanonicalConfigSerializer.to_canonical_json(payload_copy).encode("utf-8")
    ).hexdigest()
    if manifest_digest != EXPECTED_R1_MANIFEST_SHA256 or recalculated != EXPECTED_R1_MANIFEST_SHA256:
        raise DataContractError(
            f"Precondition failed: R1 manifest SHA-256 mismatch: {manifest_digest} (recalc: {recalculated}) != {EXPECTED_R1_MANIFEST_SHA256}"
        )

    return {
        "hypothesis_sha256": computed_hyp_sha,
        "preregistration_sha256": computed_prereg_sha,
        "r1_manifest_sha256": manifest_digest,
        "clarification_record": str(clarification_path),
    }


@dataclass(frozen=True)
class Ca1SessionUniverse:
    """Complete census of calendar days across the In-Sample research window."""
    regular_sessions: Tuple[date, ...]
    early_close_sessions: Tuple[date, ...]
    holiday_sessions: Tuple[Tuple[date, str], ...]
    weekend_days: Tuple[date, ...]
    total_calendar_days: int

    @property
    def total_regular_sessions(self) -> int:
        return len(self.regular_sessions)

    @property
    def total_early_close_sessions(self) -> int:
        return len(self.early_close_sessions)

    @property
    def total_holidays(self) -> int:
        return len(self.holiday_sessions)

    @property
    def total_expected_bars(self) -> int:
        return self.total_regular_sessions * REGULAR_SESSION_BAR_COUNT


def build_ca1_session_universe(
    start_date: date = IS_START_DATE,
    end_date: date = IS_END_DATE,
    calendar: Optional[NyseCa1Calendar] = None,
) -> Ca1SessionUniverse:
    """Enumerate and classify every calendar day in [start_date, end_date] using NyseCa1Calendar."""
    assert_is_boundary(start_date)
    assert_is_boundary(end_date)

    cal = calendar or NyseCa1Calendar()

    reg_list: List[date] = []
    early_list: List[date] = []
    hol_list: List[Tuple[date, str]] = []
    wk_list: List[date] = []

    curr = start_date
    total_days = 0
    while curr <= end_date:
        total_days += 1
        if curr.weekday() >= 5:
            wk_list.append(curr)
        elif cal.is_holiday(curr):
            reason = cal.get_holiday_reason(curr) or "Official NYSE Holiday"
            hol_list.append((curr, reason))
        elif cal.is_early_close(curr):
            early_list.append(curr)
        else:
            reg_list.append(curr)
        curr += timedelta(days=1)

    return Ca1SessionUniverse(
        regular_sessions=tuple(reg_list),
        early_close_sessions=tuple(early_list),
        holiday_sessions=tuple(hol_list),
        weekend_days=tuple(wk_list),
        total_calendar_days=total_days,
    )


@dataclass(frozen=True)
class SessionBarValidationResult:
    """Result of validating 1-minute bars for a single regular trading session."""
    session_date: date
    is_valid: bool
    bar_count: int
    expected_bar_count: int = REGULAR_SESSION_BAR_COUNT
    error_reasons: Tuple[str, ...] = ()


def validate_session_bars(
    session_date: date,
    bars: Sequence[HistoricalSipBar],
) -> SessionBarValidationResult:
    """Validate that a regular session contains exactly 390 valid, monotonic, non-duplicate 1-minute bars."""
    assert_is_boundary(session_date)

    errors: List[str] = []
    n_bars = len(bars)

    if n_bars != REGULAR_SESSION_BAR_COUNT:
        errors.append(
            f"Bar count mismatch for {session_date.isoformat()}: expected {REGULAR_SESSION_BAR_COUNT}, got {n_bars}"
        )

    seen_timestamps: set[datetime] = set()
    prev_ts: Optional[datetime] = None

    for idx, bar in enumerate(bars):
        ts = bar.timestamp_utc
        # Convert to America/New_York local time
        ts_ny = ts.astimezone(NY_TZ)

        # Check date alignment
        if ts_ny.date() != session_date:
            errors.append(
                f"Row {idx}: bar timestamp {ts_ny.isoformat()} does not belong to session {session_date.isoformat()}"
            )

        # Check regular trading hours [09:30, 15:59]
        bar_time = ts_ny.time()
        if bar_time < REGULAR_SESSION_OPEN_TIME or bar_time > REGULAR_SESSION_LAST_BAR_TIME:
            errors.append(f"Row {idx}: bar time {bar_time} outside regular hours [09:30, 15:59]")

        # Monotonicity & duplicates
        if ts in seen_timestamps:
            errors.append(f"Row {idx}: duplicate timestamp {ts.isoformat()}")
        seen_timestamps.add(ts)

        if prev_ts is not None and ts <= prev_ts:
            errors.append(f"Row {idx}: non-monotonic timestamp {ts.isoformat()} preceded by {prev_ts.isoformat()}")
        prev_ts = ts

        # OHLC integrity
        if bar.open <= Decimal("0") or bar.high <= Decimal("0") or bar.low <= Decimal("0") or bar.close <= Decimal("0"):
            errors.append(f"Row {idx}: non-positive price in OHLC")
        if bar.high < bar.low:
            errors.append(f"Row {idx}: high < low ({bar.high} < {bar.low})")
        if bar.high < bar.open or bar.high < bar.close:
            errors.append(f"Row {idx}: high is lower than open or close")
        if bar.low > bar.open or bar.low > bar.close:
            errors.append(f"Row {idx}: low is higher than open or close")
        if bar.volume < Decimal("0"):
            errors.append(f"Row {idx}: negative volume ({bar.volume})")

    return SessionBarValidationResult(
        session_date=session_date,
        is_valid=(len(errors) == 0),
        bar_count=n_bars,
        expected_bar_count=REGULAR_SESSION_BAR_COUNT,
        error_reasons=tuple(errors),
    )


def build_canonical_arrow_table(
    sessions_bars: Mapping[date, Sequence[HistoricalSipBar]],
    source_id: str = "alpaca_sip",
    symbol: str = "SPY",
    timeframe: str = "1Min",
) -> pa.Table:
    """Construct canonical PyArrow Table adhering strictly to CANONICAL_ARROW_SCHEMA.

    Deterministic sorting: session_date ascending, event_start_utc ascending.
    """
    sorted_dates = sorted(sessions_bars.keys())

    source_ids: List[str] = []
    symbols: List[str] = []
    timeframes: List[str] = []
    event_start_utcs: List[datetime] = []
    event_end_utcs: List[datetime] = []
    knowledge_times: List[datetime] = []
    revision_seqs: List[int] = []
    opens: List[Decimal] = []
    highs: List[Decimal] = []
    lows: List[Decimal] = []
    closes: List[Decimal] = []
    volumes: List[Decimal] = []
    quote_volumes: List[Decimal] = []
    trade_counts: List[int] = []

    for d in sorted_dates:
        assert_is_boundary(d)
        bars = sorted(sessions_bars[d], key=lambda b: b.timestamp_utc)
        for bar in bars:
            start_ts = bar.timestamp_utc
            end_ts = start_ts + timedelta(minutes=1)
            source_ids.append(source_id)
            symbols.append(symbol)
            timeframes.append(timeframe)
            event_start_utcs.append(start_ts)
            event_end_utcs.append(end_ts)
            knowledge_times.append(end_ts)
            revision_seqs.append(1)
            opens.append(validate_decimal128_bounds(bar.open, "open"))
            highs.append(validate_decimal128_bounds(bar.high, "high"))
            lows.append(validate_decimal128_bounds(bar.low, "low"))
            closes.append(validate_decimal128_bounds(bar.close, "close"))
            volumes.append(validate_decimal128_bounds(bar.volume, "volume"))
            # If quote_volume not directly provided, use approx close * volume
            quote_vol = bar.close * bar.volume
            quote_volumes.append(validate_decimal128_bounds(quote_vol, "quote_volume"))
            trade_counts.append(bar.trade_count if bar.trade_count is not None else 0)

    pydict = {
        "source_id": pa.array(source_ids, type=pa.string()),
        "symbol": pa.array(symbols, type=pa.string()),
        "timeframe": pa.array(timeframes, type=pa.string()),
        "event_start_utc": pa.array(event_start_utcs, type=pa.timestamp("us", tz="UTC")),
        "event_end_utc": pa.array(event_end_utcs, type=pa.timestamp("us", tz="UTC")),
        "knowledge_time_utc": pa.array(knowledge_times, type=pa.timestamp("us", tz="UTC")),
        "revision_seq": pa.array(revision_seqs, type=pa.int64()),
        "open": pa.array(opens, type=pa.decimal128(38, 18)),
        "high": pa.array(highs, type=pa.decimal128(38, 18)),
        "low": pa.array(lows, type=pa.decimal128(38, 18)),
        "close": pa.array(closes, type=pa.decimal128(38, 18)),
        "volume": pa.array(volumes, type=pa.decimal128(38, 18)),
        "quote_volume": pa.array(quote_volumes, type=pa.decimal128(38, 18)),
        "trade_count": pa.array(trade_counts, type=pa.int64()),
    }

    table = pa.Table.from_pydict(pydict, schema=CANONICAL_ARROW_SCHEMA)
    return table


def load_local_env(env_path: Optional[Path] = None, override: bool = False) -> Dict[str, str]:
    """Safely load key-value pairs from a local .env file into os.environ.

    Precedence & Invariants:
    1. If env_path is None, defaults to Path(".env").
    2. If file does not exist, returns empty dict without error.
    3. If override is False (default), existing variables in os.environ are preserved.
    4. Strips leading/trailing whitespace, ignores comments (# ...), and handles quotes.
    5. Never prints, logs, or serializes loaded values.
    """
    target_path = env_path if env_path is not None else Path(".env")
    if not target_path.is_file():
        return {}

    loaded: Dict[str, str] = {}
    try:
        content = target_path.read_text(encoding="utf-8")
    except Exception:
        return {}

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        if key:
            loaded[key] = val
            if override or key not in os.environ:
                os.environ[key] = val
    return loaded


def resolve_alpaca_credentials(env_path: Optional[Path] = None) -> Optional[AlpacaCredentials]:
    """Safely resolve Alpaca credentials adhering to strict precedence.

    Precedence:
    1. Explicit process environment variables
    2. Local .env file (without overriding process env)
    3. Supported alias pairs:
       - ACASH_ALPACA_API_KEY_ID / ACASH_ALPACA_API_SECRET
       - APCA_API_KEY_ID / APCA_API_SECRET_KEY
       - ALPACA_API_KEY / ALPACA_API_SECRET
    """
    # 1. Load local .env without overriding process environment
    load_local_env(env_path=env_path, override=False)

    # 2. Check candidate alias pairs in priority order
    candidates = [
        ("ACASH_ALPACA_API_KEY_ID", "ACASH_ALPACA_API_SECRET"),
        ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY"),
        ("ALPACA_API_KEY", "ALPACA_API_SECRET"),
    ]
    for key_var, sec_var in candidates:
        k = os.environ.get(key_var, "").strip()
        s = os.environ.get(sec_var, "").strip()
        if k and s:
            provider = EnvAlpacaCredentialProvider(api_key_id=k, api_secret=s)
            return provider.load()
    return None


def create_r2_manifest(
    hypothesis_sha256: str,
    preregistration_sha256: str,
    semantic_clarification_commit: str,
    source_git_sha: str,
    total_expected_regular_sessions: int,
    included_sessions_count: int,
    excluded_sessions_breakdown: Dict[str, int],
    total_canonical_bars: int,
    first_timestamp_utc: str,
    last_timestamp_utc: str,
    canonical_dataset_sha256: str,
    raw_evidence_aggregate_sha256: str,
    status: str = "STEP_R2_HISTORICAL_DATA_QUALIFIED_PASS",
) -> Dict[str, Any]:
    """Assemble durable cryptographic manifest for Step R2."""
    return {
        "manifest_type": "HISTORICAL_DATA_QUALIFICATION_MANIFEST",
        "hypothesis_id": "HYP_003",
        "hypothesis_ordinal": 3,
        "hypothesis_ordinal_alias": "HYP_003",
        "mechanism_id": "MEC-0013",
        "hypothesis_sha256": hypothesis_sha256,
        "preregistration_sha256": preregistration_sha256,
        "semantic_clarification_commit": semantic_clarification_commit,
        "source_git_sha": source_git_sha,
        "data_contract": {
            "symbol": "SPY",
            "timeframe": "1Min",
            "feed": "sip",
            "adjustment": "raw",
            "provider": "Alpaca",
        },
        "temporal_partitions": {
            "in_sample_window_utc": ["2017-01-01T00:00:00Z", "2022-12-31T23:59:59Z"],
            "out_of_sample_state": "SEALED_UNREAD",
            "out_of_sample_boundary": ">= 2023-01-01T00:00:00Z (STRICTLY FORBIDDEN)",
        },
        "calendar_authority": {
            "calendar_name": "NyseCa1Calendar",
            "authority_code": "CA-1",
            "regular_session_expected_minutes": 390,
            "timezone": "America/New_York",
        },
        "session_census": {
            "total_expected_regular_sessions": total_expected_regular_sessions,
            "total_included_sessions": included_sessions_count,
            "total_excluded_sessions": sum(excluded_sessions_breakdown.values()),
            "exclusion_breakdown": excluded_sessions_breakdown,
        },
        "dataset_integrity": {
            "total_canonical_bars": total_canonical_bars,
            "first_timestamp_utc": first_timestamp_utc,
            "last_timestamp_utc": last_timestamp_utc,
            "canonical_dataset_sha256": canonical_dataset_sha256,
            "raw_evidence_aggregate_sha256": raw_evidence_aggregate_sha256,
        },
        "status": status,
        "next_required_step": "STEP_R3_IN_SAMPLE_SEARCH_CENSUS_LOCKED",
        "capital_authority_usd": "0.00",
        "paper_authorized": False,
        "live_authorized": False,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
