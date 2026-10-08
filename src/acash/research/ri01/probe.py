"""RI-01 provider probe R1 harness (CODE PREPARATION ONLY).

Bounded zero-outcome network probe design. THIS MODULE MUST NOT BE EXECUTED
against live endpoints without a future single explicit network authority
(after HYP_011 Observation #1 forensic check), and NEVER from /home/mew/Acash
while HYP_011 V2 is armed.

Scope, frozen:
- Symbol: SPY only (hardcoded; any other symbol is rejected).
- Sessions: allowlisted already-consumed / pre-holdout dates only.
  The sealed 2023-2026 holdout (>= 2023-01-01) is rejected before any network.
- Capabilities: 1Min SIP raw bars (paginated to exhaustion), narrow
  historical-trades windows around open/close (exchange + conditions
  preserved), credential-entitlement signal, rate-limit headers, raw-bytes +
  SHA-256 envelopes, deterministic re-fetch stability comparison.

Computes NOTHING predictive: no returns, no PnL, no Sharpe, no hit-rate, no
thresholds, no signal. Missing data is DATA_UNAVAILABLE, never imputed.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import httpx

from acash.core.domain.exceptions import DataContractError
from acash.core.runtime_identity import get_current_runtime_sha
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.evidence import (
    RetrievalPageRecord,
    RetrievalRunManifest,
    ordered_page_chain_digest,
    validate_external_evidence_root,
    write_immutable_bytes,
    write_immutable_json,
)
from acash.execution.alpaca.credentials import (
    AlpacaCredentialError,
    EnvAlpacaCredentialProvider,
)
from acash.research.ri01.feasibility import (
    parse_utc_timestamp,
    require_complete_rth_grid,
    validate_provider_bar,
)

DATA_HOST = "https://data.alpaca.markets"
PROBE_SYMBOL = "SPY"
PROBE_FEED = "sip"
PROBE_TIMEFRAME = "1Min"
PROBE_ADJUSTMENT = "raw"
HOLDOUT_START: date = date(2023, 1, 1)

_HEX40_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")

# Already-consumed (MEC-0015 probes) or pre-holdout sessions ONLY:
# - 2018-06-01: early-depth regular session (390 min expected)
# - 2021-06-01: normal later in-sample regular session (390 min expected)
# - 2021-11-26: historical half-day (210 min expected)
ALLOWLISTED_SESSIONS: tuple[date, ...] = (
    date(2018, 6, 1),
    date(2021, 6, 1),
    date(2021, 11, 26),
)

CAPABILITIES: tuple[str, ...] = ("bars", "trades")


@dataclass(frozen=True)
class RI01ProbeAuthority:
    """Structured, hash-bound operator authorization artifact for RI-01 bounded probe.

    NOTE: This is a hash-bound operator authorization artifact, NOT a
    cryptographically signed PKI credential.
    """

    authority_id: str
    runtime_sha: str
    session: date
    capability: str
    evidence_root: Path
    max_requests: int
    valid_from_utc: datetime
    valid_until_utc: datetime
    symbol: str = PROBE_SYMBOL
    read_only: bool = True
    no_outcomes: bool = True
    no_paper: bool = True
    no_live: bool = True
    capital_usd: Decimal = Decimal("0.00")
    no_real_orders: bool = True

    @property
    def authority_sha256(self) -> str:
        """Deterministic SHA-256 digest over the canonical authority document."""
        return CanonicalConfigSerializer.compute_sha256(self.to_dict())

    def validate(
        self,
        now_utc: datetime,
        current_runtime_sha: str,
        calendar: NyseCa1Calendar,
    ) -> None:
        """Validate authority fail-closed against time windows, commit hash, and locks."""
        if not self.authority_id or not self.authority_id.startswith("AUTHORIZE_RI01_PROBE_R1_"):
            raise DataContractError(
                f"RI01_PROBE_BAD_AUTHORITY_ID: must start with AUTHORIZE_RI01_PROBE_R1_, got '{self.authority_id}'."
            )
        if not isinstance(self.runtime_sha, str) or not _HEX40_PATTERN.match(self.runtime_sha):
            raise DataContractError(
                f"RI01_PROBE_BAD_RUNTIME_SHA: authority runtime_sha must be 40-char hex, got '{self.runtime_sha}'."
            )
        if self.runtime_sha != current_runtime_sha:
            raise DataContractError(
                f"RI01_PROBE_RUNTIME_MISMATCH: authority bound to {self.runtime_sha}, current runtime is {current_runtime_sha}."
            )
        if self.symbol != PROBE_SYMBOL:
            raise DataContractError(
                f"RI01_PROBE_SYMBOL_FORBIDDEN: only {PROBE_SYMBOL} is allowed, got '{self.symbol}'."
            )
        if self.session >= HOLDOUT_START:
            raise DataContractError(
                f"RI01_PROBE_HOLDOUT_FORBIDDEN: {self.session.isoformat()} is in sealed 2023-2026 holdout."
            )
        if self.session not in ALLOWLISTED_SESSIONS:
            raise DataContractError(
                f"RI01_PROBE_SESSION_NOT_ALLOWLISTED: {self.session.isoformat()}."
            )
        if not calendar.is_trading_session(self.session):
            raise DataContractError(
                f"RI01_PROBE_NON_SESSION: {self.session.isoformat()}."
            )
        if self.capability not in CAPABILITIES:
            raise DataContractError(
                f"RI01_PROBE_UNKNOWN_CAPABILITY: {self.capability}."
            )
        validate_external_evidence_root(self.evidence_root)
        if self.max_requests <= 0:
            raise DataContractError(
                f"RI01_PROBE_INVALID_REQUEST_BUDGET: max_requests must be > 0, got {self.max_requests}."
            )
        if self.valid_from_utc.tzinfo is None or self.valid_until_utc.tzinfo is None:
            raise DataContractError("RI01_PROBE_AUTHORITY_NAIVE_TIME.")
        if not self.valid_from_utc < self.valid_until_utc:
            raise DataContractError("RI01_PROBE_AUTHORITY_WINDOW_INVERTED.")
        if now_utc < self.valid_from_utc:
            raise DataContractError(
                f"RI01_PROBE_AUTHORITY_FUTURE: valid from {self.valid_from_utc.isoformat()}, now is {now_utc.isoformat()}."
            )
        if now_utc > self.valid_until_utc:
            raise DataContractError(
                f"RI01_PROBE_AUTHORITY_EXPIRED: valid until {self.valid_until_utc.isoformat()}, now is {now_utc.isoformat()}."
            )
        # Lock enforcement
        if not self.read_only:
            raise DataContractError("RI01_PROBE_LOCK_VIOLATION: read_only must be True.")
        if not self.no_outcomes:
            raise DataContractError("RI01_PROBE_LOCK_VIOLATION: no_outcomes must be True.")
        if not self.no_paper:
            raise DataContractError("RI01_PROBE_LOCK_VIOLATION: no_paper must be True.")
        if not self.no_live:
            raise DataContractError("RI01_PROBE_LOCK_VIOLATION: no_live must be True.")
        if self.capital_usd != Decimal("0.00"):
            raise DataContractError("RI01_PROBE_LOCK_VIOLATION: capital_usd must be 0.00.")
        if not self.no_real_orders:
            raise DataContractError("RI01_PROBE_LOCK_VIOLATION: no_real_orders must be True.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "authority_id": self.authority_id,
            "runtime_sha": self.runtime_sha,
            "session": self.session.isoformat(),
            "capability": self.capability,
            "symbol": self.symbol,
            "evidence_root": str(self.evidence_root),
            "max_requests": self.max_requests,
            "valid_from_utc": self.valid_from_utc.isoformat(),
            "valid_until_utc": self.valid_until_utc.isoformat(),
            "read_only": self.read_only,
            "no_outcomes": self.no_outcomes,
            "no_paper": self.no_paper,
            "no_live": self.no_live,
            "capital_usd": str(self.capital_usd),
            "no_real_orders": self.no_real_orders,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RI01ProbeAuthority":
        if not isinstance(data, Mapping):
            raise DataContractError(
                f"RI01_PROBE_AUTHORITY_NOT_MAPPING: expected mapping, got {type(data).__name__}."
            )

        allowed_fields = {
            "authority_id",
            "runtime_sha",
            "session",
            "capability",
            "symbol",
            "evidence_root",
            "max_requests",
            "valid_from_utc",
            "valid_until_utc",
            "read_only",
            "no_outcomes",
            "no_paper",
            "no_live",
            "capital_usd",
            "no_real_orders",
        }
        unknown = set(data.keys()) - allowed_fields
        if unknown:
            raise DataContractError(
                f"RI01_PROBE_AUTHORITY_UNKNOWN_FIELDS: unexpected fields {sorted(unknown)}."
            )

        mandatory_fields = (
            "authority_id",
            "runtime_sha",
            "session",
            "capability",
            "evidence_root",
            "max_requests",
            "valid_from_utc",
            "valid_until_utc",
        )
        for field in mandatory_fields:
            if field not in data:
                raise DataContractError(
                    f"RI01_PROBE_AUTHORITY_MISSING_FIELD: '{field}' is required."
                )

        authority_id = data["authority_id"]
        if not isinstance(authority_id, str):
            raise DataContractError("RI01_PROBE_AUTHORITY_BAD_TYPE: authority_id must be str.")

        runtime_sha = data["runtime_sha"]
        if not isinstance(runtime_sha, str) or not _HEX40_PATTERN.match(runtime_sha):
            raise DataContractError(
                "RI01_PROBE_AUTHORITY_BAD_TYPE: runtime_sha must be 40-char hex string."
            )

        raw_session = data["session"]
        if isinstance(raw_session, date) and not isinstance(raw_session, datetime):
            session = raw_session
        elif isinstance(raw_session, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", raw_session):
            try:
                session = date.fromisoformat(raw_session)
            except ValueError as exc:
                raise DataContractError(f"RI01_PROBE_AUTHORITY_BAD_SESSION: {exc}.") from exc
        else:
            raise DataContractError("RI01_PROBE_AUTHORITY_BAD_TYPE: session must be YYYY-MM-DD date.")

        capability = data["capability"]
        if not isinstance(capability, str):
            raise DataContractError("RI01_PROBE_AUTHORITY_BAD_TYPE: capability must be str.")

        symbol = data.get("symbol", PROBE_SYMBOL)
        if not isinstance(symbol, str) or symbol != PROBE_SYMBOL:
            raise DataContractError(
                f"RI01_PROBE_AUTHORITY_BAD_SYMBOL: symbol must be {PROBE_SYMBOL}."
            )

        evidence_root_raw = data["evidence_root"]
        if not isinstance(evidence_root_raw, (str, Path)):
            raise DataContractError("RI01_PROBE_AUTHORITY_BAD_TYPE: evidence_root must be str or Path.")
        evidence_root = Path(evidence_root_raw)

        max_requests = data["max_requests"]
        if (
            not isinstance(max_requests, int)
            or isinstance(max_requests, bool)
            or max_requests <= 0
        ):
            raise DataContractError("RI01_PROBE_AUTHORITY_BAD_TYPE: max_requests must be positive int.")

        raw_from = data["valid_from_utc"]
        if not isinstance(raw_from, (str, datetime)):
            raise DataContractError("RI01_PROBE_AUTHORITY_BAD_TYPE: valid_from_utc must be str or datetime.")
        try:
            valid_from_utc = (
                raw_from if isinstance(raw_from, datetime) else datetime.fromisoformat(raw_from)
            )
            if valid_from_utc.tzinfo is None:
                raise DataContractError("RI01_PROBE_AUTHORITY_NAIVE_TIME: valid_from_utc must be timezone-aware.")
        except (ValueError, TypeError) as exc:
            raise DataContractError(f"RI01_PROBE_AUTHORITY_BAD_TIMESTAMP: {exc}.") from exc

        raw_until = data["valid_until_utc"]
        if not isinstance(raw_until, (str, datetime)):
            raise DataContractError("RI01_PROBE_AUTHORITY_BAD_TYPE: valid_until_utc must be str or datetime.")
        try:
            valid_until_utc = (
                raw_until if isinstance(raw_until, datetime) else datetime.fromisoformat(raw_until)
            )
            if valid_until_utc.tzinfo is None:
                raise DataContractError("RI01_PROBE_AUTHORITY_NAIVE_TIME: valid_until_utc must be timezone-aware.")
        except (ValueError, TypeError) as exc:
            raise DataContractError(f"RI01_PROBE_AUTHORITY_BAD_TIMESTAMP: {exc}.") from exc

        # Strict fail-closed bool decoding (reject string "false"/"true", int 0/1)
        bool_fields = ("read_only", "no_outcomes", "no_paper", "no_live", "no_real_orders")
        bool_vals = {}
        for bf in bool_fields:
            if bf in data:
                v = data[bf]
                if type(v) is not bool:
                    raise DataContractError(
                        f"RI01_PROBE_AUTHORITY_BAD_TYPE: {bf} must be bool, got {type(v).__name__}."
                    )
                bool_vals[bf] = v
            else:
                bool_vals[bf] = True

        raw_cap = data.get("capital_usd", "0.00")
        try:
            capital_usd = Decimal(str(raw_cap))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise DataContractError(f"RI01_PROBE_AUTHORITY_BAD_NUMERIC: capital_usd: {exc}.") from exc
        if capital_usd != Decimal("0.00"):
            raise DataContractError(f"RI01_PROBE_AUTHORITY_NONZERO_CAPITAL: got {capital_usd}.")

        return cls(
            authority_id=authority_id,
            runtime_sha=runtime_sha,
            session=session,
            capability=capability,
            symbol=symbol,
            evidence_root=evidence_root,
            max_requests=max_requests,
            valid_from_utc=valid_from_utc,
            valid_until_utc=valid_until_utc,
            read_only=bool_vals["read_only"],
            no_outcomes=bool_vals["no_outcomes"],
            no_paper=bool_vals["no_paper"],
            no_live=bool_vals["no_live"],
            capital_usd=capital_usd,
            no_real_orders=bool_vals["no_real_orders"],
        )


@dataclass(frozen=True)
class RI01QualificationRecord:
    """Canonical consumer qualification record for an RI-01 dataset.

    Separates consumer qualification from generic retrieval.
    Only sessions satisfying exact [session_open, session_close) calendar-derived
    RTH grid receive status="QUALIFIED".
    """

    qualification_id: str
    session: str
    symbol: str
    capability: str
    status: str  # QUALIFIED, DATA_UNAVAILABLE, CONTRACT_FAILED
    retrieval_run_id: str
    retrieval_manifest_sha256: str
    authority_sha256: str
    raw_item_count: int
    qualified_item_count: int
    expected_item_count: int
    evaluated_at_utc: str
    schema_version: str = "1.0"
    error_message: Optional[str] = None

    def __post_init__(self) -> None:
        if self.status not in ("QUALIFIED", "DATA_UNAVAILABLE", "CONTRACT_FAILED"):
            raise DataContractError(
                f"RI01_QUALIFICATION_BAD_STATUS: '{self.status}'."
            )
        if not _HEX64_PATTERN.match(self.retrieval_manifest_sha256):
            raise DataContractError(
                f"RI01_QUALIFICATION_BAD_MANIFEST_SHA: '{self.retrieval_manifest_sha256}'."
            )
        if not _HEX64_PATTERN.match(self.authority_sha256):
            raise DataContractError(
                f"RI01_QUALIFICATION_BAD_AUTHORITY_SHA: '{self.authority_sha256}'."
            )
        try:
            ts = datetime.fromisoformat(self.evaluated_at_utc)
            if ts.tzinfo is None:
                raise DataContractError("RI01_QUALIFICATION_NAIVE_TIME.")
        except (ValueError, TypeError) as exc:
            raise DataContractError(f"RI01_QUALIFICATION_BAD_TIMESTAMP: {exc}.") from exc

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "qualification_id": self.qualification_id,
            "session": self.session,
            "symbol": self.symbol,
            "capability": self.capability,
            "status": self.status,
            "retrieval_run_id": self.retrieval_run_id,
            "retrieval_manifest_sha256": self.retrieval_manifest_sha256,
            "authority_sha256": self.authority_sha256,
            "raw_item_count": self.raw_item_count,
            "qualified_item_count": self.qualified_item_count,
            "expected_item_count": self.expected_item_count,
            "error_message": self.error_message,
            "evaluated_at_utc": self.evaluated_at_utc,
        }

    def qualification_sha256(self) -> str:
        return CanonicalConfigSerializer.compute_sha256(self.to_dict())

    def write_immutable(self, target_file: Path) -> str:
        return write_immutable_json(target_file, self.to_dict())


@dataclass(frozen=True)
class ProbeTrade:
    """One historical trade with venue + condition provenance preserved."""

    timestamp_utc: datetime
    exchange: str
    price: Decimal
    size: Decimal
    conditions: Tuple[str, ...]

    @classmethod
    def from_dict(cls, doc: Mapping[str, Any], context: str) -> "ProbeTrade":
        if not isinstance(doc, Mapping):
            raise DataContractError(f"RI01_TRADE_NOT_A_MAPPING: {context}.")
        timestamp = parse_utc_timestamp(doc.get("t"), f"{context}.t")
        exchange = doc.get("x")
        if not isinstance(exchange, str) or not exchange.strip():
            raise DataContractError(f"RI01_TRADE_BAD_EXCHANGE: {context}.")
        try:
            price = Decimal(str(doc.get("p")))
            size = Decimal(str(doc.get("s")))
        except (InvalidOperation, ValueError, TypeError, ArithmeticError) as exc:
            raise DataContractError(f"RI01_TRADE_BAD_NUMERIC: {context}.") from exc
        if not price.is_finite() or price <= 0:
            raise DataContractError(f"RI01_TRADE_NONPOSITIVE_PRICE: {context}.")
        if not size.is_finite() or size <= 0:
            raise DataContractError(f"RI01_TRADE_NONPOSITIVE_SIZE: {context}.")
        raw_conditions = doc.get("c", [])
        if not isinstance(raw_conditions, list) or not all(
            isinstance(item, str) for item in raw_conditions
        ):
            raise DataContractError(f"RI01_TRADE_BAD_CONDITIONS: {context}.")
        return cls(
            timestamp_utc=timestamp,
            exchange=exchange.strip(),
            price=price,
            size=size,
            conditions=tuple(raw_conditions),
        )


def _extract_rate_limit_headers(headers: httpx.Headers) -> Dict[str, str]:
    """Capture only response header names beginning case-insensitively with 'x-ratelimit-'."""
    captured: Dict[str, str] = {}
    for key, val in headers.items():
        k_lower = key.lower()
        if k_lower.startswith("x-ratelimit-"):
            captured[k_lower] = str(val)
    return captured


def _auth_headers(credential_provider: EnvAlpacaCredentialProvider) -> Dict[str, str]:
    try:
        creds = credential_provider.load()
    except AlpacaCredentialError as exc:
        raise DataContractError(f"RI01_PROBE_CREDENTIALS_UNAVAILABLE: {exc}.") from exc
    return {
        "APCA-API-KEY-ID": creds.api_key_id,
        "APCA-API-SECRET-KEY": creds.api_secret_ref,
    }


def _auth_failure_outcome(response: httpx.Response) -> Tuple[str, str]:
    """Classify observed failures without inferring entitlement from HTTP alone.

    Alpaca's documented SIP restriction requires both the machine code and
    the exact allowlisted message: 42210000 is also used for unrelated errors.
    Arbitrary response bodies are never retained in terminal evidence.
    """
    status_code = response.status_code
    if status_code == 401:
        return ("RI01_PROBE_AUTHENTICATION_FAILED: HTTP 401.", "AUTHENTICATION_FAILED")
    if status_code in (403, 422) and len(response.content) <= 4096:
        try:
            doc = response.json()
        except ValueError:
            doc = None
        if (
            isinstance(doc, dict)
            and type(doc.get("code")) is int
            and doc.get("code") in (42210000, 40010001)
            and doc.get("message") == "subscription does not permit querying recent SIP data"
        ):
            return (
                "RI01_PROBE_ENTITLEMENT_DENIED: provider confirmed recent SIP subscription restriction.",
                "ENTITLEMENT_DENIED",
            )
    if status_code == 403:
        return ("RI01_PROBE_ACCESS_FORBIDDEN: HTTP 403; reason unconfirmed.", "ACCESS_FORBIDDEN")
    return (f"RI01_PROBE_HTTP_FAILED: HTTP {status_code}.", "HTTP_FAILED")


class RI01ProbeClient:
    """Minimal read-only Alpaca client for the R1 probe (injectable transport)."""

    def __init__(
        self,
        credential_provider: Optional[EnvAlpacaCredentialProvider] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        self._credential_provider = credential_provider or EnvAlpacaCredentialProvider()
        self._http = httpx.Client(transport=transport, timeout=30.0)
        self.requests_issued = 0
        self.last_qualification_record: Optional[RI01QualificationRecord] = None

    def _write_terminal_manifest(
        self,
        target_dir: Path,
        authority: RI01ProbeAuthority,
        capability: str,
        page_records: Sequence[RetrievalPageRecord],
        raw_items_count: int,
        status: str,
        error_message: str,
        now_utc: datetime,
        failure_metadata: Optional[Mapping[str, Any]] = None,
    ) -> RetrievalRunManifest:
        chain_digest = (
            ordered_page_chain_digest(page_records)
            if page_records
            else CanonicalConfigSerializer.compute_sha256([])
        )
        manifest = RetrievalRunManifest(
            schema_version="1.1",
            run_id=f"RUN_{authority.session.isoformat()}_{capability}",
            consumer_id="ri01",
            operation=f"fetch_{capability}",
            subject_metadata={
                "symbol": PROBE_SYMBOL,
                "session": authority.session.isoformat(),
                "capability": capability,
                **(failure_metadata or {}),
            },
            runtime_sha=authority.runtime_sha,
            authority_ref=authority.authority_id,
            authority_sha256=authority.authority_sha256,
            page_records=tuple(page_records),
            page_chain_sha256=chain_digest,
            item_count=raw_items_count,
            operation_count=self.requests_issued,
            status=status,
            error_message=error_message,
            created_at_utc=now_utc.isoformat(),
        )
        manifest.write_immutable(target_dir / "manifest.json")
        return manifest

    def fetch_bars(
        self,
        authority: RI01ProbeAuthority,
        calendar: NyseCa1Calendar,
        now_utc: datetime,
    ) -> Tuple[RetrievalRunManifest, List[Dict[str, Any]]]:
        """Fetch one session of 1Min SIP raw bars, paginated to exhaustion.

        Enforces:
        - Strict request budget
        - Loop detection on repeated page tokens
        - Immutable raw page storage in Evidence Plane BEFORE qualification
        - Per-page rate limit header capture (x-ratelimit- prefix only)
        - Disentangles generic retrieval (RETRIEVED) from consumer qualification (QUALIFIED)
        - Incomplete sessions receive qualification status CONTRACT_FAILED, NEVER QUALIFIED
        """
        bounds = calendar.get_session(authority.session)
        if bounds.open_utc is None or bounds.close_utc is None:
            raise DataContractError(f"RI01_SESSION_BOUNDS_MISSING: {authority.session.isoformat()}.")
        open_utc = bounds.open_utc.astimezone(timezone.utc)
        close_utc = bounds.close_utc.astimezone(timezone.utc)

        target_dir = authority.evidence_root / authority.session.isoformat() / "bars"
        target_dir.mkdir(parents=True, exist_ok=True)

        params: Dict[str, Any] = {
            "symbols": PROBE_SYMBOL,
            "timeframe": PROBE_TIMEFRAME,
            "start": open_utc.isoformat(),
            "end": close_utc.isoformat(),
            "feed": PROBE_FEED,
            "adjustment": PROBE_ADJUSTMENT,
            "sort": "asc",
            "limit": 1000,
        }

        page_records: List[RetrievalPageRecord] = []
        raw_bars: List[Dict[str, Any]] = []
        seen_tokens: set[str] = set()
        page_token: Optional[str] = None
        page_index = 0

        while True:
            if self.requests_issued >= authority.max_requests:
                err_msg = (
                    f"RI01_PROBE_REQUEST_BUDGET_EXHAUSTED: issued {self.requests_issued} >= limit {authority.max_requests}."
                )
                self._write_terminal_manifest(
                    target_dir=target_dir,
                    authority=authority,
                    capability="bars",
                    page_records=page_records,
                    raw_items_count=len(raw_bars),
                    status="PARTIAL",
                    error_message=err_msg,
                    now_utc=now_utc,
                )
                raise DataContractError(err_msg)

            if page_token is not None:
                params["page_token"] = page_token

            headers = _auth_headers(self._credential_provider)
            self.requests_issued += 1  # Local invocation count, not provider receipt.
            try:
                response = self._http.get(
                    f"{DATA_HOST}/v2/stocks/bars", params=params, headers=headers,
                )
            except httpx.RequestError:
                err_msg = "RI01_PROBE_TRANSPORT_FAILED: no HTTP response observed; provider acceptance unknown."
                self._write_terminal_manifest(
                    target_dir=target_dir, authority=authority,
                    capability="bars", page_records=page_records,
                    raw_items_count=len(raw_bars), status="TRANSPORT_FAILED",
                    error_message=err_msg, now_utc=now_utc,
                    failure_metadata={
                        "invocation_initiated": True,
                        "provider_acceptance": "UNKNOWN",
                        "http_response_observed": False,
                        "retrieval_completed": False,
                        "previous_pages_observed": len(page_records),
                    },
                )
                raise DataContractError(err_msg) from None

            if response.status_code in (401, 403, 422):
                err_msg, term_status = _auth_failure_outcome(response)
                self._write_terminal_manifest(
                    target_dir=target_dir,
                    authority=authority,
                    capability="bars",
                    page_records=page_records,
                    raw_items_count=len(raw_bars),
                    status=term_status,
                    error_message=err_msg,
                    now_utc=now_utc,
                    failure_metadata={"http_status": response.status_code,
                                      "http_response_observed": True,
                                      "invocation_initiated": True,
                                      "provider_acceptance": "RESPONSE_OBSERVED",
                                      "retrieval_completed": False},
                )
                raise DataContractError(err_msg)
            if response.status_code != 200:
                err_msg = f"RI01_PROBE_BARS_HTTP_{response.status_code}."
                self._write_terminal_manifest(
                    target_dir=target_dir,
                    authority=authority,
                    capability="bars",
                    page_records=page_records,
                    raw_items_count=len(raw_bars),
                    status="HTTP_FAILED",
                    error_message=err_msg,
                    now_utc=now_utc,
                )
                raise DataContractError(err_msg)

            rate_limits = _extract_rate_limit_headers(response.headers)
            page_filename = f"page_{page_index:04d}.bin"
            page_path = target_dir / page_filename
            page_sha256 = write_immutable_bytes(page_path, response.content)

            try:
                doc = response.json()
            except ValueError as exc:
                err_msg = f"RI01_PROBE_BARS_CORRUPT: {exc}."
                self._write_terminal_manifest(
                    target_dir=target_dir,
                    authority=authority,
                    capability="bars",
                    page_records=page_records,
                    raw_items_count=len(raw_bars),
                    status="MALFORMED_RESPONSE",
                    error_message=err_msg,
                    now_utc=now_utc,
                )
                raise DataContractError(err_msg) from exc

            entries = doc.get("bars", {}).get(PROBE_SYMBOL, [])
            if not isinstance(entries, list):
                err_msg = "RI01_PROBE_BARS_MALFORMED."
                self._write_terminal_manifest(
                    target_dir=target_dir,
                    authority=authority,
                    capability="bars",
                    page_records=page_records,
                    raw_items_count=len(raw_bars),
                    status="MALFORMED_RESPONSE",
                    error_message=err_msg,
                    now_utc=now_utc,
                )
                raise DataContractError(err_msg)

            for position, entry in enumerate(entries):
                if not isinstance(entry, Mapping):
                    err_msg = "RI01_PROBE_BAR_NOT_A_MAPPING."
                    self._write_terminal_manifest(
                        target_dir=target_dir,
                        authority=authority,
                        capability="bars",
                        page_records=page_records,
                        raw_items_count=len(raw_bars),
                        status="MALFORMED_RESPONSE",
                        error_message=err_msg,
                        now_utc=now_utc,
                    )
                    raise DataContractError(err_msg)
                raw_bars.append(
                    validate_provider_bar(
                        {
                            "timestamp": entry.get("t"),
                            "open": entry.get("o"),
                            "high": entry.get("h"),
                            "low": entry.get("l"),
                            "close": entry.get("c"),
                            "volume": entry.get("v"),
                        },
                        f"{authority.session.isoformat()}[{len(raw_bars)}]",
                    )
                )

            next_token = doc.get("next_page_token")

            page_records.append(
                RetrievalPageRecord(
                    page_index=page_index,
                    request_token=page_token,
                    next_page_token=next_token,
                    item_count=len(entries),
                    raw_bytes_sha256=page_sha256,
                    page_file=page_filename,
                    rate_limit_headers=rate_limits,
                    retrieved_at_utc=now_utc.isoformat(),
                )
            )

            if not next_token:
                break

            if next_token in seen_tokens:
                err_msg = f"RI01_PROBE_REPEATED_PAGE_TOKEN: loop detected on token {next_token}."
                self._write_terminal_manifest(
                    target_dir=target_dir,
                    authority=authority,
                    capability="bars",
                    page_records=page_records,
                    raw_items_count=len(raw_bars),
                    status="MALFORMED_RESPONSE",
                    error_message=err_msg,
                    now_utc=now_utc,
                )
                raise DataContractError(err_msg)
            seen_tokens.add(next_token)
            page_token = next_token
            page_index += 1

        chain_digest = ordered_page_chain_digest(page_records)
        manifest = RetrievalRunManifest(
            schema_version="1.1",
            run_id=f"RUN_{authority.session.isoformat()}_bars",
            consumer_id="ri01",
            operation="fetch_bars",
            subject_metadata={
                "symbol": PROBE_SYMBOL,
                "session": authority.session.isoformat(),
                "capability": "bars",
                "timeframe": PROBE_TIMEFRAME,
                "feed": PROBE_FEED,
                "adjustment": PROBE_ADJUSTMENT,
            },
            runtime_sha=authority.runtime_sha,
            authority_ref=authority.authority_id,
            authority_sha256=authority.authority_sha256,
            page_records=tuple(page_records),
            page_chain_sha256=chain_digest,
            item_count=len(raw_bars),
            operation_count=len(page_records),
            status="RETRIEVED",
            error_message=None,
            created_at_utc=now_utc.isoformat(),
        )
        manifest.write_immutable(target_dir / "manifest.json")

        # Canonical RTH qualification [open, close)
        # Provider start/end are inclusive; exclude any bar at or after close_utc
        session_info = calendar.get_session(authority.session)
        expected_bars = session_info.expected_minute_count
        qualified_bars = [
            b
            for b in raw_bars
            if open_utc <= parse_utc_timestamp(b["timestamp"], "bar") < close_utc
        ]
        qual_id = f"QUAL_{authority.session.isoformat()}_bars"
        try:
            require_complete_rth_grid(
                qualified_bars, authority.session, calendar, f"{authority.session.isoformat()}/bars"
            )
            qual_record = RI01QualificationRecord(
                qualification_id=qual_id,
                session=authority.session.isoformat(),
                symbol=PROBE_SYMBOL,
                capability="bars",
                status="QUALIFIED",
                retrieval_run_id=manifest.run_id,
                retrieval_manifest_sha256=manifest.manifest_sha256(),
                authority_sha256=authority.authority_sha256,
                raw_item_count=len(raw_bars),
                qualified_item_count=len(qualified_bars),
                expected_item_count=expected_bars,
                evaluated_at_utc=now_utc.isoformat(),
                error_message=None,
            )
            qual_record.write_immutable(target_dir / "qualification.json")
            self.last_qualification_record = qual_record
        except Exception as exc:
            qual_record = RI01QualificationRecord(
                qualification_id=qual_id,
                session=authority.session.isoformat(),
                symbol=PROBE_SYMBOL,
                capability="bars",
                status="CONTRACT_FAILED",
                retrieval_run_id=manifest.run_id,
                retrieval_manifest_sha256=manifest.manifest_sha256(),
                authority_sha256=authority.authority_sha256,
                raw_item_count=len(raw_bars),
                qualified_item_count=len(qualified_bars),
                expected_item_count=expected_bars,
                evaluated_at_utc=now_utc.isoformat(),
                error_message=str(exc),
            )
            qual_record.write_immutable(target_dir / "qualification.json")
            self.last_qualification_record = qual_record
            raise

        return manifest, qualified_bars

    def fetch_trades_window(
        self,
        window_start_utc: datetime,
        window_end_utc: datetime,
        window_label: str,
        authority: RI01ProbeAuthority,
        now_utc: datetime,
    ) -> Tuple[RetrievalRunManifest, List[ProbeTrade]]:
        """Fetch historical SIP trades in a window, paginated to exhaustion."""
        if window_start_utc.tzinfo is None or window_end_utc.tzinfo is None:
            raise DataContractError("RI01_PROBE_WINDOW_NAIVE_TIME.")
        if not window_start_utc < window_end_utc:
            raise DataContractError("RI01_PROBE_WINDOW_INVERTED.")

        target_dir = (
            authority.evidence_root
            / authority.session.isoformat()
            / f"trades_{window_label}"
        )
        target_dir.mkdir(parents=True, exist_ok=True)

        params: Dict[str, Any] = {
            "symbols": PROBE_SYMBOL,
            "start": window_start_utc.isoformat(),
            "end": window_end_utc.isoformat(),
            "feed": PROBE_FEED,
            "sort": "asc",
            "limit": 1000,
        }

        page_records: List[RetrievalPageRecord] = []
        trades: List[ProbeTrade] = []
        seen_tokens: set[str] = set()
        page_token: Optional[str] = None
        page_index = 0

        while True:
            if self.requests_issued >= authority.max_requests:
                err_msg = (
                    f"RI01_PROBE_REQUEST_BUDGET_EXHAUSTED: issued {self.requests_issued} >= limit {authority.max_requests}."
                )
                self._write_terminal_manifest(
                    target_dir=target_dir,
                    authority=authority,
                    capability=f"trades_{window_label}",
                    page_records=page_records,
                    raw_items_count=len(trades),
                    status="PARTIAL",
                    error_message=err_msg,
                    now_utc=now_utc,
                )
                raise DataContractError(err_msg)

            if page_token is not None:
                params["page_token"] = page_token

            headers = _auth_headers(self._credential_provider)
            self.requests_issued += 1  # Local invocation count, not provider receipt.
            try:
                response = self._http.get(
                    f"{DATA_HOST}/v2/stocks/trades", params=params, headers=headers,
                )
            except httpx.RequestError:
                err_msg = "RI01_PROBE_TRANSPORT_FAILED: no HTTP response observed; provider acceptance unknown."
                self._write_terminal_manifest(
                    target_dir=target_dir, authority=authority,
                    capability=f"trades_{window_label}", page_records=page_records,
                    raw_items_count=len(trades), status="TRANSPORT_FAILED",
                    error_message=err_msg, now_utc=now_utc,
                    failure_metadata={
                        "invocation_initiated": True,
                        "provider_acceptance": "UNKNOWN",
                        "http_response_observed": False,
                        "retrieval_completed": False,
                        "previous_pages_observed": len(page_records),
                    },
                )
                raise DataContractError(err_msg) from None

            if response.status_code in (401, 403, 422):
                err_msg, term_status = _auth_failure_outcome(response)
                self._write_terminal_manifest(
                    target_dir=target_dir,
                    authority=authority,
                    capability=f"trades_{window_label}",
                    page_records=page_records,
                    raw_items_count=len(trades),
                    status=term_status,
                    error_message=err_msg,
                    now_utc=now_utc,
                    failure_metadata={"http_status": response.status_code,
                                      "http_response_observed": True,
                                      "invocation_initiated": True,
                                      "provider_acceptance": "RESPONSE_OBSERVED",
                                      "retrieval_completed": False},
                )
                raise DataContractError(err_msg)
            if response.status_code != 200:
                err_msg = f"RI01_PROBE_TRADES_HTTP_{response.status_code}."
                self._write_terminal_manifest(
                    target_dir=target_dir,
                    authority=authority,
                    capability=f"trades_{window_label}",
                    page_records=page_records,
                    raw_items_count=len(trades),
                    status="HTTP_FAILED",
                    error_message=err_msg,
                    now_utc=now_utc,
                )
                raise DataContractError(err_msg)

            rate_limits = _extract_rate_limit_headers(response.headers)
            page_filename = f"page_{page_index:04d}.bin"
            page_path = target_dir / page_filename
            page_sha256 = write_immutable_bytes(page_path, response.content)

            try:
                doc = response.json()
            except ValueError as exc:
                err_msg = f"RI01_PROBE_TRADES_CORRUPT: {exc}."
                self._write_terminal_manifest(
                    target_dir=target_dir,
                    authority=authority,
                    capability=f"trades_{window_label}",
                    page_records=page_records,
                    raw_items_count=len(trades),
                    status="MALFORMED_RESPONSE",
                    error_message=err_msg,
                    now_utc=now_utc,
                )
                raise DataContractError(err_msg) from exc

            entries = doc.get("trades", {}).get(PROBE_SYMBOL, [])
            if not isinstance(entries, list):
                err_msg = "RI01_PROBE_TRADES_MALFORMED."
                self._write_terminal_manifest(
                    target_dir=target_dir,
                    authority=authority,
                    capability=f"trades_{window_label}",
                    page_records=page_records,
                    raw_items_count=len(trades),
                    status="MALFORMED_RESPONSE",
                    error_message=err_msg,
                    now_utc=now_utc,
                )
                raise DataContractError(err_msg)

            for position, entry in enumerate(entries):
                trades.append(
                    ProbeTrade.from_dict(entry, f"trades[{len(trades)}]")
                )

            next_token = doc.get("next_page_token")

            page_records.append(
                RetrievalPageRecord(
                    page_index=page_index,
                    request_token=page_token,
                    next_page_token=next_token,
                    item_count=len(entries),
                    raw_bytes_sha256=page_sha256,
                    page_file=page_filename,
                    rate_limit_headers=rate_limits,
                    retrieved_at_utc=now_utc.isoformat(),
                )
            )

            if not next_token:
                break

            if next_token in seen_tokens:
                err_msg = f"RI01_PROBE_REPEATED_PAGE_TOKEN: loop detected on token {next_token}."
                self._write_terminal_manifest(
                    target_dir=target_dir,
                    authority=authority,
                    capability=f"trades_{window_label}",
                    page_records=page_records,
                    raw_items_count=len(trades),
                    status="MALFORMED_RESPONSE",
                    error_message=err_msg,
                    now_utc=now_utc,
                )
                raise DataContractError(err_msg)
            seen_tokens.add(next_token)
            page_token = next_token
            page_index += 1

        chain_digest = ordered_page_chain_digest(page_records)
        manifest = RetrievalRunManifest(
            schema_version="1.1",
            run_id=f"RUN_{authority.session.isoformat()}_trades_{window_label}",
            consumer_id="ri01",
            operation=f"fetch_trades_{window_label}",
            subject_metadata={
                "symbol": PROBE_SYMBOL,
                "session": authority.session.isoformat(),
                "capability": "trades",
                "window": window_label,
                "start": window_start_utc.isoformat(),
                "end": window_end_utc.isoformat(),
            },
            runtime_sha=authority.runtime_sha,
            authority_ref=authority.authority_id,
            authority_sha256=authority.authority_sha256,
            page_records=tuple(page_records),
            page_chain_sha256=chain_digest,
            item_count=len(trades),
            operation_count=len(page_records),
            status="RETRIEVED",
            error_message=None,
            created_at_utc=now_utc.isoformat(),
        )
        manifest.write_immutable(target_dir / "manifest.json")

        qual_id = f"QUAL_{authority.session.isoformat()}_trades_{window_label}"
        qual_record = RI01QualificationRecord(
            qualification_id=qual_id,
            session=authority.session.isoformat(),
            symbol=PROBE_SYMBOL,
            capability=f"trades_{window_label}",
            status="QUALIFIED",
            retrieval_run_id=manifest.run_id,
            retrieval_manifest_sha256=manifest.manifest_sha256(),
            authority_sha256=authority.authority_sha256,
            raw_item_count=len(trades),
            qualified_item_count=len(trades),
            expected_item_count=len(trades),
            evaluated_at_utc=now_utc.isoformat(),
            error_message=None,
        )
        qual_record.write_immutable(target_dir / "qualification.json")
        self.last_qualification_record = qual_record

        return manifest, trades


def _validate_scope(
    sessions: Sequence[date], capabilities: Sequence[str], calendar: NyseCa1Calendar
) -> None:
    if not sessions:
        raise DataContractError("RI01_PROBE_NO_SESSIONS.")
    for session in sessions:
        if session >= HOLDOUT_START:
            raise DataContractError(
                f"RI01_PROBE_HOLDOUT_FORBIDDEN: {session.isoformat()} is in the "
                "sealed 2023-2026 holdout."
            )
        if session not in ALLOWLISTED_SESSIONS:
            raise DataContractError(
                f"RI01_PROBE_SESSION_NOT_ALLOWLISTED: {session.isoformat()}."
            )
        if not calendar.is_trading_session(session):
            raise DataContractError(
                f"RI01_PROBE_NON_SESSION: {session.isoformat()}."
            )
    for capability in capabilities:
        if capability not in CAPABILITIES:
            raise DataContractError(
                f"RI01_PROBE_UNKNOWN_CAPABILITY: {capability}."
            )


def compare_stability(first_sha256: str, second_sha256: str) -> str:
    """Compare two evidence digests (pure; used by scheduled revisits)."""
    if not first_sha256 or not second_sha256:
        raise DataContractError("RI01_STABILITY_EMPTY_DIGEST.")
    return "STABLE" if first_sha256 == second_sha256 else "DIFFERENT"


def main(
    argv: List[str] | None = None,
    _transport: Optional[httpx.BaseTransport] = None,
    _now_utc: Optional[datetime] = None,
    _authority: Optional[RI01ProbeAuthority] = None,
    _runtime_sha: Optional[str] = None,
    _credential_provider: Optional[EnvAlpacaCredentialProvider] = None,
) -> int:
    parser = argparse.ArgumentParser(description="RI-01 provider probe R1 (bounded, zero-outcome).")
    parser.add_argument("--execute-network", action="store_true", default=False)
    parser.add_argument("--authority-file", default="")
    parser.add_argument("--session", action="append", default=[])
    parser.add_argument("--capability", action="append", default=[])
    args = parser.parse_args(argv)

    calendar = NyseCa1Calendar()

    if not args.execute_network:
        # Dry-run mode: validates scope and bounds with ZERO network requests
        try:
            sessions = [date.fromisoformat(str(raw)) for raw in args.session] or [ALLOWLISTED_SESSIONS[0]]
        except (ValueError, TypeError) as exc:
            raise DataContractError(f"RI01_PROBE_BAD_SESSION: {exc}.") from exc
        capabilities = list(args.capability) or ["bars"]
        _validate_scope(sessions, capabilities, calendar)

        print("RI01-PROBE-DRY-RUN: zero network. Scope validated.")
        print(f"SYMBOL = {PROBE_SYMBOL}")
        for s in sessions:
            print(f"SESSION = {s.isoformat()}")
        for c in capabilities:
            print(f"CAPABILITY = {c}")
        print("NETWORK_REQUESTS = 0")
        return 0

    # Live execution requested: require explicit authority
    current_sha = _runtime_sha or get_current_runtime_sha()
    now_utc = _now_utc or datetime.now(timezone.utc)

    authority = _authority
    if authority is None:
        if not args.authority_file:
            raise DataContractError(
                "RI01_PROBE_AUTHORITY_REQUIRED: live probe requires explicit RI01ProbeAuthority."
            )
        authority_path = Path(args.authority_file)
        if not authority_path.is_file():
            raise DataContractError(f"RI01_PROBE_AUTHORITY_FILE_NOT_FOUND: {authority_path}.")
        try:
            doc = json.loads(authority_path.read_text(encoding="utf-8"))
            authority = RI01ProbeAuthority.from_dict(doc)
        except Exception as exc:
            raise DataContractError(f"RI01_PROBE_AUTHORITY_LOAD_FAILED: {exc}.") from exc

    authority.validate(now_utc, current_sha, calendar)

    client = RI01ProbeClient(
        credential_provider=_credential_provider, transport=_transport
    )

    if authority.capability == "bars":
        manifest, bars = client.fetch_bars(authority, calendar, now_utc)
        print(
            f"BARS {authority.session.isoformat()}: {len(bars)} bars, "
            f"pages={len(manifest.page_records)}, chain_sha256={manifest.page_chain_sha256}"
        )
    elif authority.capability == "trades":
        bounds = calendar.get_session(authority.session)
        if bounds.open_utc is None or bounds.close_utc is None:
            raise DataContractError(f"RI01_SESSION_BOUNDS_MISSING: {authority.session.isoformat()}.")
        for label, anchor in (
            ("open", bounds.open_utc.astimezone(timezone.utc)),
            ("close", bounds.close_utc.astimezone(timezone.utc)),
        ):
            window_start = anchor - timedelta(minutes=5)
            window_end = anchor + timedelta(minutes=5)
            manifest, trades = client.fetch_trades_window(
                window_start, window_end, label, authority, now_utc
            )
            print(
                f"TRADES {authority.session.isoformat()}/{label}: {len(trades)} trades, "
                f"pages={len(manifest.page_records)}, chain_sha256={manifest.page_chain_sha256}"
            )

    print(f"NETWORK_REQUESTS_ISSUED = {client.requests_issued}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
