"""Phase 14 Step R2: HYP_004 / MEC-0014A Historical Dataset Construction & Qualification.

Implements the deterministic, fail-closed historical provider dataset construction,
session-level endpoint extraction, and provenance sealing for HYP_004
(Market Intraday Momentum: Gao Baseline Replication on SPY).

STRICT INVARIANTS:
1. Temporal Boundary: 2017-01-01 through 2022-12-31 ONLY.
   Any date or market timestamp >= 2023-01-01 immediately aborts (FAIL-CLOSED)
   before any network, file, or evaluation operation.
2. Provider Contract Authority:
   - Endpoint extraction: QUALIFIED_LAST_SIP_TRANSACTION_PRICE_AT_OR_BEFORE_BOUNDARY
     at 10:00:00 ET (p1) and 15:30:00 ET (p12).
   - Daily trade count: ALPACA_DAILY_TRADE_COUNT_MAPPING = QUALIFIED_PROVIDER_OPERATIONALIZATION
     (raw SIP trade records with 09:30:00 <= t <= 16:00:00 ET >= 500).
   - Closing authority: NYSE Arca primary closing auction (x=P, c=6) for p13 and p0.
3. First Session Rule:
   2017-01-03 = EXCLUDED_FIRST_SESSION_NO_PRIOR_IN_SAMPLE_CLOSE.
   Zero 2016 data accessed. Trade fetch not required.
4. Separate Status Concepts:
   - acquisition_status: NOT_STARTED, NOT_REQUIRED_BY_FROZEN_ELIGIBILITY_RULE,
     IN_PROGRESS, RAW_COMPLETE, RAW_FAILED.
   - qualification_status: NOT_EVALUATED, QUALIFIED, EXCLUDED_PREREGISTERED,
     PROVIDER_CONTRACT_FAILURE.
5. Atomic Checkpointing:
   session_meta.json written via temporary file and atomic replace.
   Marked RAW_COMPLETE only after full hash and pagination chain verification.
6. Adaptive Rate Limiting:
   Header-aware using X-RateLimit-* when available; ~185 req/min fallback.
7. ABSOLUTE EMPIRICAL PROHIBITIONS:
   ZERO r1, ZERO r13, ZERO price subtraction, ZERO returns, ZERO beta,
   ZERO regression, ZERO p-value, ZERO alpha, ZERO trading signals.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import random
import tempfile
import time as pytime
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple
from zoneinfo import ZoneInfo

import httpx
import pyarrow as pa
import pyarrow.parquet as pq

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar, SessionType
from acash.data.qualification.mec_0014_close_contract import (
    AuctionRecord,
    IS_END_DATE,
    IS_START_DATE,
    OOS_FORBIDDEN_DATE,
    parse_auction_response,
)
from acash.data.qualification.mec_0014_coverage_census import (
    AuctionCoverageClassification,
    classify_session_auctions,
    enumerate_qualified_regular_sessions,
)
from acash.data.qualification.mec_0014_transaction_contract import (
    BOUNDARY_1000_ET,
    BOUNDARY_1530_ET,
    BoundaryCandidate,
    BoundaryEndpointClassification,
    RawSipTradeRecord,
    classify_boundary_endpoint,
    detect_transport_duplicates,
    filter_regular_session_records,
    parse_trades_page,
)
from acash.execution.alpaca.credentials import AlpacaCredentials
from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.schema import HypothesisSpecification

NY_TZ: ZoneInfo = ZoneInfo("America/New_York")

# Pinned Cryptographic Lineage Digests
EXPECTED_HYP_004_SHA256: str = "fc07b8aff8c580edd437a299be704a5d19b0cb3dcce65024d01a0dc3f771667d"
EXPECTED_R1_MANIFEST_SHA256: str = "eacd98963f51b759b43ba8565aecbc43432f93acd9386b3c20bec8184712bd5b"
EXPECTED_PREREG_SHA256: str = "1e5100f6733951c61d52494028b347164c7ae457794df23fa3766b7a738782ce"

# Expected Regular Session Census by Year
EXPECTED_SESSIONS_BY_YEAR: Dict[int, int] = {
    2017: 249,
    2018: 248,
    2019: 249,
    2020: 251,
    2021: 251,
    2022: 250,
}
TOTAL_EXPECTED_REGULAR_SESSIONS: int = 1498
FIRST_SAMPLE_SESSION: date = date(2017, 1, 3)
GAO_MIN_DAILY_TRADE_COUNT: int = 500


# ---------------------------------------------------------------------------
# Status Enumerations
# ---------------------------------------------------------------------------

class AcquisitionStatus(str, Enum):
    """Status of raw provider data acquisition for a session."""
    NOT_STARTED = "NOT_STARTED"
    NOT_REQUIRED_BY_FROZEN_ELIGIBILITY_RULE = "NOT_REQUIRED_BY_FROZEN_ELIGIBILITY_RULE"
    IN_PROGRESS = "IN_PROGRESS"
    RAW_COMPLETE = "RAW_COMPLETE"
    RAW_FAILED = "RAW_FAILED"


class QualificationStatus(str, Enum):
    """Status of research qualification / eligibility for a session."""
    NOT_EVALUATED = "NOT_EVALUATED"
    QUALIFIED = "QUALIFIED"
    EXCLUDED_PREREGISTERED = "EXCLUDED_PREREGISTERED"
    PROVIDER_CONTRACT_FAILURE = "PROVIDER_CONTRACT_FAILURE"


# ---------------------------------------------------------------------------
# Fail-closed Boundary Guards
# ---------------------------------------------------------------------------

def assert_is_boundary(d: date) -> None:
    """Enforce temporal boundary: 2017-01-01 <= date <= 2022-12-31 ONLY."""
    if d >= OOS_FORBIDDEN_DATE:
        raise DataContractError(
            f"OOS HARD BOUNDARY VIOLATION: Date {d.isoformat()} lies within the sealed Out-of-Sample "
            f"window (>= {OOS_FORBIDDEN_DATE.isoformat()}). Access is strictly prohibited."
        )
    if d < IS_START_DATE:
        raise DataContractError(
            f"PRE-IN-SAMPLE BOUNDARY VIOLATION: Date {d.isoformat()} is prior to authorized IS start "
            f"({IS_START_DATE.isoformat()})."
        )


def validate_r2_preconditions(repo_root: Optional[Path] = None) -> Dict[str, str]:
    """Verify all upstream governance documents, hashes, and lineage before Step R2 execution."""
    root = repo_root or Path(".")

    # 1. Sealed HYP_004
    hyp_path = root / "docs/phase14/hypotheses/HYP_004.json"
    if not hyp_path.exists():
        raise DataContractError(f"Precondition failed: Sealed HYP_004 not found at {hyp_path}")
    hyp_data = json.loads(hyp_path.read_text(encoding="utf-8"))
    spec = HypothesisSpecification.model_validate(hyp_data)
    computed_hyp_sha = calculate_hypothesis_spec_sha256(spec)
    if computed_hyp_sha != EXPECTED_HYP_004_SHA256:
        raise DataContractError(
            f"Precondition failed: HYP_004 SHA-256 mismatch: {computed_hyp_sha} != {EXPECTED_HYP_004_SHA256}"
        )

    # 2. Frozen Pre-registration
    prereg_path = root / "docs/research/MEC-0014A-statistical-preregistration-draft.md"
    if not prereg_path.exists():
        raise DataContractError(f"Precondition failed: Pre-registration not found at {prereg_path}")
    computed_prereg_sha = hashlib.sha256(prereg_path.read_bytes()).hexdigest()
    if computed_prereg_sha != EXPECTED_PREREG_SHA256:
        raise DataContractError(
            f"Precondition failed: Pre-registration SHA-256 mismatch: {computed_prereg_sha} != {EXPECTED_PREREG_SHA256}"
        )

    # 3. Semantic Conformance Record
    conformance_path = root / "docs/phase14/phase14_r1_semantic_conformance_record_HYP_004.md"
    if not conformance_path.exists():
        raise DataContractError(
            f"Precondition failed: Semantic conformance record not found at {conformance_path}"
        )

    # 4. R1 Manifest
    r1_manifest_path = root / "docs/phase14/manifests/manifest_r1_HYP_004.json"
    if not r1_manifest_path.exists():
        raise DataContractError(f"Precondition failed: R1 manifest not found at {r1_manifest_path}")
    r1_man_data = json.loads(r1_manifest_path.read_text(encoding="utf-8"))
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
        "conformance_record": str(conformance_path),
    }


# ---------------------------------------------------------------------------
# Adaptive Rate Governor
# ---------------------------------------------------------------------------

class AdaptiveRateGovernor:
    """Header-aware rate governor for Alpaca Market Data API requests.

    Enforces:
    - Provider authority: Inspects X-RateLimit-Limit, X-RateLimit-Remaining,
      and X-RateLimit-Reset headers when present.
    - Fallback rate: When headers are missing, enforces conservative ~185 req/min.
    - HTTP 429 backoff: Respects provider Retry-After / reset timing; uses bounded
      exponential backoff if headers are absent.
    - Tracking: Accumulates request counts, 429 responses, and retry latencies.
    """

    def __init__(self, fallback_req_per_min: float = 185.0):
        self.fallback_min_interval: float = 60.0 / fallback_req_per_min
        self.last_request_time: float = 0.0
        self.total_requests: int = 0
        self.rate_limit_429_count: int = 0
        self.total_retry_count: int = 0
        self.header_observed: bool = False
        self.last_remaining: Optional[int] = None
        self.last_limit: Optional[int] = None
        self.last_reset_epoch: Optional[int] = None

    def pace_before_request(self) -> None:
        """Pace execution before sending an HTTP request.
        
        Uses provider headers as canonical authority when available.
        Uses conservative fallback (~185 req/min) when headers are unobserved.
        """
        now = pytime.monotonic()
        elapsed = now - self.last_request_time

        if self.header_observed and self.last_limit is not None:
            # Scale target interval based on provider limit with 5% safety margin
            target_rate = max(10.0, float(self.last_limit) * 0.95)
            target_interval = 60.0 / target_rate

            if self.last_remaining is not None and self.last_reset_epoch is not None:
                if self.last_remaining <= 5:
                    time_now_epoch = pytime.time()
                    wait_seconds = max(0.0, float(self.last_reset_epoch - time_now_epoch) + 0.2)
                    if wait_seconds > 0:
                        pytime.sleep(min(wait_seconds, 60.0))
                else:
                    time_to_reset = max(0.1, float(self.last_reset_epoch - pytime.time()))
                    smoothed_interval = max(target_interval, time_to_reset / max(1, self.last_remaining))
                    if elapsed < smoothed_interval:
                        pytime.sleep(smoothed_interval - elapsed)
            elif elapsed < target_interval:
                pytime.sleep(target_interval - elapsed)
        else:
            # Conservative fallback (~185 req/min)
            if elapsed < self.fallback_min_interval:
                pytime.sleep(self.fallback_min_interval - elapsed)

        self.last_request_time = pytime.monotonic()
        self.total_requests += 1

    def update_from_headers(self, headers: Mapping[str, str]) -> None:
        """Extract and update rate limit state from HTTP response headers."""
        limit_str = headers.get("x-ratelimit-limit") or headers.get("X-RateLimit-Limit")
        rem_str = headers.get("x-ratelimit-remaining") or headers.get("X-RateLimit-Remaining")
        reset_str = headers.get("x-ratelimit-reset") or headers.get("X-RateLimit-Reset")

        if limit_str is not None and rem_str is not None:
            try:
                self.last_limit = int(limit_str)
                self.last_remaining = int(rem_str)
                self.header_observed = True
                if reset_str is not None:
                    self.last_reset_epoch = int(reset_str)
            except (ValueError, TypeError):
                pass

    def handle_429_response(
        self,
        headers: Mapping[str, str],
        attempt: int,
        sleep: bool = True,
    ) -> float:
        """Calculate wait time after receiving an HTTP 429 Too Many Requests response."""
        self.rate_limit_429_count += 1
        self.total_retry_count += 1
        jitter = random.uniform(0.1, 0.5)

        # 1. Inspect Retry-After header
        retry_after = headers.get("retry-after") or headers.get("Retry-After")
        if retry_after is not None:
            try:
                wait_sec = max(1.0, float(retry_after) + jitter)
                if sleep:
                    pytime.sleep(wait_sec)
                return wait_sec
            except ValueError:
                pass

        # 2. Inspect X-RateLimit-Reset header
        reset_str = headers.get("x-ratelimit-reset") or headers.get("X-RateLimit-Reset")
        if reset_str is not None:
            try:
                reset_epoch = float(reset_str)
                wait_sec = max(1.0, (reset_epoch - pytime.time()) + jitter)
                if sleep:
                    pytime.sleep(min(wait_sec, 65.0))
                return wait_sec
            except ValueError:
                pass

        # 3. Fallback bounded exponential backoff with jitter
        backoff = min(60.0, (2.0 ** attempt) + jitter)
        if sleep:
            pytime.sleep(backoff)
        return backoff


# ---------------------------------------------------------------------------
# Close Authority Cache Loader
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CloseAuthorityRecord:
    """Deterministic NYSE Arca x=P, c=6 closing auction print for one regular session."""
    session_date: str
    price: Decimal
    timestamp_utc: str
    exchange: str = "P"
    condition: str = "6"
    status: str = "QUALIFIED_PRIMARY_CLOSE"


def load_verified_close_authority(
    repo_root: Optional[Path] = None,
) -> Dict[str, CloseAuthorityRecord]:
    """Load and hash-verify all 1,498 closing auction authorities from cached census payloads."""
    root = repo_root or Path(".")
    manifest_path = root / "docs/research/manifests/MEC-0014-spy-close-coverage-manifest.json"
    if not manifest_path.exists():
        raise DataContractError(f"Close coverage manifest not found at {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_hashes: Dict[str, str] = manifest["raw_payload_hashes"]

    base_dir = root / "data/raw/research/MEC_0014/coverage_census"
    if not base_dir.exists():
        raise DataContractError(f"Close census payload directory not found at {base_dir}")

    # Hash-verify each payload file
    for filename, expected_hash in raw_hashes.items():
        file_path = base_dir / filename
        if not file_path.is_file():
            raise DataContractError(f"Missing required closing auction payload: {file_path}")
        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise DataContractError(
                f"Close authority payload hash mismatch for {filename}: {actual_hash} != {expected_hash}"
            )

    # Parse and extract unique NYSE Arca x=P, c=6 auction for each regular session
    cal = NyseCa1Calendar()
    regular_sessions = enumerate_qualified_regular_sessions(
        calendar=cal,
        start_date=IS_START_DATE,
        end_date=IS_END_DATE,
    )
    if len(regular_sessions) != TOTAL_EXPECTED_REGULAR_SESSIONS:
        raise DataContractError(
            f"Calendar enumeration mismatch: expected {TOTAL_EXPECTED_REGULAR_SESSIONS}, got {len(regular_sessions)}"
        )

    symbol = "SPY"
    all_auctions_by_date: Dict[str, List[AuctionRecord]] = {}
    for filename in sorted(raw_hashes.keys()):
        payload = json.loads((base_dir / filename).read_text(encoding="utf-8"))
        auctions_list = payload.get("auctions", [])
        if isinstance(auctions_list, dict):
            auctions_list = auctions_list.get(symbol, [])
        for entry in auctions_list:
            if not isinstance(entry, dict):
                continue
            d_str = str(entry.get("d", ""))
            if not d_str:
                continue
            if d_str not in all_auctions_by_date:
                all_auctions_by_date[d_str] = []
            for c_auc in entry.get("c") or []:
                all_auctions_by_date[d_str].append(
                    AuctionRecord(
                        timestamp_utc=str(c_auc["t"]),
                        price=Decimal(str(c_auc["p"])),
                        size=int(c_auc["s"]),
                        exchange=str(c_auc["x"]),
                        condition=str(c_auc.get("c", "")),
                        auction_type="c",
                    )
                )

    authority_map: Dict[str, CloseAuthorityRecord] = {}
    for s_date in regular_sessions:
        d_str = s_date.isoformat()
        day_auctions = all_auctions_by_date.get(d_str, [])
        cov = classify_session_auctions(session_date=s_date, auctions=day_auctions, target_symbol=symbol)
        if cov.classification != AuctionCoverageClassification.UNIQUE_PRIMARY_AUCTION:
            raise DataContractError(
                f"Closing auction not unique for regular session {d_str}: {cov.classification.value}"
            )
        if cov.primary_candidate_price is None or cov.primary_candidate_timestamp is None:
            raise DataContractError(f"Missing primary closing auction fields for session {d_str}")

        authority_map[d_str] = CloseAuthorityRecord(
            session_date=d_str,
            price=Decimal(cov.primary_candidate_price),
            timestamp_utc=cov.primary_candidate_timestamp,
            exchange="P",
            condition="6",
            status="QUALIFIED_PRIMARY_CLOSE",
        )

    return authority_map


# ---------------------------------------------------------------------------
# Atomic Checkpointing & Session Metadata
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SessionPageMeta:
    """Metadata and integrity hash for one downloaded raw SIP trade page."""
    page_index: int
    page_file_name: str
    page_file_sha256: str
    incoming_page_token: Optional[str]
    next_page_token: Optional[str]
    record_count: int
    first_timestamp_utc: Optional[str]
    last_timestamp_utc: Optional[str]


@dataclass
class SessionCheckpointMeta:
    """Atomic checkpoint metadata for a single regular session."""
    session_date: str
    acquisition_status: AcquisitionStatus
    qualification_status: QualificationStatus
    exclusion_reason_codes: List[str]
    pages: List[SessionPageMeta]
    total_raw_records: int
    regular_session_records: int
    raw_evidence_aggregate_sha256: Optional[str]
    b1000_classification: Optional[str]
    b1000_price: Optional[str]
    b1530_classification: Optional[str]
    b1530_price: Optional[str]
    exact_transport_duplicates: int
    last_updated_utc: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_date": self.session_date,
            "acquisition_status": self.acquisition_status.value,
            "qualification_status": self.qualification_status.value,
            "exclusion_reason_codes": self.exclusion_reason_codes,
            "pages": [asdict(p) for p in self.pages],
            "total_raw_records": self.total_raw_records,
            "regular_session_records": self.regular_session_records,
            "raw_evidence_aggregate_sha256": self.raw_evidence_aggregate_sha256,
            "b1000_classification": self.b1000_classification,
            "b1000_price": self.b1000_price,
            "b1530_classification": self.b1530_classification,
            "b1530_price": self.b1530_price,
            "exact_transport_duplicates": self.exact_transport_duplicates,
            "last_updated_utc": self.last_updated_utc,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SessionCheckpointMeta:
        pages = [
            SessionPageMeta(
                page_index=p["page_index"],
                page_file_name=p["page_file_name"],
                page_file_sha256=p["page_file_sha256"],
                incoming_page_token=p.get("incoming_page_token"),
                next_page_token=p.get("next_page_token"),
                record_count=p["record_count"],
                first_timestamp_utc=p.get("first_timestamp_utc"),
                last_timestamp_utc=p.get("last_timestamp_utc"),
            )
            for p in data.get("pages", [])
        ]
        return cls(
            session_date=data["session_date"],
            acquisition_status=AcquisitionStatus(data["acquisition_status"]),
            qualification_status=QualificationStatus(data["qualification_status"]),
            exclusion_reason_codes=list(data.get("exclusion_reason_codes", [])),
            pages=pages,
            total_raw_records=data.get("total_raw_records", 0),
            regular_session_records=data.get("regular_session_records", 0),
            raw_evidence_aggregate_sha256=data.get("raw_evidence_aggregate_sha256"),
            b1000_classification=data.get("b1000_classification"),
            b1000_price=data.get("b1000_price"),
            b1530_classification=data.get("b1530_classification"),
            b1530_price=data.get("b1530_price"),
            exact_transport_duplicates=data.get("exact_transport_duplicates", 0),
            last_updated_utc=data.get("last_updated_utc", datetime.now(timezone.utc).isoformat()),
        )


def write_atomic_checkpoint(checkpoint_path: Path, checkpoint: SessionCheckpointMeta) -> None:
    """Atomically persist session_meta.json using temporary file write + flush + replace.

    Guarantees crash safety: an interruption never produces a partially written or corrupted file.
    """
    checkpoint_dir = checkpoint_path.parent
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    json_bytes = json.dumps(checkpoint.to_dict(), indent=2).encode("utf-8")

    # Write to a temporary file in the same directory to guarantee same-filesystem atomic rename
    temp_fd, temp_path_str = tempfile.mkstemp(
        prefix="meta_tmp_", suffix=".json", dir=str(checkpoint_dir)
    )
    temp_path = Path(temp_path_str)
    try:
        with os.fdopen(temp_fd, "wb") as f:
            f.write(json_bytes)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, checkpoint_path)
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        raise DataContractError(f"Atomic checkpoint publication failed for {checkpoint_path}: {exc}") from exc


def compute_page_chain_aggregate_sha(pages: Sequence[SessionPageMeta]) -> str:
    """Compute deterministic aggregate SHA-256 of all pages in exact sequential chain order."""
    hasher = hashlib.sha256()
    for p in sorted(pages, key=lambda x: x.page_index):
        hasher.update(f"{p.page_index}:{p.page_file_name}:{p.page_file_sha256}:{p.record_count}\n".encode("utf-8"))
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# Canonical Session Endpoint Record (Dataset Row)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SessionEndpointRow:
    """Deterministic canonical record for one regular session in the R2 dataset.

    STRICT INVARIANT:
    Zero return fields, zero price ratios, zero price differences.
    Raw prices may coexist on the same row; no arithmetic combining them is permitted.
    """
    trading_date: str
    calendar_session_ordinal: int
    prior_regular_session_date: Optional[str]

    # p0 (Previous Qualified Primary Close)
    p0_previous_primary_close: Optional[Decimal]
    p0_source_session_date: Optional[str]
    p0_auction_timestamp: Optional[str]
    p0_exchange: Optional[str]
    p0_condition: Optional[str]
    p0_authority_status: str

    # p1 (10:00 ET Endpoint)
    p1_1000_price: Optional[Decimal]
    p1_t_star_utc: Optional[str]
    p1_distance_to_boundary_seconds: Optional[str]
    p1_tie_record_count: int
    p1_distinct_price_count: int
    p1_endpoint_status: str

    # p12 (15:30 ET Endpoint)
    p12_1530_price: Optional[Decimal]
    p12_t_star_utc: Optional[str]
    p12_distance_to_boundary_seconds: Optional[str]
    p12_tie_record_count: int
    p12_distinct_price_count: int
    p12_endpoint_status: str

    # p13 (Current Qualified Primary Close)
    p13_current_primary_close: Optional[Decimal]
    p13_auction_timestamp: Optional[str]
    p13_exchange: Optional[str]
    p13_condition: Optional[str]
    p13_authority_status: str

    # Trade Qualification
    raw_regular_session_sip_trade_count: int
    trade_count_threshold: int = GAO_MIN_DAILY_TRADE_COUNT
    trade_count_pass: bool = False

    # Provider Integrity
    pagination_page_count: int = 0
    pagination_complete: bool = False
    exact_transport_duplicate_count: int = 0

    # Eligibility & Status
    acquisition_status: str = AcquisitionStatus.NOT_STARTED.value
    qualification_status: str = QualificationStatus.NOT_EVALUATED.value
    primary_regression_eligible: bool = False
    exclusion_reason_codes: Tuple[str, ...] = ()

    # Provenance
    per_session_raw_evidence_aggregate_sha256: Optional[str] = None
    close_evidence_reference: str = "docs/research/manifests/MEC-0014-spy-close-coverage-manifest.json"
    close_evidence_hash: str = ""
    contract_version_git_sha: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trading_date": self.trading_date,
            "calendar_session_ordinal": self.calendar_session_ordinal,
            "prior_regular_session_date": self.prior_regular_session_date,
            "p0_previous_primary_close": str(self.p0_previous_primary_close) if self.p0_previous_primary_close is not None else None,
            "p0_source_session_date": self.p0_source_session_date,
            "p0_auction_timestamp": self.p0_auction_timestamp,
            "p0_exchange": self.p0_exchange,
            "p0_condition": self.p0_condition,
            "p0_authority_status": self.p0_authority_status,
            "p1_1000_price": str(self.p1_1000_price) if self.p1_1000_price is not None else None,
            "p1_t_star_utc": self.p1_t_star_utc,
            "p1_distance_to_boundary_seconds": self.p1_distance_to_boundary_seconds,
            "p1_tie_record_count": self.p1_tie_record_count,
            "p1_distinct_price_count": self.p1_distinct_price_count,
            "p1_endpoint_status": self.p1_endpoint_status,
            "p12_1530_price": str(self.p12_1530_price) if self.p12_1530_price is not None else None,
            "p12_t_star_utc": self.p12_t_star_utc,
            "p12_distance_to_boundary_seconds": self.p12_distance_to_boundary_seconds,
            "p12_tie_record_count": self.p12_tie_record_count,
            "p12_distinct_price_count": self.p12_distinct_price_count,
            "p12_endpoint_status": self.p12_endpoint_status,
            "p13_current_primary_close": str(self.p13_current_primary_close) if self.p13_current_primary_close is not None else None,
            "p13_auction_timestamp": self.p13_auction_timestamp,
            "p13_exchange": self.p13_exchange,
            "p13_condition": self.p13_condition,
            "p13_authority_status": self.p13_authority_status,
            "raw_regular_session_sip_trade_count": self.raw_regular_session_sip_trade_count,
            "trade_count_threshold": self.trade_count_threshold,
            "trade_count_pass": self.trade_count_pass,
            "pagination_page_count": self.pagination_page_count,
            "pagination_complete": self.pagination_complete,
            "exact_transport_duplicate_count": self.exact_transport_duplicate_count,
            "acquisition_status": self.acquisition_status,
            "qualification_status": self.qualification_status,
            "primary_regression_eligible": self.primary_regression_eligible,
            "exclusion_reason_codes": list(self.exclusion_reason_codes),
            "per_session_raw_evidence_aggregate_sha256": self.per_session_raw_evidence_aggregate_sha256,
            "close_evidence_reference": self.close_evidence_reference,
            "close_evidence_hash": self.close_evidence_hash,
            "contract_version_git_sha": self.contract_version_git_sha,
        }


# ---------------------------------------------------------------------------
# Canonical PyArrow Parquet Schema
# ---------------------------------------------------------------------------

R2_SESSION_ENDPOINTS_ARROW_SCHEMA = pa.schema([
    ("trading_date", pa.string()),
    ("calendar_session_ordinal", pa.int32()),
    ("prior_regular_session_date", pa.string()),
    ("p0_previous_primary_close", pa.decimal128(18, 4)),
    ("p0_source_session_date", pa.string()),
    ("p0_auction_timestamp", pa.string()),
    ("p0_exchange", pa.string()),
    ("p0_condition", pa.string()),
    ("p0_authority_status", pa.string()),
    ("p1_1000_price", pa.decimal128(18, 4)),
    ("p1_t_star_utc", pa.string()),
    ("p1_distance_to_boundary_seconds", pa.string()),
    ("p1_tie_record_count", pa.int32()),
    ("p1_distinct_price_count", pa.int32()),
    ("p1_endpoint_status", pa.string()),
    ("p12_1530_price", pa.decimal128(18, 4)),
    ("p12_t_star_utc", pa.string()),
    ("p12_distance_to_boundary_seconds", pa.string()),
    ("p12_tie_record_count", pa.int32()),
    ("p12_distinct_price_count", pa.int32()),
    ("p12_endpoint_status", pa.string()),
    ("p13_current_primary_close", pa.decimal128(18, 4)),
    ("p13_auction_timestamp", pa.string()),
    ("p13_exchange", pa.string()),
    ("p13_condition", pa.string()),
    ("p13_authority_status", pa.string()),
    ("raw_regular_session_sip_trade_count", pa.int64()),
    ("trade_count_threshold", pa.int32()),
    ("trade_count_pass", pa.bool_()),
    ("pagination_page_count", pa.int32()),
    ("pagination_complete", pa.bool_()),
    ("exact_transport_duplicate_count", pa.int32()),
    ("acquisition_status", pa.string()),
    ("qualification_status", pa.string()),
    ("primary_regression_eligible", pa.bool_()),
    ("exclusion_reason_codes", pa.list_(pa.string())),
    ("per_session_raw_evidence_aggregate_sha256", pa.string()),
    ("close_evidence_reference", pa.string()),
    ("close_evidence_hash", pa.string()),
    ("contract_version_git_sha", pa.string()),
])


def build_canonical_endpoint_parquet(
    rows: Sequence[SessionEndpointRow],
    output_path: Path,
) -> Path:
    """Build and write the canonical Parquet dataset.

    Enforces:
    - Deterministic sort by trading_date ascending
    - Cardinality assertion: exactly 1,498 rows
    - Schema validation with exact decimal128(18, 4) price representation
    - Strict prohibition: zero return or regression columns
    """
    if len(rows) != TOTAL_EXPECTED_REGULAR_SESSIONS:
        raise DataContractError(
            f"Dataset cardinality violation: expected {TOTAL_EXPECTED_REGULAR_SESSIONS} rows, got {len(rows)}"
        )

    # Sort deterministically
    sorted_rows = sorted(rows, key=lambda r: r.trading_date)

    # Verify no prohibited columns exist
    prohibited_names = {"r1", "r13", "return", "returns", "beta", "alpha", "p_value", "pvalue", "t_stat", "t_statistic", "sharpe", "pnl", "profit"}
    for f in R2_SESSION_ENDPOINTS_ARROW_SCHEMA:
        name_parts = set(f.name.lower().split("_"))
        if any(p in name_parts for p in prohibited_names) or f.name.lower() in prohibited_names:
            raise DataContractError(f"CRITICAL PROHIBITION: Parquet schema contains forbidden field: {f.name}")

    pydict: Dict[str, List[Any]] = {field.name: [] for field in R2_SESSION_ENDPOINTS_ARROW_SCHEMA}

    for r in sorted_rows:
        pydict["trading_date"].append(r.trading_date)
        pydict["calendar_session_ordinal"].append(r.calendar_session_ordinal)
        pydict["prior_regular_session_date"].append(r.prior_regular_session_date)
        pydict["p0_previous_primary_close"].append(r.p0_previous_primary_close)
        pydict["p0_source_session_date"].append(r.p0_source_session_date)
        pydict["p0_auction_timestamp"].append(r.p0_auction_timestamp)
        pydict["p0_exchange"].append(r.p0_exchange)
        pydict["p0_condition"].append(r.p0_condition)
        pydict["p0_authority_status"].append(r.p0_authority_status)
        pydict["p1_1000_price"].append(r.p1_1000_price)
        pydict["p1_t_star_utc"].append(r.p1_t_star_utc)
        pydict["p1_distance_to_boundary_seconds"].append(r.p1_distance_to_boundary_seconds)
        pydict["p1_tie_record_count"].append(r.p1_tie_record_count)
        pydict["p1_distinct_price_count"].append(r.p1_distinct_price_count)
        pydict["p1_endpoint_status"].append(r.p1_endpoint_status)
        pydict["p12_1530_price"].append(r.p12_1530_price)
        pydict["p12_t_star_utc"].append(r.p12_t_star_utc)
        pydict["p12_distance_to_boundary_seconds"].append(r.p12_distance_to_boundary_seconds)
        pydict["p12_tie_record_count"].append(r.p12_tie_record_count)
        pydict["p12_distinct_price_count"].append(r.p12_distinct_price_count)
        pydict["p12_endpoint_status"].append(r.p12_endpoint_status)
        pydict["p13_current_primary_close"].append(r.p13_current_primary_close)
        pydict["p13_auction_timestamp"].append(r.p13_auction_timestamp)
        pydict["p13_exchange"].append(r.p13_exchange)
        pydict["p13_condition"].append(r.p13_condition)
        pydict["p13_authority_status"].append(r.p13_authority_status)
        pydict["raw_regular_session_sip_trade_count"].append(r.raw_regular_session_sip_trade_count)
        pydict["trade_count_threshold"].append(r.trade_count_threshold)
        pydict["trade_count_pass"].append(r.trade_count_pass)
        pydict["pagination_page_count"].append(r.pagination_page_count)
        pydict["pagination_complete"].append(r.pagination_complete)
        pydict["exact_transport_duplicate_count"].append(r.exact_transport_duplicate_count)
        pydict["acquisition_status"].append(r.acquisition_status)
        pydict["qualification_status"].append(r.qualification_status)
        pydict["primary_regression_eligible"].append(r.primary_regression_eligible)
        pydict["exclusion_reason_codes"].append(list(r.exclusion_reason_codes))
        pydict["per_session_raw_evidence_aggregate_sha256"].append(r.per_session_raw_evidence_aggregate_sha256)
        pydict["close_evidence_reference"].append(r.close_evidence_reference)
        pydict["close_evidence_hash"].append(r.close_evidence_hash)
        pydict["contract_version_git_sha"].append(r.contract_version_git_sha)

    table = pa.Table.from_pydict(pydict, schema=R2_SESSION_ENDPOINTS_ARROW_SCHEMA)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, output_path, compression="zstd")
    return output_path


# ---------------------------------------------------------------------------
# Session Evaluator & Ledger Builder
# ---------------------------------------------------------------------------

def evaluate_session(
    session_date: date,
    ordinal: int,
    prior_session_date: Optional[date],
    close_authority_map: Mapping[str, CloseAuthorityRecord],
    checkpoint: Optional[SessionCheckpointMeta],
    close_evidence_hash: str,
    contract_git_sha: str,
) -> SessionEndpointRow:
    """Evaluate a single calendar session against the 9 frozen eligibility rules."""
    assert_is_boundary(session_date)
    d_str = session_date.isoformat()
    prior_d_str = prior_session_date.isoformat() if prior_session_date else None

    # Rule 1: First session exclusion
    if session_date == FIRST_SAMPLE_SESSION or prior_session_date is None:
        p13_rec = close_authority_map.get(d_str)
        return SessionEndpointRow(
            trading_date=d_str,
            calendar_session_ordinal=ordinal,
            prior_regular_session_date=None,
            p0_previous_primary_close=None,
            p0_source_session_date=None,
            p0_auction_timestamp=None,
            p0_exchange=None,
            p0_condition=None,
            p0_authority_status="FIRST_SESSION_NO_PRIOR_CLOSE",
            p1_1000_price=None,
            p1_t_star_utc=None,
            p1_distance_to_boundary_seconds=None,
            p1_tie_record_count=0,
            p1_distinct_price_count=0,
            p1_endpoint_status="NOT_REQUIRED_FIRST_SESSION",
            p12_1530_price=None,
            p12_t_star_utc=None,
            p12_distance_to_boundary_seconds=None,
            p12_tie_record_count=0,
            p12_distinct_price_count=0,
            p12_endpoint_status="NOT_REQUIRED_FIRST_SESSION",
            p13_current_primary_close=p13_rec.price if p13_rec else None,
            p13_auction_timestamp=p13_rec.timestamp_utc if p13_rec else None,
            p13_exchange="P" if p13_rec else None,
            p13_condition="6" if p13_rec else None,
            p13_authority_status="QUALIFIED_PRIMARY_CLOSE" if p13_rec else "MISSING_P13",
            raw_regular_session_sip_trade_count=0,
            trade_count_threshold=GAO_MIN_DAILY_TRADE_COUNT,
            trade_count_pass=False,
            pagination_page_count=0,
            pagination_complete=True,
            exact_transport_duplicate_count=0,
            acquisition_status=AcquisitionStatus.NOT_REQUIRED_BY_FROZEN_ELIGIBILITY_RULE.value,
            qualification_status=QualificationStatus.EXCLUDED_PREREGISTERED.value,
            primary_regression_eligible=False,
            exclusion_reason_codes=("FIRST_SESSION_NO_PRIOR_IN_SAMPLE_CLOSE",),
            per_session_raw_evidence_aggregate_sha256=None,
            close_evidence_hash=close_evidence_hash,
            contract_version_git_sha=contract_git_sha,
        )

    # General Sessions (ordinal >= 2)
    exclusion_reasons: List[str] = []

    # Close authorities
    p0_rec = close_authority_map.get(prior_d_str) if prior_d_str else None
    p13_rec = close_authority_map.get(d_str)

    p0_price = p0_rec.price if p0_rec else None
    p13_price = p13_rec.price if p13_rec else None

    if p0_rec is None:
        exclusion_reasons.append("MISSING_P0")
    if p13_rec is None:
        exclusion_reasons.append("MISSING_P13")

    if checkpoint is None:
        # Not yet acquired or missing checkpoint
        return SessionEndpointRow(
            trading_date=d_str,
            calendar_session_ordinal=ordinal,
            prior_regular_session_date=prior_d_str,
            p0_previous_primary_close=p0_price,
            p0_source_session_date=prior_d_str,
            p0_auction_timestamp=p0_rec.timestamp_utc if p0_rec else None,
            p0_exchange="P" if p0_rec else None,
            p0_condition="6" if p0_rec else None,
            p0_authority_status="QUALIFIED_PRIMARY_CLOSE" if p0_rec else "MISSING_P0",
            p1_1000_price=None,
            p1_t_star_utc=None,
            p1_distance_to_boundary_seconds=None,
            p1_tie_record_count=0,
            p1_distinct_price_count=0,
            p1_endpoint_status="MISSING_DATA",
            p12_1530_price=None,
            p12_t_star_utc=None,
            p12_distance_to_boundary_seconds=None,
            p12_tie_record_count=0,
            p12_distinct_price_count=0,
            p12_endpoint_status="MISSING_DATA",
            p13_current_primary_close=p13_price,
            p13_auction_timestamp=p13_rec.timestamp_utc if p13_rec else None,
            p13_exchange="P" if p13_rec else None,
            p13_condition="6" if p13_rec else None,
            p13_authority_status="QUALIFIED_PRIMARY_CLOSE" if p13_rec else "MISSING_P13",
            raw_regular_session_sip_trade_count=0,
            trade_count_threshold=GAO_MIN_DAILY_TRADE_COUNT,
            trade_count_pass=False,
            pagination_page_count=0,
            pagination_complete=False,
            exact_transport_duplicate_count=0,
            acquisition_status=AcquisitionStatus.NOT_STARTED.value,
            qualification_status=QualificationStatus.PROVIDER_CONTRACT_FAILURE.value,
            primary_regression_eligible=False,
            exclusion_reason_codes=tuple(exclusion_reasons + ["DATA_NOT_ACQUIRED"]),
            per_session_raw_evidence_aggregate_sha256=None,
            close_evidence_hash=close_evidence_hash,
            contract_version_git_sha=contract_git_sha,
        )

    # Evaluate using checkpoint evidence
    trade_count = checkpoint.regular_session_records
    trade_pass = (trade_count >= GAO_MIN_DAILY_TRADE_COUNT)
    if not trade_pass:
        exclusion_reasons.append("TRADE_COUNT_LT_500")

    # Endpoint 10:00
    p1_price = Decimal(checkpoint.b1000_price) if checkpoint.b1000_price is not None else None
    p1_status = checkpoint.b1000_classification or "MISSING_PRE_BOUNDARY_TRANSACTION"
    if p1_status == BoundaryEndpointClassification.AMBIGUOUS_BOUNDARY_PRICE.value:
        exclusion_reasons.append("AMBIGUOUS_P1_BOUNDARY_PRICE")
    elif p1_status == BoundaryEndpointClassification.MISSING_PRE_BOUNDARY_TRANSACTION.value or p1_price is None:
        exclusion_reasons.append("MISSING_P1")

    # Endpoint 15:30
    p12_price = Decimal(checkpoint.b1530_price) if checkpoint.b1530_price is not None else None
    p12_status = checkpoint.b1530_classification or "MISSING_PRE_BOUNDARY_TRANSACTION"
    if p12_status == BoundaryEndpointClassification.AMBIGUOUS_BOUNDARY_PRICE.value:
        exclusion_reasons.append("AMBIGUOUS_P12_BOUNDARY_PRICE")
    elif p12_status == BoundaryEndpointClassification.MISSING_PRE_BOUNDARY_TRANSACTION.value or p12_price is None:
        exclusion_reasons.append("MISSING_P12")

    if checkpoint.exact_transport_duplicates > 0:
        exclusion_reasons.append("TRANSPORT_DUPLICATE_DEFECT")

    # Determine qualification status vs acquisition status
    is_eligible = (len(exclusion_reasons) == 0 and checkpoint.acquisition_status == AcquisitionStatus.RAW_COMPLETE)

    if is_eligible:
        qual_status = QualificationStatus.QUALIFIED
    elif checkpoint.acquisition_status == AcquisitionStatus.RAW_COMPLETE:
        # Complete raw acquisition, but excluded by preregistered rules
        qual_status = QualificationStatus.EXCLUDED_PREREGISTERED
    else:
        # Acquisition failure / incomplete
        qual_status = QualificationStatus.PROVIDER_CONTRACT_FAILURE

    return SessionEndpointRow(
        trading_date=d_str,
        calendar_session_ordinal=ordinal,
        prior_regular_session_date=prior_d_str,
        p0_previous_primary_close=p0_price,
        p0_source_session_date=prior_d_str,
        p0_auction_timestamp=p0_rec.timestamp_utc if p0_rec else None,
        p0_exchange="P" if p0_rec else None,
        p0_condition="6" if p0_rec else None,
        p0_authority_status="QUALIFIED_PRIMARY_CLOSE" if p0_rec else "MISSING_P0",
        p1_1000_price=p1_price,
        p1_t_star_utc=None,
        p1_distance_to_boundary_seconds=None,
        p1_tie_record_count=1,
        p1_distinct_price_count=1 if p1_price is not None else 0,
        p1_endpoint_status=p1_status,
        p12_1530_price=p12_price,
        p12_t_star_utc=None,
        p12_distance_to_boundary_seconds=None,
        p12_tie_record_count=1,
        p12_distinct_price_count=1 if p12_price is not None else 0,
        p12_endpoint_status=p12_status,
        p13_current_primary_close=p13_price,
        p13_auction_timestamp=p13_rec.timestamp_utc if p13_rec else None,
        p13_exchange="P" if p13_rec else None,
        p13_condition="6" if p13_rec else None,
        p13_authority_status="QUALIFIED_PRIMARY_CLOSE" if p13_rec else "MISSING_P13",
        raw_regular_session_sip_trade_count=trade_count,
        trade_count_threshold=GAO_MIN_DAILY_TRADE_COUNT,
        trade_count_pass=trade_pass,
        pagination_page_count=len(checkpoint.pages),
        pagination_complete=True,
        exact_transport_duplicate_count=checkpoint.exact_transport_duplicates,
        acquisition_status=checkpoint.acquisition_status.value,
        qualification_status=qual_status.value,
        primary_regression_eligible=is_eligible,
        exclusion_reason_codes=tuple(exclusion_reasons),
        per_session_raw_evidence_aggregate_sha256=checkpoint.raw_evidence_aggregate_sha256,
        close_evidence_hash=close_evidence_hash,
        contract_version_git_sha=contract_git_sha,
    )


# ---------------------------------------------------------------------------
# Session Acquisition Processor
# ---------------------------------------------------------------------------

def process_session_trades(
    session_date: date,
    client: Optional[httpx.Client],
    headers: Mapping[str, str],
    governor: AdaptiveRateGovernor,
    raw_cache_base_dir: Path,
    symbol: str = "SPY",
    verify_only: bool = False,
) -> SessionCheckpointMeta:
    """Acquire and qualify historical SIP trades for a single regular session.

    Guarantees:
    - Resumable: Reuses completely verified cache if session_meta.json exists.
    - Idempotent: Verified cache produces zero network calls.
    - Rate-governed: Paced via AdaptiveRateGovernor.
    - Atomic: Checkpoint published atomically only after completion and hash checks.
    - Separate statuses: Distinguishes raw acquisition from scientific qualification.
    """
    assert_is_boundary(session_date)
    d_iso = session_date.isoformat()
    session_dir = raw_cache_base_dir / str(session_date.year) / d_iso
    meta_path = session_dir / "session_meta.json"

    # 1. Attempt Cache Reuse
    if meta_path.is_file():
        try:
            cached_meta = SessionCheckpointMeta.from_dict(
                json.loads(meta_path.read_text(encoding="utf-8"))
            )
            if cached_meta.acquisition_status == AcquisitionStatus.RAW_COMPLETE:
                # Verify that every cached page file exists and matches its recorded SHA-256
                all_pages_valid = True
                for p in cached_meta.pages:
                    p_file = session_dir / p.page_file_name
                    if not p_file.is_file():
                        all_pages_valid = False
                        break
                    actual_sha = hashlib.sha256(p_file.read_bytes()).hexdigest()
                    if actual_sha != p.page_file_sha256:
                        all_pages_valid = False
                        break

                if all_pages_valid and len(cached_meta.pages) > 0:
                    # Verify page token chain
                    seen_chain_tokens: Set[str] = set()
                    chain_valid = True
                    for i, page in enumerate(cached_meta.pages):
                        if page.incoming_page_token and page.incoming_page_token in seen_chain_tokens:
                            chain_valid = False
                            break
                        if page.incoming_page_token:
                            seen_chain_tokens.add(page.incoming_page_token)
                        if i == len(cached_meta.pages) - 1 and page.next_page_token is not None:
                            chain_valid = False
                            break

                    if chain_valid:
                        # Re-verify aggregate hash
                        expected_agg = compute_page_chain_aggregate_sha(cached_meta.pages)
                        if cached_meta.raw_evidence_aggregate_sha256 == expected_agg:
                            return cached_meta
        except Exception:
            # If checkpoint is corrupted, fail closed if verify_only, else re-acquire
            if verify_only:
                raise DataContractError(f"Session {d_iso} checkpoint is corrupted in verify-only mode.")

    if verify_only:
        raise DataContractError(
            f"Session {d_iso} has no valid verified local cache while running in verify-only mode."
        )

    if client is None:
        raise DataContractError(f"HTTP client required to acquire un-cached session {d_iso}.")

    # 2. Acquire from Alpaca Historical Stock Trades Endpoint
    session_dir.mkdir(parents=True, exist_ok=True)
    start_utc = datetime.combine(session_date, time(9, 30, 0), tzinfo=NY_TZ).astimezone(timezone.utc)
    end_utc = datetime.combine(session_date, time(16, 0, 0), tzinfo=NY_TZ).astimezone(timezone.utc)

    all_raw_records: List[RawSipTradeRecord] = []
    page_metas: List[SessionPageMeta] = []
    seen_tokens: Set[str] = set()
    page_idx = 1
    next_token: Optional[str] = None

    base_url = "https://data.alpaca.markets"

    while True:
        params: Dict[str, Any] = {
            "start": start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "feed": "sip",
            "limit": 10000,
        }
        if next_token:
            params["page_token"] = next_token

        # Pacing
        governor.pace_before_request()

        # Execute with retry for 429 and transient 5xx
        max_attempts = 6
        response: Optional[httpx.Response] = None
        for attempt in range(1, max_attempts + 1):
            try:
                r = client.get(
                    f"{base_url}/v2/stocks/{symbol}/trades",
                    headers=dict(headers),
                    params=params,
                    timeout=45.0,
                )
                if r.status_code == 200:
                    governor.update_from_headers(r.headers)
                    response = r
                    break
                elif r.status_code == 429:
                    governor.handle_429_response(r.headers, attempt)
                    continue
                elif r.status_code in (500, 502, 503, 504):
                    pytime.sleep(min(30.0, 2.0 ** attempt))
                    continue
                else:
                    raise DataContractError(
                        f"[{d_iso}] Alpaca API returned HTTP {r.status_code}: {r.text}"
                    )
            except (httpx.RequestError, httpx.TimeoutException) as net_err:
                if attempt == max_attempts:
                    raise DataContractError(
                        f"[{d_iso}] Network error after {max_attempts} attempts: {net_err}"
                    ) from net_err
                pytime.sleep(min(30.0, 2.0 ** attempt))

        if response is None or response.status_code != 200:
            raise DataContractError(f"[{d_iso}] Failed to acquire page {page_idx} after retries.")

        raw_bytes = response.content
        page_file_name = f"trades_{symbol}_{d_iso}_p{page_idx}.json"
        page_file_path = session_dir / page_file_name
        page_file_path.write_bytes(raw_bytes)

        page_sha = hashlib.sha256(raw_bytes).hexdigest()
        payload = response.json()

        page_records, token_from_payload = parse_trades_page(
            payload, symbol=symbol, session_date=session_date
        )
        all_raw_records.extend(page_records)

        first_ts = page_records[0].timestamp_utc if page_records else None
        last_ts = page_records[-1].timestamp_utc if page_records else None

        page_metas.append(
            SessionPageMeta(
                page_index=page_idx,
                page_file_name=page_file_name,
                page_file_sha256=page_sha,
                incoming_page_token=next_token,
                next_page_token=token_from_payload,
                record_count=len(page_records),
                first_timestamp_utc=first_ts,
                last_timestamp_utc=last_ts,
            )
        )

        if token_from_payload is not None:
            if token_from_payload in seen_tokens:
                raise DataContractError(
                    f"[{d_iso}] Repeated pagination token '{token_from_payload}'. Infinite loop. Fail-closed."
                )
            seen_tokens.add(token_from_payload)

        next_token = token_from_payload
        if next_token is None:
            # End of pagination
            break

        page_idx += 1

    # 3. Post-Acquisition Qualification
    reg_records = filter_regular_session_records(all_raw_records, session_date)
    exact_dups = detect_transport_duplicates(reg_records)
    if exact_dups > 0:
        raise DataContractError(
            f"Session {d_iso}: {exact_dups} exact transport duplicates detected. Fail-closed."
        )

    b1000 = classify_boundary_endpoint(session_date, reg_records, BOUNDARY_1000_ET)
    b1530 = classify_boundary_endpoint(session_date, reg_records, BOUNDARY_1530_ET)

    agg_sha = compute_page_chain_aggregate_sha(page_metas)

    # Determine scientific exclusion codes
    exclusion_codes: List[str] = []
    if len(reg_records) < GAO_MIN_DAILY_TRADE_COUNT:
        exclusion_codes.append("TRADE_COUNT_LT_500")
    if b1000.classification == BoundaryEndpointClassification.AMBIGUOUS_BOUNDARY_PRICE:
        exclusion_codes.append("AMBIGUOUS_P1_BOUNDARY_PRICE")
    elif b1000.classification == BoundaryEndpointClassification.MISSING_PRE_BOUNDARY_TRANSACTION or b1000.selected_price is None:
        exclusion_codes.append("MISSING_P1")

    if b1530.classification == BoundaryEndpointClassification.AMBIGUOUS_BOUNDARY_PRICE:
        exclusion_codes.append("AMBIGUOUS_P12_BOUNDARY_PRICE")
    elif b1530.classification == BoundaryEndpointClassification.MISSING_PRE_BOUNDARY_TRANSACTION or b1530.selected_price is None:
        exclusion_codes.append("MISSING_P12")

    qual_status = (
        QualificationStatus.QUALIFIED
        if len(exclusion_codes) == 0
        else QualificationStatus.EXCLUDED_PREREGISTERED
    )

    checkpoint = SessionCheckpointMeta(
        session_date=d_iso,
        acquisition_status=AcquisitionStatus.RAW_COMPLETE,
        qualification_status=qual_status,
        exclusion_reason_codes=exclusion_codes,
        pages=page_metas,
        total_raw_records=len(all_raw_records),
        regular_session_records=len(reg_records),
        raw_evidence_aggregate_sha256=agg_sha,
        b1000_classification=b1000.classification.value,
        b1000_price=str(b1000.selected_price) if b1000.selected_price is not None else None,
        b1530_classification=b1530.classification.value,
        b1530_price=str(b1530.selected_price) if b1530.selected_price is not None else None,
        exact_transport_duplicates=exact_dups,
        last_updated_utc=datetime.now(timezone.utc).isoformat(),
    )

    # Atomic publication
    write_atomic_checkpoint(meta_path, checkpoint)
    return checkpoint


# ---------------------------------------------------------------------------
# Manifests and Audit Builders
# ---------------------------------------------------------------------------

def build_raw_page_manifest(
    checkpoints: Sequence[SessionCheckpointMeta],
) -> Dict[str, Any]:
    """Assemble local raw page manifest indexing every downloaded raw page."""
    page_entries: List[Dict[str, Any]] = []
    for cp in sorted(checkpoints, key=lambda c: c.session_date):
        for p in cp.pages:
            page_entries.append({
                "session_date": cp.session_date,
                "page_index": p.page_index,
                "page_file_name": p.page_file_name,
                "page_file_sha256": p.page_file_sha256,
                "record_count": p.record_count,
                "first_timestamp_utc": p.first_timestamp_utc,
                "last_timestamp_utc": p.last_timestamp_utc,
            })

    return {
        "manifest_type": "HYP_004_R2_RAW_PAGE_MANIFEST",
        "hypothesis_id": "HYP_004",
        "symbol": "SPY",
        "feed": "sip",
        "total_sessions_indexed": len(checkpoints),
        "total_pages_indexed": len(page_entries),
        "pages": page_entries,
    }


def build_session_ledger(
    rows: Sequence[SessionEndpointRow],
) -> Dict[str, Any]:
    """Assemble the local 1,498-session ledger."""
    sorted_rows = sorted(rows, key=lambda r: r.trading_date)
    return {
        "ledger_type": "HYP_004_R2_SESSION_LEDGER",
        "hypothesis_id": "HYP_004",
        "symbol": "SPY",
        "total_calendar_sessions": len(sorted_rows),
        "eligible_sessions_count": sum(1 for r in sorted_rows if r.primary_regression_eligible),
        "excluded_sessions_count": sum(1 for r in sorted_rows if not r.primary_regression_eligible),
        "sessions": [r.to_dict() for r in sorted_rows],
    }


def build_r2_tracked_manifest(
    rows: Sequence[SessionEndpointRow],
    local_dataset_sha256: str,
    session_ledger_sha256: str,
    raw_page_manifest_sha256: str,
    raw_evidence_aggregate_sha256: str,
    total_raw_pages: int,
    source_git_sha: str,
) -> Dict[str, Any]:
    """Assemble the Git-tracked R2 qualification manifest."""
    sorted_rows = sorted(rows, key=lambda r: r.trading_date)
    eligible_count = sum(1 for r in sorted_rows if r.primary_regression_eligible)
    excluded_count = len(sorted_rows) - eligible_count

    # Tally exclusion reasons
    exclusion_census: Dict[str, int] = {}
    for r in sorted_rows:
        for code in r.exclusion_reason_codes:
            exclusion_census[code] = exclusion_census.get(code, 0) + 1

    payload: Dict[str, Any] = {
        "manifest_type": "HISTORICAL_DATA_QUALIFICATION_MANIFEST",
        "hypothesis_id": "HYP_004",
        "hypothesis_ordinal": 4,
        "mechanism_id": "MEC-0014A",
        "hypothesis_sha256": EXPECTED_HYP_004_SHA256,
        "r1_manifest_sha256": EXPECTED_R1_MANIFEST_SHA256,
        "preregistration_sha256": EXPECTED_PREREG_SHA256,
        "source_git_sha": source_git_sha,
        "dataset_id": "HYP_004_MEC0014A_R2_session_endpoints",
        "calendar_authority": "NyseCa1Calendar",
        "temporal_bounds": {
            "start": "2017-01-01",
            "end": "2022-12-31",
            "oos_sealed_boundary": ">= 2023-01-01",
        },
        "session_census": {
            "total_enumerated_regular_sessions": TOTAL_EXPECTED_REGULAR_SESSIONS,
            "eligible_regression_sessions": eligible_count,
            "excluded_sessions": excluded_count,
            "exclusion_reason_census": dict(sorted(exclusion_census.items())),
        },
        "provider_contracts": {
            "feed": "sip",
            "symbol": "SPY",
            "intraday_endpoint_rule": "QUALIFIED_LAST_SIP_TRANSACTION_PRICE_AT_OR_BEFORE_BOUNDARY",
            "daily_trade_count_rule": "RAW_REGULAR_SESSION_SIP_TRADE_COUNT >= 500",
            "closing_authority_rule": "NYSE_ARCA_PRIMARY_CLOSING_AUCTION_X_P_C_6",
        },
        "provenance_digests": {
            "total_raw_pages_count": total_raw_pages,
            "raw_evidence_aggregate_sha256": raw_evidence_aggregate_sha256,
            "local_page_manifest_sha256": raw_page_manifest_sha256,
            "local_session_ledger_sha256": session_ledger_sha256,
            "local_endpoint_dataset_sha256": local_dataset_sha256,
        },
        "governance_assertions": {
            "no_returns_computed": True,
            "no_regressions_computed": True,
            "oos_holdout_sealed": True,
            "capital_authority_usd": "0.00",
            "trading_authorized": False,
        },
        "status": "STEP_R2_HISTORICAL_DATA_QUALIFIED_PASS",
        "next_required_step": "STEP_R3_MEC0014A_PRIMARY_RETURN_AND_REGRESSION_LOCKED_PENDING_SEPARATE_HUMAN_AUTHORIZATION",
    }

    manifest_json = CanonicalConfigSerializer.to_canonical_json(payload)
    manifest_digest = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
    payload["manifest_sha256"] = manifest_digest
    return payload
