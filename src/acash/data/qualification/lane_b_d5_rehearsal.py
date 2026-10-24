"""D5 dataset sealing and real-input admission gate (unissued by default).

The default rehearsal is synthetic. Real input must pass an explicit authority,
raw-page, calendar, corporate-action and evidence-level admission gate. This
module does NOT issue Lane A/B authority, acquire market data or authorize
trading; it composes the canonical HYP_009 qualification/accounting checks with
the canonical manifest hashing helpers and fails closed on unproven input.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
import hashlib
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence

from acash.core.domain.exceptions import DataContractError, DomainValidationError
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.calendar.nyse_ca1 import NyseCa1Calendar
from acash.data.qualification.daily_models import DailyBar
from acash.data.qualification.lane_a_d3_approval import verify_ed25519_signature
from acash.execution.signing import Ed25519Signer
from acash.data.qualification.lane_a_rehearsal import (
    bar_date,
    expected_session_dates,
    parse_bars_page,
)
from acash.data.qualification.manifest import (
    compute_framed_composite_sha256,
    compute_page_sha256,
)
from acash.research.hyp_009.qualification import (
    qualify_bar_series,
    qualify_dividends,
    require_no_unbound_splits,
)

ALLOWED_D5_SYMBOLS: tuple[str, ...] = ("BND", "BIL", "GLD", "VOO")
EXCLUDED_D5_SYMBOLS: frozenset[str] = frozenset({"GLDM"})
ALLOWED_D5_FEEDS: frozenset[str] = frozenset({"iex", "sip"})
ALLOWED_D5_TIMEFRAMES: frozenset[str] = frozenset({"1Day"})
ALLOWED_D5_ADJUSTMENTS: frozenset[str] = frozenset({"raw"})
ALLOWED_D5_CURRENCIES: frozenset[str] = frozenset({"USD"})
CONFIRMED_CANDIDATE: str = "SOURCE_CONFIRMED_CANDIDATE"
DATASET_SCHEMA: str = "ACASH_D5_SEALED_DATASET_V1"
SYNTHETIC_LABEL: str = "SYNTHETIC_FIXTURE_NOT_MARKET_HISTORY"
D5_EVIDENCE_ENVELOPE_DOMAIN: bytes = b"ACASH-D5-REAL-INPUT-ADMISSION/v1"
D5_EVIDENCE_SCOPE_SCHEMA: str = "ACASH_D5_EVIDENCE_SCOPE_V1"
D5_ADMISSION_RECORD_DOMAIN: bytes = b"ACASH-D5-INDEPENDENT-ADMISSION/v1"


class D5OfflineVerdict(str, Enum):
    READY = "D5_OFFLINE_PIPELINE_READY"
    PARTIAL = "D5_OFFLINE_PIPELINE_PARTIAL"
    BLOCKED = "D5_OFFLINE_PIPELINE_BLOCKED"


class DatasetOrigin(str, Enum):
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"
    REAL_CANDIDATE = "REAL_CANDIDATE"
    REAL_ADMITTED = "REAL_ADMITTED"


class D5EvidenceLevel(str, Enum):
    SYNTHETIC_PIPELINE_PROOF = "SYNTHETIC_PIPELINE_PROOF"
    SOURCE_VERIFIED_CANDIDATE = "SOURCE_VERIFIED_CANDIDATE"
    RETROSPECTIVE_QUALITY_QUALIFIED = "RETROSPECTIVE_QUALITY_QUALIFIED"
    PIT_EVIDENCE_QUALIFIED = "PIT_EVIDENCE_QUALIFIED"
    FULL_DATASET_ADMITTED = "FULL_DATASET_ADMITTED"


@dataclass(frozen=True)
class D5DividendRecord:
    symbol: str
    ex_date: date
    record_date: date
    payable_date: date
    amount_per_share: Decimal
    confirmation_status: str
    source_row_ref: str = ""
    pit_vintage_known: bool = False
    currency: str = "USD"


@dataclass(frozen=True)
class D5RehearsalSpec:
    origin: DatasetOrigin
    universe: tuple[str, ...]
    scope_start: date
    scope_end: date
    feed: str
    timeframe: str
    adjustment: str
    authority_ref: str
    expected_sessions: tuple[date, ...]
    split_bars: Mapping[str, Sequence[DailyBar]]
    raw_bars: Mapping[str, Sequence[DailyBar]]
    dividends: Sequence[D5DividendRecord] = ()
    expected_ex_dates: Mapping[str, tuple[date, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class D5RehearsalResult:
    verdict: D5OfflineVerdict
    checks: Mapping[str, bool]
    blockers: tuple[str, ...]
    manifest: Mapping[str, Any]
    dataset_bytes: bytes | None = None
    dataset_sha256: str | None = None
    composite_sha256: str | None = None


class D5AuthorityStatus(str, Enum):
    UNISSUED = "UNISSUED"
    ISSUED = "ISSUED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class D5AuthorityProvenance(str, Enum):
    OPERATOR_ISSUED = "OPERATOR_ISSUED"
    TEST_FIXTURE = "TEST_FIXTURE"


class D5InputOrigin(str, Enum):
    OPERATOR_ACQUISITION = "OPERATOR_ACQUISITION"
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"


class D5AdmissionVerdict(str, Enum):
    ADMITTED = "D5_REAL_INPUT_ADMITTED"
    INDEPENDENT_ADMISSION_REQUIRED = (
        "D5_EVIDENCE_VERIFIED_INDEPENDENT_ADMISSION_REQUIRED"
    )
    RETROSPECTIVE_ADMITTED = "D5_RETROSPECTIVE_RESEARCH_ADMITTED"
    RETROSPECTIVE_ONLY = "D5_RETROSPECTIVE_QUALITY_QUALIFIED"
    SYNTHETIC_ONLY = "D5_SYNTHETIC_PIPELINE_PROOF_ONLY"
    BLOCKED = "D5_REAL_INPUT_ADMISSION_BLOCKED"


@dataclass(frozen=True)
class D5AdmissionAuthority:
    """Exact, versioned acquisition authority bound to a real-input bundle.

    Structural validation proves only that the fields are internally
    consistent. It is NOT proof that a human issued the referenced approval;
    that binding is out-of-band evidence, exactly as in Lane A.
    """

    status: D5AuthorityStatus
    provenance: D5AuthorityProvenance
    authority_ref: str
    provider: str
    feed: str
    timeframe: str
    symbols: tuple[str, ...]
    start_date: date
    end_date: date
    adjustments: tuple[str, ...]
    max_http_requests: int
    max_observed_bytes: int
    issued_at_utc: datetime
    expires_at_utc: datetime
    approval_reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.status, D5AuthorityStatus):
            raise DataContractError("D5_AUTHORITY_BAD_STATUS.")
        if not isinstance(self.provenance, D5AuthorityProvenance):
            raise DataContractError("D5_AUTHORITY_BAD_PROVENANCE.")
        if not self.authority_ref.strip():
            raise DataContractError("D5_AUTHORITY_EMPTY_REF.")
        if not self.approval_reference.strip():
            raise DataContractError("D5_AUTHORITY_EMPTY_APPROVAL_REF.")
        if self.provider != "ALPACA":
            raise DataContractError(
                f"D5_AUTHORITY_UNAPPROVED_PROVIDER: {self.provider!r}."
            )
        if self.feed not in ALLOWED_D5_FEEDS:
            raise DataContractError(
                f"D5_AUTHORITY_UNAPPROVED_FEED: {self.feed!r}."
            )
        if self.timeframe not in ALLOWED_D5_TIMEFRAMES:
            raise DataContractError(
                f"D5_AUTHORITY_UNAPPROVED_TIMEFRAME: {self.timeframe!r}."
            )
        if not self.symbols:
            raise DataContractError("D5_AUTHORITY_EMPTY_UNIVERSE.")
        if self.symbols != tuple(sorted(set(self.symbols))):
            raise DataContractError("D5_AUTHORITY_UNIVERSE_NOT_SORTED_UNIQUE.")
        if set(self.symbols) & EXCLUDED_D5_SYMBOLS:
            raise DataContractError("D5_AUTHORITY_EXCLUDED_SYMBOL.")
        if not set(self.symbols) <= set(ALLOWED_D5_SYMBOLS):
            raise DataContractError("D5_AUTHORITY_UNAPPROVED_UNIVERSE.")
        if self.start_date > self.end_date:
            raise DataContractError("D5_AUTHORITY_SCOPE_INVERTED.")
        if self.adjustments != ("raw", "split"):
            raise DataContractError(
                "D5_AUTHORITY_ADJUSTMENTS_MUST_BE_RAW_AND_SPLIT."
            )
        for label, value in (
            ("max_http_requests", self.max_http_requests),
            ("max_observed_bytes", self.max_observed_bytes),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise DataContractError(f"D5_AUTHORITY_BAD_{label.upper()}.")
        for label, moment in (
            ("issued_at_utc", self.issued_at_utc),
            ("expires_at_utc", self.expires_at_utc),
        ):
            if moment.tzinfo is None:
                raise DataContractError(
                    f"D5_AUTHORITY_NAIVE_TIME: {label} must be timezone-aware."
                )
        if self.issued_at_utc > self.expires_at_utc:
            raise DataContractError("D5_AUTHORITY_WINDOW_INVERTED.")

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "provenance": self.provenance.value,
            "authority_ref": self.authority_ref,
            "provider": self.provider,
            "feed": self.feed,
            "timeframe": self.timeframe,
            "symbols": list(self.symbols),
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "adjustments": list(self.adjustments),
            "max_http_requests": self.max_http_requests,
            "max_observed_bytes": self.max_observed_bytes,
            "issued_at_utc": self.issued_at_utc.astimezone(timezone.utc).isoformat(),
            "expires_at_utc": self.expires_at_utc.astimezone(timezone.utc).isoformat(),
            "approval_reference": self.approval_reference,
        }

    def digest(self) -> str:
        canonical = CanonicalConfigSerializer.to_canonical_json(
            self.canonical_payload()
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class D5EvidenceTrustRoot(Protocol):
    """Verifier seam for the acquisition evidence envelope.

    A caller supplies this object, so it is never an admission authority:
    passing it proves only that the envelope verified under the caller's
    chosen keys. Real admission additionally requires a
    ``D5IndependentAdmissionRecord`` verified against
    ``D5_ADMISSION_TRUST_ANCHORS``.
    """

    def verify_signature(
        self,
        *,
        key_id: str,
        message: bytes,
        signature_b64: str,
        now_utc: str,
        valid_from_utc: str,
        valid_until_utc: str,
    ) -> None: ...


def _is_sha256_hex(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _parse_aware_utc(value: str, context: str) -> datetime:
    try:
        moment = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise DataContractError(
            f"D5_EVIDENCE_ENVELOPE_MALFORMED_TIME: {context}: {value!r}."
        ) from exc
    if moment.tzinfo is None:
        raise DataContractError(
            f"D5_EVIDENCE_ENVELOPE_NAIVE_TIME: {context} must be timezone-aware."
        )
    return moment.astimezone(timezone.utc)


@dataclass(frozen=True)
class D5EvidenceEnvelope:
    """Signed authority and bundle-scope attestation for D5 admission.

    This is a distinct message schema verified by the existing Lane A
    Ed25519 trust-root primitive. A D5 authority field named ``ISSUED`` or
    ``OPERATOR_ISSUED`` is structural only; it becomes authenticated evidence
    only when this envelope verifies against an explicitly supplied trust
    root and its scope digest equals the recomputed bundle scope.

    A verified envelope never sets ``real_data_admitted`` by itself; that
    requires a separately signed, anchored ``D5IndependentAdmissionRecord``.
    """

    key_id: str
    approval_ref: str
    authority_sha256: str
    evidence_scope_sha256: str
    valid_from_utc: str
    valid_until_utc: str
    max_http_requests: int
    max_observed_bytes: int
    signature_b64: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.key_id, str) or not self.key_id.strip():
            raise DataContractError("D5_EVIDENCE_ENVELOPE_EMPTY_KEY_ID.")
        if not isinstance(self.approval_ref, str) or not self.approval_ref.strip():
            raise DataContractError("D5_EVIDENCE_ENVELOPE_EMPTY_APPROVAL_REF.")
        if not _is_sha256_hex(self.authority_sha256):
            raise DataContractError("D5_EVIDENCE_ENVELOPE_BAD_AUTHORITY_SHA256.")
        if not _is_sha256_hex(self.evidence_scope_sha256):
            raise DataContractError("D5_EVIDENCE_ENVELOPE_BAD_SCOPE_SHA256.")
        start = _parse_aware_utc(self.valid_from_utc, "valid_from_utc")
        end = _parse_aware_utc(self.valid_until_utc, "valid_until_utc")
        if start >= end:
            raise DataContractError("D5_EVIDENCE_ENVELOPE_EMPTY_WINDOW.")
        for label, value in (
            ("max_http_requests", self.max_http_requests),
            ("max_observed_bytes", self.max_observed_bytes),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise DataContractError(
                    f"D5_EVIDENCE_ENVELOPE_BAD_{label.upper()}."
                )

    def canonical_message_bytes(self) -> bytes:
        document = {
            "domain": D5_EVIDENCE_ENVELOPE_DOMAIN.decode("ascii"),
            "key_id": self.key_id,
            "approval_ref": self.approval_ref,
            "authority_sha256": self.authority_sha256,
            "evidence_scope_sha256": self.evidence_scope_sha256,
            "valid_from_utc": self.valid_from_utc,
            "valid_until_utc": self.valid_until_utc,
            "max_http_requests": self.max_http_requests,
            "max_observed_bytes": self.max_observed_bytes,
        }
        return D5_EVIDENCE_ENVELOPE_DOMAIN + b"." + (
            CanonicalConfigSerializer.to_canonical_json(document).encode("utf-8")
        )


def sign_d5_evidence_envelope(
    envelope: D5EvidenceEnvelope, private_key_b64: str
) -> D5EvidenceEnvelope:
    """Attach an Ed25519 signature using ephemeral test material (offline)."""
    signature = Ed25519Signer.sign(private_key_b64, envelope.canonical_message_bytes())
    return replace(envelope, signature_b64=signature)


# Public keys of ratified dataset-admission authorities (key_id -> raw Ed25519
# public key, base64). Empty until a production trust root is provisioned out of
# band and added by a reviewed change; real admission is unreachable until then.
# Revocation is removal from this mapping.
D5_ADMISSION_TRUST_ANCHORS: Mapping[str, str] = MappingProxyType({})


class D5AdmissionKind(str, Enum):
    RETROSPECTIVE_RESEARCH = "RETROSPECTIVE_RESEARCH_ADMITTED"
    PIT_RESEARCH = "PIT_RESEARCH_ADMITTED"


@dataclass(frozen=True)
class D5IndependentAdmissionRecord:
    """Dataset-admission decision signed by an authority independent of acquisition.

    The record binds one evidence scope digest and one admission kind. The
    scope digest covers the claimed level and PIT fields, so a retrospective
    record cannot be reused for a PIT claim by editing metadata.
    """

    admission_ref: str
    kind: D5AdmissionKind
    evidence_scope_sha256: str
    acquisition_key_id: str
    admitter_key_id: str
    admitted_at_utc: str
    signature_b64: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.kind, D5AdmissionKind):
            raise DataContractError("D5_ADMISSION_RECORD_BAD_KIND.")
        for label, value in (
            ("admission_ref", self.admission_ref),
            ("acquisition_key_id", self.acquisition_key_id),
            ("admitter_key_id", self.admitter_key_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise DataContractError(f"D5_ADMISSION_RECORD_EMPTY_{label.upper()}.")
        if not _is_sha256_hex(self.evidence_scope_sha256):
            raise DataContractError("D5_ADMISSION_RECORD_BAD_SCOPE_SHA256.")
        if self.admitter_key_id == self.acquisition_key_id:
            raise DataContractError(
                "D5_ADMISSION_NOT_INDEPENDENT: admitter key equals acquisition key."
            )
        _parse_aware_utc(self.admitted_at_utc, "admitted_at_utc")

    def canonical_message_bytes(self) -> bytes:
        document = {
            "domain": D5_ADMISSION_RECORD_DOMAIN.decode("ascii"),
            "admission_ref": self.admission_ref,
            "kind": self.kind.value,
            "evidence_scope_sha256": self.evidence_scope_sha256,
            "acquisition_key_id": self.acquisition_key_id,
            "admitter_key_id": self.admitter_key_id,
            "admitted_at_utc": self.admitted_at_utc,
        }
        return D5_ADMISSION_RECORD_DOMAIN + b"." + (
            CanonicalConfigSerializer.to_canonical_json(document).encode("utf-8")
        )


def sign_d5_admission_record(
    record: D5IndependentAdmissionRecord, private_key_b64: str
) -> D5IndependentAdmissionRecord:
    """Attach an Ed25519 signature using ephemeral test material (offline)."""
    signature = Ed25519Signer.sign(private_key_b64, record.canonical_message_bytes())
    return replace(record, signature_b64=signature)


@dataclass(frozen=True)
class D5RawPage:
    """One immutable raw response page bound to a frozen request identity."""

    adjustment: str
    page_index: int
    page_token: str | None
    next_page_token: str | None
    request_sha256: str
    content_sha256: str
    raw_bytes: bytes
    status: str = "RETRIEVED"

    def __post_init__(self) -> None:
        if self.adjustment not in ("raw", "split"):
            raise DataContractError(
                f"D5_PAGE_BAD_ADJUSTMENT: {self.adjustment!r}."
            )
        if (
            isinstance(self.page_index, bool)
            or not isinstance(self.page_index, int)
            or self.page_index < 0
        ):
            raise DataContractError("D5_PAGE_BAD_INDEX.")
        for label, token in (
            ("page_token", self.page_token),
            ("next_page_token", self.next_page_token),
        ):
            if token is not None and (not isinstance(token, str) or not token):
                raise DataContractError(f"D5_PAGE_BAD_{label.upper()}.")
        for label, digest in (
            ("request_sha256", self.request_sha256),
            ("content_sha256", self.content_sha256),
        ):
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise DataContractError(f"D5_PAGE_BAD_{label.upper()}.")
        if not isinstance(self.raw_bytes, bytes):
            raise DataContractError("D5_PAGE_RAW_BYTES_NOT_BYTES.")
        if not self.status.strip():
            raise DataContractError("D5_PAGE_EMPTY_STATUS.")


@dataclass(frozen=True)
class D5RealInputBundle:
    """Raw real-input evidence offered to independent D5 admission."""

    authority: D5AdmissionAuthority
    origin: D5InputOrigin
    pages: tuple[D5RawPage, ...]
    dividends: tuple[D5DividendRecord, ...]
    expected_ex_dates: Mapping[str, tuple[date, ...]]
    claimed_level: D5EvidenceLevel
    pit_vintage_known: bool = False
    pit_evidence_ref: str = ""
    pit_evidence_sha256: str = ""
    expected_dividends: tuple[D5DividendRecord, ...] | None = None
    evidence_envelope: D5EvidenceEnvelope | None = None
    admission_record: D5IndependentAdmissionRecord | None = None

    def evidence_scope_sha256(self) -> str:
        """Canonical digest of every offered evidence field.

        The envelope signs this value. Any change to the authority, pages,
        dividends, PIT reference, expected events, origin, or claimed level
        changes the digest and invalidates a previously signed envelope.
        """
        ordered_pages = tuple(
            sorted(self.pages, key=lambda page: (page.adjustment, page.page_index))
        )
        expected_ex_dates = {
            symbol: [day.isoformat() for day in days]
            for symbol, days in sorted(self.expected_ex_dates.items())
        }
        expected_dividends = (
            None
            if self.expected_dividends is None
            else [list(row) for row in _dividend_fingerprint(self.expected_dividends)]
        )
        return _sha256_json(
            {
                "schema": D5_EVIDENCE_SCOPE_SCHEMA,
                "authority_sha256": self.authority.digest(),
                "origin": self.origin.value,
                "claimed_level": self.claimed_level.value,
                "pit_vintage_known": self.pit_vintage_known,
                "pit_evidence_ref": self.pit_evidence_ref,
                "pit_evidence_sha256": self.pit_evidence_sha256,
                "pages": [
                    {
                        "adjustment": page.adjustment,
                        "page_index": page.page_index,
                        "page_token": page.page_token,
                        "next_page_token": page.next_page_token,
                        "request_sha256": page.request_sha256,
                        "content_sha256": page.content_sha256,
                        "status": page.status,
                    }
                    for page in ordered_pages
                ],
                "dividends": [list(row) for row in _dividend_fingerprint(self.dividends)],
                "expected_ex_dates": expected_ex_dates,
                "expected_dividends": expected_dividends,
            }
        )


@dataclass(frozen=True)
class D5AdmissionResult:
    verdict: D5AdmissionVerdict
    admitted_level: D5EvidenceLevel | None
    claimed_level: D5EvidenceLevel
    checks: Mapping[str, bool]
    blockers: tuple[str, ...]
    manifest: Mapping[str, Any]
    dataset_bytes: bytes | None = None
    dataset_sha256: str | None = None
    composite_sha256: str | None = None


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DataContractError(message)


def _identity(spec: D5RehearsalSpec) -> dict[str, Any]:
    return {
        "symbols": list(spec.universe),
        "timeframe": spec.timeframe,
        "scope_start": spec.scope_start.isoformat(),
        "scope_end": spec.scope_end.isoformat(),
        "adjustment": spec.adjustment,
        "feed": spec.feed,
        "sort": "asc",
        "limit": 1000,
        "currency": "USD",
    }


def _validate_identity(spec: D5RehearsalSpec) -> None:
    universe = tuple(spec.universe)
    _require(len(universe) > 0, "D5_UNIVERSE_EMPTY.")
    _require(universe == tuple(sorted(universe)), "D5_UNIVERSE_NOT_SORTED.")
    _require(len(set(universe)) == len(universe), "D5_UNIVERSE_DUPLICATE.")
    _require(
        not (set(universe) & EXCLUDED_D5_SYMBOLS),
        f"D5_EXCLUDED_SYMBOL_PRESENT: {sorted(set(universe) & EXCLUDED_D5_SYMBOLS)}.",
    )
    _require(
        set(universe) <= set(ALLOWED_D5_SYMBOLS),
        f"D5_UNAPPROVED_UNIVERSE: {sorted(set(universe) - set(ALLOWED_D5_SYMBOLS))}.",
    )
    _require(spec.scope_start <= spec.scope_end, "D5_SCOPE_INVERTED.")
    _require(spec.feed in ALLOWED_D5_FEEDS, f"D5_UNAPPROVED_FEED: {spec.feed}.")
    _require(
        spec.timeframe in ALLOWED_D5_TIMEFRAMES,
        f"D5_UNAPPROVED_TIMEFRAME: {spec.timeframe}.",
    )
    _require(
        spec.adjustment in ALLOWED_D5_ADJUSTMENTS,
        f"D5_UNAPPROVED_ADJUSTMENT: {spec.adjustment}.",
    )
    _require(bool(spec.authority_ref.strip()), "D5_MISSING_APPROVAL_LINEAGE.")


def _validate_calendar(spec: D5RehearsalSpec) -> None:
    expected = tuple(spec.expected_sessions)
    _require(len(expected) > 0, "D5_EXPECTED_SESSIONS_EMPTY.")
    _require(list(expected) == sorted(set(expected)), "D5_EXPECTED_SESSIONS_CORRUPT.")
    for symbol in spec.universe:
        split = spec.split_bars.get(symbol)
        raw = spec.raw_bars.get(symbol)
        _require(
            split is not None and raw is not None,
            f"D5_MISSING_SERIES: {symbol}.",
        )
        qualify_bar_series(list(expected), list(split or ()), list(raw or ()))
        require_no_unbound_splits(
            list(expected),
            {bar.timestamp_utc.date(): bar.close for bar in (split or ())},
            {bar.timestamp_utc.date(): bar.close for bar in (raw or ())},
        )
    for symbol in spec.split_bars:
        _require(symbol in spec.universe, f"D5_UNDECLARED_SERIES_SYMBOL: {symbol}.")


def _validate_dividends(spec: D5RehearsalSpec) -> tuple[list[dict[str, Any]], list[str]]:
    seen_amounts: dict[tuple[str, date], Decimal] = {}
    events: list[dict[str, Any]] = []
    payable_outside: list[str] = []
    for record in spec.dividends:
        _require(
            record.symbol in spec.universe,
            f"D5_DIVIDEND_UNDECLARED_SYMBOL: {record.symbol}.",
        )
        _require(
            record.symbol != "GLD",
            "D5_GLD_CASH_DIVIDEND_FORBIDDEN: GLD has NO_CASH_DISTRIBUTION_ENTITLEMENT.",
        )
        _require(
            record.symbol not in EXCLUDED_D5_SYMBOLS,
            f"D5_EXCLUDED_SYMBOL_EVENT: {record.symbol}.",
        )
        _require(
            record.currency in ALLOWED_D5_CURRENCIES,
            f"D5_UNSUPPORTED_CURRENCY: {record.currency}.",
        )
        _require(
            record.amount_per_share.is_finite() and record.amount_per_share > Decimal("0"),
            f"D5_NONPOSITIVE_OR_NONFINITE_AMOUNT: {record.symbol} {record.ex_date}.",
        )
        _require(
            record.ex_date <= record.record_date <= record.payable_date,
            f"D5_DATE_ORDER_VIOLATION: {record.symbol} {record.ex_date}.",
        )
        key = (record.symbol, record.ex_date)
        if key in seen_amounts:
            _require(
                seen_amounts[key] != record.amount_per_share,
                f"D5_DUPLICATE_EVENT: {record.symbol} {record.ex_date}.",
            )
        seen_amounts[key] = record.amount_per_share
        _require(
            spec.scope_start <= record.ex_date <= spec.scope_end,
            f"D5_EVENT_OUTSIDE_SCOPE: {record.symbol} {record.ex_date}.",
        )
        if record.payable_date > spec.scope_end:
            payable_outside.append(f"{record.symbol}:{record.ex_date.isoformat()}")
        events.append(
            {
                "symbol": record.symbol,
                "ex_date": record.ex_date.isoformat(),
                "record_date": record.record_date.isoformat(),
                "payable_date": record.payable_date.isoformat(),
                "cash_distribution": format(record.amount_per_share, "f"),
            }
        )
    for symbol in sorted({record.symbol for record in spec.dividends}):
        _require(
            symbol in spec.expected_ex_dates,
            f"D5_UNDECLARED_EVENT_COVERAGE: {symbol}.",
        )
    events.sort(
        key=lambda item: (
            str(item["symbol"]),
            str(item["ex_date"]),
            str(item["cash_distribution"]),
        )
    )
    return events, sorted(payable_outside)


def _qualify_dividend_authority(
    spec: D5RehearsalSpec, *, require_pit: bool
) -> list[str]:
    blockers: list[str] = []
    for symbol in spec.universe:
        symbol_records = [r for r in spec.dividends if r.symbol == symbol]
        for record in symbol_records:
            if record.confirmation_status != CONFIRMED_CANDIDATE:
                blockers.append(
                    f"PARTIAL_SOURCE_CONTAMINATION: {symbol} {record.ex_date} "
                    f"{record.confirmation_status}."
                )
            if not record.source_row_ref.strip():
                blockers.append(f"MISSING_SOURCE_ROW_REF: {symbol} {record.ex_date}.")
            if require_pit and not record.pit_vintage_known:
                blockers.append(f"PIT_VINTAGE_UNKNOWN: {symbol} {record.ex_date}.")
        if symbol == "GLD":
            continue
        expected = spec.expected_ex_dates.get(symbol)
        if expected is None:
            continue
        actual = {record.ex_date for record in symbol_records}
        missing = sorted(set(expected) - actual)
        extra = sorted(actual - set(expected))
        if missing:
            blockers.append(f"MISSING_EVENT_COVERAGE: {symbol} {missing}.")
        if extra:
            blockers.append(f"UNDECLARED_EVENT: {symbol} {extra}.")
    return blockers


def _validate_dividend_events(spec: D5RehearsalSpec) -> int:
    count = 0
    for symbol in spec.universe:
        records = [
            {
                "ex_date": r.ex_date.isoformat(),
                "payable_date": r.payable_date.isoformat(),
                "cash_distribution": format(r.amount_per_share, "f"),
            }
            for r in spec.dividends
            if r.symbol == symbol
        ]
        events = qualify_dividends(records, spec.scope_start, spec.scope_end)
        count += len(events)
    return count


def _dataset_payload(
    spec: D5RehearsalSpec,
    events: list[dict[str, Any]],
    payable_outside: list[str],
    *,
    evidence_level: D5EvidenceLevel,
    label: str,
    real_data_admitted: bool,
) -> dict[str, Any]:
    series: dict[str, Any] = {}
    for symbol in spec.universe:
        split = sorted(spec.split_bars.get(symbol, ()), key=lambda b: b.timestamp_utc)
        raw = sorted(spec.raw_bars.get(symbol, ()), key=lambda b: b.timestamp_utc)
        series[symbol] = {
            "split": [
                {
                    "session": bar.timestamp_utc.date().isoformat(),
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                }
                for bar in split
            ],
            "raw": [
                {
                    "session": bar.timestamp_utc.date().isoformat(),
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                }
                for bar in raw
            ],
        }
    return {
        "schema": DATASET_SCHEMA,
        "label": label,
        "origin": spec.origin.value,
        "evidence_level": evidence_level.value,
        "real_data_admitted": real_data_admitted,
        "identity": _identity(spec),
        "price_semantics": "RAW_UNADJUSTED_OHLCV",
        "time_basis": "UTC_DAILY_BAR",
        "share_basis": "PER_SHARE",
        "sessions_authority": (
            "CALLER_SUPPLIED_SYNTHETIC"
            if spec.origin is DatasetOrigin.SYNTHETIC_FIXTURE
            else "EXCHANGE_CALENDAR_AND_PROVIDER_COVERAGE_VERIFIED"
        ),
        "authority_ref": spec.authority_ref,
        "sessions": [day.isoformat() for day in spec.expected_sessions],
        "series": series,
        "dividends": events,
        "payable_outside_scope": payable_outside,
        "pit_vintage_known": all(r.pit_vintage_known for r in spec.dividends),
    }


def _seal_dataset(
    spec: D5RehearsalSpec,
    *,
    evidence_level: D5EvidenceLevel,
    label: str,
    real_data_admitted: bool,
    require_pit: bool,
    admission_bridge: bool = False,
) -> D5RehearsalResult:
    checks: dict[str, bool] = {}
    try:
        _validate_identity(spec)
        checks["request_identity"] = True
        _validate_calendar(spec)
        checks["price_calendar_alignment"] = True
        checks["no_unbound_split"] = True
        _validate_dividend_events(spec)
        events, payable_outside = _validate_dividends(spec)
        checks["dividend_events"] = True
        blockers = _qualify_dividend_authority(spec, require_pit=require_pit)
        checks["source_authority"] = not blockers
    except DataContractError as exc:
        return D5RehearsalResult(
            verdict=D5OfflineVerdict.BLOCKED,
            checks=checks,
            blockers=(str(exc),),
            manifest={"schema": DATASET_SCHEMA, "blocked": True},
        )

    if spec.origin is DatasetOrigin.REAL_CANDIDATE and not admission_bridge:
        blockers = list(blockers) + [
            "REAL_CANDIDATE_SEALING_REQUIRES_AUTHORIZED_ADMISSION"
        ]
        checks["real_admission_authorized"] = False

    if checks["source_authority"] and not blockers:
        payload = _dataset_payload(
            spec,
            events,
            payable_outside,
            evidence_level=evidence_level,
            label=label,
            real_data_admitted=real_data_admitted,
        )
        dataset_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
        dataset_sha = CanonicalConfigSerializer.compute_sha256(payload)
        page_sha = compute_page_sha256(dataset_bytes)
        composite_sha = compute_framed_composite_sha256([dataset_bytes])
        _require(page_sha == dataset_sha, "D5_PAGE_SHA_MISMATCH.")
        manifest = {
            "schema": DATASET_SCHEMA,
            "dataset_sha256": dataset_sha,
            "composite_sha256": composite_sha,
            "page_shas": [page_sha],
            "identity": _identity(spec),
            "authority_ref": spec.authority_ref,
            "session_count": len(spec.expected_sessions),
            "dividend_count": len(events),
            "payable_outside_scope": payable_outside,
            "origin": spec.origin.value,
            "label": label,
            "evidence_level": evidence_level.value,
            "real_data_admitted": real_data_admitted,
            "pit_vintage_known": all(r.pit_vintage_known for r in spec.dividends),
            "sessions_authority": (
                "CALLER_SUPPLIED_SYNTHETIC"
                if spec.origin is DatasetOrigin.SYNTHETIC_FIXTURE
                else "EXCHANGE_CALENDAR_AND_PROVIDER_COVERAGE_VERIFIED"
            ),
            "blockers": [],
        }
        checks["dataset_sealed"] = True
        return D5RehearsalResult(
            verdict=D5OfflineVerdict.READY,
            checks=checks,
            blockers=(),
            manifest=manifest,
            dataset_bytes=dataset_bytes,
            dataset_sha256=dataset_sha,
            composite_sha256=composite_sha,
        )

    return D5RehearsalResult(
        verdict=D5OfflineVerdict.PARTIAL,
        checks=checks,
        blockers=tuple(blockers),
        manifest={"schema": DATASET_SCHEMA, "sealed": False, "blockers": list(blockers)},
    )


def evaluate_d5_offline_rehearsal(spec: D5RehearsalSpec) -> D5RehearsalResult:
    """Run the synthetic rehearsal; never seal real input through this door."""
    if spec.origin is DatasetOrigin.REAL_CANDIDATE:
        return _seal_dataset(
            spec,
            evidence_level=D5EvidenceLevel.SYNTHETIC_PIPELINE_PROOF,
            label=SYNTHETIC_LABEL,
            real_data_admitted=False,
            require_pit=True,
        )
    if spec.origin is DatasetOrigin.REAL_ADMITTED:
        return D5RehearsalResult(
            verdict=D5OfflineVerdict.BLOCKED,
            checks={"real_admission_via_bridge": False},
            blockers=("REAL_ADMITTED_REQUIRES_D5_REAL_ADMISSION_BRIDGE",),
            manifest={"schema": DATASET_SCHEMA, "blocked": True},
        )
    return _seal_dataset(
        spec,
        evidence_level=D5EvidenceLevel.SYNTHETIC_PIPELINE_PROOF,
        label=SYNTHETIC_LABEL,
        real_data_admitted=False,
        require_pit=True,
    )


def _sha256_json(payload: Any) -> str:
    canonical = CanonicalConfigSerializer.to_canonical_json(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def expected_d5_request_sha256(
    authority: D5AdmissionAuthority,
    adjustment: str,
    page_token: str | None,
) -> str:
    """Canonical request identity for one admission page.

    This is a deterministic identity, not an HTTP dispatcher. A page is
    admitted only when its stored request digest equals this value.
    """
    if adjustment not in ("raw", "split"):
        raise DataContractError(f"D5_REQUEST_BAD_ADJUSTMENT: {adjustment!r}.")
    if page_token is not None and (not isinstance(page_token, str) or not page_token):
        raise DataContractError("D5_REQUEST_BAD_PAGE_TOKEN.")
    return _sha256_json(
        {
            "authority_ref": authority.authority_ref,
            "authority_sha256": authority.digest(),
            "approval_reference": authority.approval_reference,
            "provider": authority.provider,
            "feed": authority.feed,
            "timeframe": authority.timeframe,
            "symbols": list(authority.symbols),
            "start_date": authority.start_date.isoformat(),
            "end_date": authority.end_date.isoformat(),
            "adjustment": adjustment,
            "endpoint_path": "/v2/stocks/bars",
            "sort": "asc",
            "limit": 1000,
            "currency": "USD",
            "page_token": page_token,
        }
    )


def _decimal_value(value: Any, context: str) -> Decimal:
    if isinstance(value, bool):
        raise DataContractError(f"D5_BAR_NON_NUMERIC: {context}: {value!r}.")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise DataContractError(f"D5_BAR_NON_NUMERIC: {context}: {value!r}.") from exc
    if not parsed.is_finite():
        raise DataContractError(f"D5_BAR_NON_FINITE: {context}: {value!r}.")
    return parsed


def _bar_from_entry(entry: Mapping[str, Any], context: str) -> DailyBar:
    raw_time = entry.get("t")
    try:
        moment = datetime.fromisoformat(str(raw_time))
    except (TypeError, ValueError) as exc:
        raise DataContractError(
            f"D5_BAR_BAD_TIMESTAMP: {context}: {raw_time!r}."
        ) from exc
    if moment.tzinfo is None:
        raise DataContractError(
            f"D5_BAR_NAIVE_TIMESTAMP: {context}: {raw_time!r}."
        )
    return DailyBar(
        timestamp_utc=moment,
        open=_decimal_value(entry.get("o"), f"{context}.open"),
        high=_decimal_value(entry.get("h"), f"{context}.high"),
        low=_decimal_value(entry.get("l"), f"{context}.low"),
        close=_decimal_value(entry.get("c"), f"{context}.close"),
        volume=_decimal_value(entry.get("v"), f"{context}.volume"),
    )


def _validate_pages(
    bundle: D5RealInputBundle,
) -> tuple[
    dict[str, list[DailyBar]],
    dict[str, list[DailyBar]],
    list[str],
    int,
]:
    authority = bundle.authority
    pages = tuple(bundle.pages)
    if not pages:
        raise DataContractError("D5_PAGES_EMPTY.")
    if len(pages) > authority.max_http_requests:
        raise DataContractError(
            f"D5_PAGE_BUDGET_EXCEEDED: {len(pages)} > "
            f"{authority.max_http_requests}."
        )
    observed_bytes = sum(len(page.raw_bytes) for page in pages)
    if observed_bytes > authority.max_observed_bytes:
        raise DataContractError(
            f"D5_BYTE_BUDGET_EXCEEDED: {observed_bytes} > "
            f"{authority.max_observed_bytes}."
        )

    by_adjustment: dict[str, list[D5RawPage]] = {"raw": [], "split": []}
    for page in pages:
        by_adjustment[page.adjustment].append(page)

    bars: dict[str, dict[str, list[DailyBar]]] = {"raw": {}, "split": {}}
    page_shas: list[str] = []
    for adjustment in ("raw", "split"):
        sequence = sorted(by_adjustment[adjustment], key=lambda p: p.page_index)
        if not sequence:
            raise DataContractError(f"D5_MISSING_ADJUSTMENT_PAGES: {adjustment}.")
        if [page.page_index for page in sequence] != list(range(len(sequence))):
            raise DataContractError(
                f"D5_PAGE_INDEX_NOT_CONTIGUOUS: {adjustment}."
            )
        if sequence[0].page_token is not None:
            raise DataContractError(
                f"D5_FIRST_PAGE_HAS_TOKEN: {adjustment}."
            )
        seen_tokens: set[str | None] = set()
        for index, page in enumerate(sequence):
            context = f"{adjustment}/page-{page.page_index}"
            if page.status != "RETRIEVED":
                raise DataContractError(
                    f"D5_PAGE_NOT_RETRIEVED: {context}: {page.status}."
                )
            if compute_page_sha256(page.raw_bytes) != page.content_sha256:
                raise DataContractError(f"D5_PAGE_CONTENT_SHA_MISMATCH: {context}.")
            if page.request_sha256 != expected_d5_request_sha256(
                authority, adjustment, page.page_token
            ):
                raise DataContractError(f"D5_PAGE_REQUEST_SHA_MISMATCH: {context}.")
            if page.page_token in seen_tokens:
                raise DataContractError(f"D5_PAGE_TOKEN_REPLAY: {context}.")
            seen_tokens.add(page.page_token)
            if index + 1 < len(sequence):
                if page.next_page_token is None:
                    raise DataContractError(
                        f"D5_PAGE_CHAIN_TRUNCATED: {context}."
                    )
                if sequence[index + 1].page_token != page.next_page_token:
                    raise DataContractError(
                        f"D5_PAGE_TOKEN_CHAIN_BROKEN: {context}."
                    )
                if page.next_page_token in seen_tokens:
                    raise DataContractError(
                        f"D5_PAGE_TOKEN_LOOP: {context}."
                    )
            elif page.next_page_token is not None:
                raise DataContractError(
                    f"D5_PAGE_CHAIN_NOT_TERMINAL: {context}."
                )

            parsed, parsed_next = parse_bars_page(
                page.raw_bytes, authority.symbols, context
            )
            if parsed_next != page.next_page_token:
                raise DataContractError(
                    f"D5_PAGE_PARSED_TOKEN_MISMATCH: {context}."
                )
            for symbol, entries in parsed.items():
                for entry in entries:
                    entry_context = f"{context}/{symbol}"
                    session_date = bar_date(entry, entry_context)
                    if not (
                        authority.start_date <= session_date <= authority.end_date
                    ):
                        raise DataContractError(
                            f"D5_PAGE_BAR_OUTSIDE_SCOPE: {entry_context}: "
                            f"{session_date.isoformat()}."
                        )
                    bar = _bar_from_entry(entry, entry_context)
                    if bar.timestamp_utc.date() != session_date:
                        raise DataContractError(
                            f"D5_BAR_UTC_NY_DATE_MISMATCH: {entry_context}: "
                            f"UTC {bar.timestamp_utc.date().isoformat()} != "
                            f"NY {session_date.isoformat()}."
                        )
                    bars[adjustment].setdefault(symbol, []).append(bar)
            page_shas.append(page.content_sha256)

    for symbol in authority.symbols:
        if not bars["raw"].get(symbol):
            raise DataContractError(f"D5_MISSING_RAW_SERIES: {symbol}.")
        if not bars["split"].get(symbol):
            raise DataContractError(f"D5_MISSING_SPLIT_SERIES: {symbol}.")
    return bars["split"], bars["raw"], page_shas, observed_bytes


def _dividend_fingerprint(
    records: Sequence[D5DividendRecord],
) -> tuple[tuple[str, str, str, str, str, str, str, bool, str], ...]:
    return tuple(
        sorted(
            (
                record.symbol,
                record.ex_date.isoformat(),
                record.record_date.isoformat(),
                record.payable_date.isoformat(),
                format(record.amount_per_share, "f"),
                record.confirmation_status,
                record.source_row_ref,
                record.pit_vintage_known,
                record.currency,
            )
            for record in records
        )
    )


def _validate_admission_authority(
    bundle: D5RealInputBundle, now_utc: datetime
) -> None:
    authority = bundle.authority
    if not isinstance(bundle.origin, D5InputOrigin):
        raise DataContractError("D5_ADMISSION_BAD_INPUT_ORIGIN.")
    if not isinstance(bundle.claimed_level, D5EvidenceLevel):
        raise DataContractError("D5_ADMISSION_BAD_CLAIMED_LEVEL.")
    if now_utc.tzinfo is None:
        raise DataContractError("D5_ADMISSION_NAIVE_NOW_UTC.")
    now = now_utc.astimezone(timezone.utc)
    if authority.status is not D5AuthorityStatus.ISSUED:
        raise DataContractError(
            f"D5_AUTHORITY_NOT_ISSUED: {authority.status.value}."
        )
    if not (authority.issued_at_utc <= now <= authority.expires_at_utc):
        raise DataContractError(
            "D5_AUTHORITY_WINDOW_CLOSED: the authority is not valid at now_utc."
        )
    if bundle.origin is D5InputOrigin.OPERATOR_ACQUISITION:
        if authority.provenance is not D5AuthorityProvenance.OPERATOR_ISSUED:
            raise DataContractError(
                "D5_OPERATOR_BUNDLE_REQUIRES_OPERATOR_AUTHORITY_PROVENANCE."
            )
    elif authority.provenance is not D5AuthorityProvenance.TEST_FIXTURE:
        raise DataContractError(
            "D5_SYNTHETIC_BUNDLE_REQUIRES_TEST_FIXTURE_PROVENANCE."
        )
    if bundle.claimed_level is D5EvidenceLevel.FULL_DATASET_ADMITTED:
        raise DataContractError(
            "D5_FULL_DATASET_ADMITTED_REQUIRES_SEPARATE_ADMISSION_RECORD."
        )
    if bundle.expected_dividends is not None:
        if _dividend_fingerprint(bundle.expected_dividends) != _dividend_fingerprint(
            bundle.dividends
        ):
            raise DataContractError("D5_DIVIDEND_INPUT_DOES_NOT_MATCH_EXPECTED.")


def _verify_evidence_envelope(
    bundle: D5RealInputBundle,
    trust_root: D5EvidenceTrustRoot | None,
    now_utc: datetime,
) -> None:
    """Verify the signed acquisition evidence envelope (never confers admission)."""
    envelope = bundle.evidence_envelope
    if envelope is None:
        raise DataContractError(
            "D5_EXTERNAL_EVIDENCE_PENDING: operator bundle has no signed evidence envelope."
        )
    if trust_root is None:
        raise DataContractError(
            "D5_EXTERNAL_EVIDENCE_PENDING: no trust root supplied for envelope verification."
        )
    trust_root.verify_signature(
        key_id=envelope.key_id,
        message=envelope.canonical_message_bytes(),
        signature_b64=envelope.signature_b64,
        now_utc=now_utc.astimezone(timezone.utc).isoformat(),
        valid_from_utc=envelope.valid_from_utc,
        valid_until_utc=envelope.valid_until_utc,
    )
    authority = bundle.authority
    if envelope.authority_sha256 != authority.digest():
        raise DataContractError("D5_EVIDENCE_ENVELOPE_AUTHORITY_MISMATCH.")
    if envelope.approval_ref != authority.approval_reference:
        raise DataContractError("D5_EVIDENCE_ENVELOPE_APPROVAL_REF_MISMATCH.")
    if (envelope.max_http_requests, envelope.max_observed_bytes) != (
        authority.max_http_requests,
        authority.max_observed_bytes,
    ):
        raise DataContractError("D5_EVIDENCE_ENVELOPE_BUDGET_MISMATCH.")
    if envelope.evidence_scope_sha256 != bundle.evidence_scope_sha256():
        raise DataContractError("D5_EVIDENCE_ENVELOPE_SCOPE_MISMATCH.")


def _verify_independent_admission(
    bundle: D5RealInputBundle, now_utc: datetime
) -> D5AdmissionKind:
    """Verify the admission record against the pinned anchors, never the caller's root."""
    record = bundle.admission_record
    envelope = bundle.evidence_envelope
    if record is None or envelope is None:
        raise DataContractError("D5_ADMISSION_RECORD_MISSING.")
    expected_kind = (
        D5AdmissionKind.PIT_RESEARCH
        if bundle.claimed_level is D5EvidenceLevel.PIT_EVIDENCE_QUALIFIED
        else D5AdmissionKind.RETROSPECTIVE_RESEARCH
    )
    if record.kind is not expected_kind:
        raise DataContractError(
            f"D5_ADMISSION_KIND_MISMATCH: {record.kind.value} for "
            f"{bundle.claimed_level.value}."
        )
    if record.evidence_scope_sha256 != bundle.evidence_scope_sha256():
        raise DataContractError("D5_ADMISSION_RECORD_SCOPE_MISMATCH.")
    if record.acquisition_key_id != envelope.key_id:
        raise DataContractError("D5_ADMISSION_RECORD_ACQUISITION_KEY_MISMATCH.")
    if record.admitter_key_id == envelope.key_id:
        raise DataContractError(
            "D5_ADMISSION_NOT_INDEPENDENT: admitter key equals acquisition key."
        )
    admitted_at = _parse_aware_utc(record.admitted_at_utc, "admitted_at_utc")
    if admitted_at > now_utc.astimezone(timezone.utc):
        raise DataContractError("D5_ADMISSION_RECORD_FUTURE_DATED.")
    if admitted_at < _parse_aware_utc(envelope.valid_from_utc, "valid_from_utc"):
        raise DataContractError("D5_ADMISSION_RECORD_PREDATES_EVIDENCE.")
    public_key_b64 = D5_ADMISSION_TRUST_ANCHORS.get(record.admitter_key_id)
    if public_key_b64 is None:
        raise DataContractError(
            f"D5_ADMISSION_UNANCHORED_KEY: {record.admitter_key_id!r} is not a "
            "ratified admission authority."
        )
    verify_ed25519_signature(
        public_key_b64, record.canonical_message_bytes(), record.signature_b64
    )
    return record.kind


def evaluate_d5_real_admission(
    bundle: D5RealInputBundle,
    *,
    now_utc: datetime,
    trust_root: D5EvidenceTrustRoot | None = None,
) -> D5AdmissionResult:
    """Independently admit or refuse a real-input bundle into D5 sealing.

    Three boundaries are evaluated in order:

    A. Structural qualification: authority fields, raw pages, request
       identity, pagination, budgets, calendar, and claimed level.
    B. External evidence: an operator bundle must carry a D5 evidence
       envelope whose Ed25519 signature verifies against ``trust_root`` and
       whose signed scope digest equals the recomputed bundle scope.
    C. Admission decision: ``real_data_admitted`` is true only when a
       ``D5IndependentAdmissionRecord`` of the matching kind (retrospective
       or PIT) binds the same scope, names the envelope's acquisition key,
       is signed by a different key, and verifies against
       ``D5_ADMISSION_TRUST_ANCHORS``. ``trust_root`` is caller-supplied and
       is never consulted for this decision. Without such a record a PIT
       claim yields ``INDEPENDENT_ADMISSION_REQUIRED``.
    """
    authority = bundle.authority
    claimed = bundle.claimed_level
    checks: dict[str, bool] = {}
    base_manifest: dict[str, Any] = {
        "schema": DATASET_SCHEMA,
        "admission_schema": "ACASH_D5_REAL_INPUT_ADMISSION_V1",
        "authority_ref": authority.authority_ref,
        "authority_sha256": authority.digest(),
        "approval_reference": authority.approval_reference,
        "claimed_level": claimed.value,
        "input_origin": bundle.origin.value,
        "authority_provenance": authority.provenance.value,
        "real_data_admitted": False,
    }
    try:
        _validate_admission_authority(bundle, now_utc)
        checks["authority"] = True
        split_bars, raw_bars, page_shas, observed_bytes = _validate_pages(bundle)
        checks["raw_pages"] = True
        calendar = NyseCa1Calendar()
        sessions = tuple(
            expected_session_dates(
                authority.start_date, authority.end_date, calendar
            )
        )
        if not sessions:
            raise DataContractError("D5_EXPECTED_SESSIONS_EMPTY.")
        checks["exchange_calendar"] = True

        if bundle.origin is D5InputOrigin.SYNTHETIC_FIXTURE:
            if claimed is not D5EvidenceLevel.SYNTHETIC_PIPELINE_PROOF:
                raise DataContractError(
                    "D5_SYNTHETIC_INPUT_CANNOT_CLAIM_REAL_EVIDENCE."
                )
            level = D5EvidenceLevel.SYNTHETIC_PIPELINE_PROOF
            label = SYNTHETIC_LABEL
            real_data_admitted = False
            require_pit = True
            verdict = D5AdmissionVerdict.SYNTHETIC_ONLY
        elif claimed is D5EvidenceLevel.PIT_EVIDENCE_QUALIFIED:
            if not bundle.pit_vintage_known or not all(
                record.pit_vintage_known for record in bundle.dividends
            ):
                raise DataContractError(
                    "D5_PIT_EVIDENCE_QUALIFIED_REQUIRES_PIT_VINTAGE."
                )
            if not bundle.pit_evidence_ref.strip():
                raise DataContractError(
                    "D5_PIT_EVIDENCE_QUALIFIED_REQUIRES_EVIDENCE_REF."
                )
            if not _is_sha256_hex(bundle.pit_evidence_sha256):
                raise DataContractError(
                    "D5_PIT_EVIDENCE_QUALIFIED_REQUIRES_EVIDENCE_SHA256."
                )
            level = D5EvidenceLevel.PIT_EVIDENCE_QUALIFIED
            label = "PIT_EVIDENCE_QUALIFIED"
            real_data_admitted = True
            require_pit = True
            verdict = D5AdmissionVerdict.ADMITTED
        elif claimed is D5EvidenceLevel.RETROSPECTIVE_QUALITY_QUALIFIED:
            level = D5EvidenceLevel.RETROSPECTIVE_QUALITY_QUALIFIED
            label = "RETROSPECTIVE_QUALITY_QUALIFIED_NOT_PIT"
            real_data_admitted = False
            require_pit = False
            verdict = D5AdmissionVerdict.RETROSPECTIVE_ONLY
        else:
            raise DataContractError(
                f"D5_CLAIMED_LEVEL_NOT_SEALABLE: {claimed.value}."
            )
        checks["evidence_level"] = True

        external_evidence_verified = False
        admission_kind: D5AdmissionKind | None = None
        if bundle.origin is D5InputOrigin.OPERATOR_ACQUISITION:
            _verify_evidence_envelope(bundle, trust_root, now_utc)
            external_evidence_verified = True
            checks["external_evidence_signature"] = True
            if bundle.admission_record is not None:
                admission_kind = _verify_independent_admission(bundle, now_utc)
                checks["independent_admission"] = True
            if admission_kind is D5AdmissionKind.RETROSPECTIVE_RESEARCH:
                real_data_admitted = True
                verdict = D5AdmissionVerdict.RETROSPECTIVE_ADMITTED
            elif admission_kind is None and real_data_admitted:
                level = D5EvidenceLevel.RETROSPECTIVE_QUALITY_QUALIFIED
                label = "PIT_CLAIM_SIGNED_INDEPENDENT_ADMISSION_REQUIRED"
                real_data_admitted = False
                verdict = D5AdmissionVerdict.INDEPENDENT_ADMISSION_REQUIRED

        if bundle.origin is D5InputOrigin.SYNTHETIC_FIXTURE:
            dataset_origin = DatasetOrigin.SYNTHETIC_FIXTURE
        elif real_data_admitted:
            dataset_origin = DatasetOrigin.REAL_ADMITTED
        else:
            dataset_origin = DatasetOrigin.REAL_CANDIDATE

        spec = D5RehearsalSpec(
            origin=dataset_origin,
            universe=authority.symbols,
            scope_start=authority.start_date,
            scope_end=authority.end_date,
            feed=authority.feed,
            timeframe=authority.timeframe,
            adjustment="raw",
            authority_ref=f"{authority.authority_ref}#sha256={authority.digest()}",
            expected_sessions=sessions,
            split_bars=split_bars,
            raw_bars=raw_bars,
            dividends=bundle.dividends,
            expected_ex_dates={
                key: tuple(value) for key, value in bundle.expected_ex_dates.items()
            },
        )
        d5 = _seal_dataset(
            spec,
            evidence_level=level,
            label=label,
            real_data_admitted=real_data_admitted,
            require_pit=require_pit,
            admission_bridge=external_evidence_verified,
        )
    except (
        DataContractError,
        DomainValidationError,
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        return D5AdmissionResult(
            verdict=D5AdmissionVerdict.BLOCKED,
            admitted_level=None,
            claimed_level=claimed,
            checks=checks,
            blockers=(str(exc),),
            manifest={**base_manifest, "admission_blocked": True},
        )

    if d5.verdict is not D5OfflineVerdict.READY:
        return D5AdmissionResult(
            verdict=D5AdmissionVerdict.BLOCKED,
            admitted_level=None,
            claimed_level=claimed,
            checks={**checks, **d5.checks},
            blockers=d5.blockers,
            manifest={
                **base_manifest,
                "admission_blocked": True,
                "d5_manifest": dict(d5.manifest),
            },
        )

    manifest = {
        **dict(d5.manifest),
        "admission": {
            **base_manifest,
            "admitted_level": level.value,
            "real_data_admitted": real_data_admitted,
            "page_count": len(bundle.pages),
            "page_shas": page_shas,
            "observed_bytes": observed_bytes,
            "pit_vintage_known": all(
                record.pit_vintage_known for record in bundle.dividends
            ),
            "pit_evidence_ref": bundle.pit_evidence_ref,
            "pit_evidence_sha256": bundle.pit_evidence_sha256,
            "external_evidence_verified": external_evidence_verified,
            "admission_kind": None if admission_kind is None else admission_kind.value,
            "limitations": (
                (
                    ["NOT_POINT_IN_TIME", "CORPORATE_ACTION_VINTAGE_UNPROVEN"]
                    if level is D5EvidenceLevel.RETROSPECTIVE_QUALITY_QUALIFIED
                    else []
                )
                + (
                    ["INDEPENDENT_ADMISSION_REQUIRED", "NO_ANCHORED_ADMISSION_RECORD"]
                    if not real_data_admitted
                    and bundle.origin is D5InputOrigin.OPERATOR_ACQUISITION
                    else []
                )
            ),
        },
    }
    checks["dataset_sealed"] = True
    return D5AdmissionResult(
        verdict=verdict,
        admitted_level=level,
        claimed_level=claimed,
        checks=checks,
        blockers=(),
        manifest=manifest,
        dataset_bytes=d5.dataset_bytes,
        dataset_sha256=d5.dataset_sha256,
        composite_sha256=d5.composite_sha256,
    )


def verify_sealed_dataset(
    dataset_bytes: bytes,
    expected_sha256: str,
    expected_composite_sha256: str,
) -> None:
    """Fail closed on any byte-level or framing tamper."""
    actual_sha = compute_page_sha256(dataset_bytes)
    _require(actual_sha == expected_sha256, "D5_TAMPER_DETECTED_DATASET_SHA.")
    actual_composite = compute_framed_composite_sha256([dataset_bytes])
    _require(
        actual_composite == expected_composite_sha256,
        "D5_TAMPER_DETECTED_COMPOSITE_SHA.",
    )


__all__ = [
    "ALLOWED_D5_SYMBOLS",
    "EXCLUDED_D5_SYMBOLS",
    "D5_ADMISSION_TRUST_ANCHORS",
    "D5AdmissionAuthority",
    "D5AdmissionKind",
    "D5AdmissionResult",
    "D5AdmissionVerdict",
    "D5AuthorityProvenance",
    "D5AuthorityStatus",
    "D5DividendRecord",
    "D5EvidenceEnvelope",
    "D5EvidenceLevel",
    "D5EvidenceTrustRoot",
    "D5IndependentAdmissionRecord",
    "D5InputOrigin",
    "D5OfflineVerdict",
    "D5RawPage",
    "D5RealInputBundle",
    "D5RehearsalResult",
    "D5RehearsalSpec",
    "DatasetOrigin",
    "evaluate_d5_offline_rehearsal",
    "evaluate_d5_real_admission",
    "expected_d5_request_sha256",
    "sign_d5_admission_record",
    "sign_d5_evidence_envelope",
    "verify_sealed_dataset",
]
