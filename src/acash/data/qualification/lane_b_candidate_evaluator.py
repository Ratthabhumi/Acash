"""Lane B Corporate-Action Candidate Qualification Evaluator (Offline Rehearsal).

Evaluates candidate ETF corporate-action panels against the fail-closed invariants
specified in docs/research/LANE_B_SPEC_OFFLINE_QUALIFICATION.md and AGENTS.md:
1. UNKNOWN-basis rejection: Records lacking authorized source binding are rejected.
2. Issuer domain binding: Source URLs must belong to authorized primary issuer domains.
3. Finite positive amounts: Decimal precision within Decimal128 bounds; no negative or zero values.
4. Date ordering: ex_date <= record_date <= payable_date.
5. Canonical duplicate handling: Identical duplicates and contradictory duplicates are rejected.
6. Dual cryptographic digests: Economic event digest vs full evidence manifest digest.
7. Truthful status: Panels containing SOURCE_PARTIAL events yield CANDIDATE_STRUCTURE_VALIDATED,
   never SOURCE_VERIFIED_CANDIDATE.
8. GLD Grantor Trust rule: GLD carries NO_CASH_DISTRIBUTION_ENTITLEMENT; cash events fail closed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple
from urllib.parse import urlparse

from acash.core.domain.exceptions import DataContractError
from acash.core.domain.types import ensure_finite_decimal
from acash.core.serialization import CanonicalConfigSerializer
from acash.data.qualification.manifest import compute_framed_composite_sha256
from acash.data.schema import validate_decimal128_bounds

LANE_B_CANDIDATE_UNIVERSE: frozenset[str] = frozenset({"VOO", "BND", "BIL", "GLD"})
ALLOWED_CURRENCIES: frozenset[str] = frozenset({"USD"})
ALLOWED_EVENT_TYPES: frozenset[str] = frozenset({"INCOME_DISTRIBUTION", "CASH_DIVIDEND"})

# Explicit confirmation vocabulary. Missing/unknown values NEVER imply confirmation.
ALLOWED_CONFIRMATION_STATUSES: frozenset[str] = frozenset({
    "SOURCE_CONFIRMED_CANDIDATE",
    "SOURCE_PARTIAL",
    "QUARANTINED",
})
DEFAULT_CONFIRMATION_STATUS: str = "SOURCE_PARTIAL"

VALID_AUTHORITY_CLASSES: frozenset[str] = frozenset({
    "ISSUER_OFFICIAL_TABLE",
    "SPONSOR_DECLARATION",
    "REGULATORY_FILING",
})

EXPECTED_FUND_IDENTITIES: Mapping[str, str] = {
    "VOO": "Vanguard Index Funds",
    "BND": "Vanguard Bond Index Funds",
    "BIL": "SPDR Series Trust",
}

AUTHORIZED_ISSUER_DOMAINS: Mapping[str, Tuple[str, ...]] = {
    "VOO": ("vanguard.com", "vanguardoffshore.com"),
    "BND": ("vanguard.com", "vanguardoffshore.com"),
    "BIL": ("ssga.com", "statestreet.com"),
    "GLD": ("spdrgoldshares.com",),
}


@dataclass(frozen=True)
class LaneBCandidateEvent:
    """Structured candidate corporate-action distribution event."""
    symbol: str
    fund_legal_identity: str
    event_type: str
    amount: Decimal
    currency: str
    ex_date: date
    record_date: date
    payable_date: date
    source_url: str
    source_document: str
    retrieval_status: str
    source_row_ref: str = ""
    publication_date: str = "UNKNOWN"
    revision_status: str = "REVISION_POLICY_UNVERIFIED"
    authority_class: str = "ISSUER_OFFICIAL_TABLE"
    confirmation_status: str = DEFAULT_CONFIRMATION_STATUS
    cusip: Optional[str] = None
    coverage_notes: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> LaneBCandidateEvent:
        """Parse from dictionary with fail-closed Decimal conversion.

        Confirmation is never inferred: a missing ``confirmation_status``
        resolves to ``SOURCE_PARTIAL`` (never confirmed), and an explicitly
        supplied but unknown status is rejected as malformed.
        """
        try:
            amt_str = str(data["amount"])
            amt = Decimal(amt_str)
        except (KeyError, InvalidOperation, ValueError) as exc:
            raise DataContractError(f"Invalid decimal amount in event: {data}") from exc

        try:
            ex_d = date.fromisoformat(str(data["ex_date"]))
            rec_d = date.fromisoformat(str(data["record_date"]))
            pay_d = date.fromisoformat(str(data["payable_date"]))
        except (KeyError, ValueError) as exc:
            raise DataContractError(f"Invalid date format in event: {data}") from exc

        raw_confirmation = data.get("confirmation_status")
        if raw_confirmation is None:
            confirmation_status = DEFAULT_CONFIRMATION_STATUS
        else:
            confirmation_status = str(raw_confirmation).strip()
            if confirmation_status not in ALLOWED_CONFIRMATION_STATUSES:
                raise DataContractError(
                    f"Malformed confirmation_status {raw_confirmation!r} for "
                    f"'{data.get('symbol')}'; allowed values are "
                    f"{sorted(ALLOWED_CONFIRMATION_STATUSES)}."
                )

        return cls(
            symbol=str(data["symbol"]).strip().upper(),
            fund_legal_identity=str(data["fund_legal_identity"]).strip(),
            event_type=str(data["event_type"]).strip(),
            amount=amt,
            currency=str(data["currency"]).strip().upper(),
            ex_date=ex_d,
            record_date=rec_d,
            payable_date=pay_d,
            source_url=str(data["source_url"]).strip(),
            source_document=str(data["source_document"]).strip(),
            retrieval_status=str(data.get("retrieval_status", "UNVERIFIED_CAPTURE_TIME")),
            source_row_ref=str(data.get("source_row_ref", "")),
            publication_date=str(data.get("publication_date", "UNKNOWN")),
            revision_status=str(data.get("revision_status", "REVISION_POLICY_UNVERIFIED")),
            authority_class=str(data.get("authority_class", "ISSUER_OFFICIAL_TABLE")),
            confirmation_status=confirmation_status,
            cusip=data.get("cusip"),
            coverage_notes=str(data.get("coverage_notes", "")),
        )


@dataclass(frozen=True)
class LaneBCandidateEvaluationResult:
    """Authoritative outcome of an offline candidate panel qualification evaluation."""
    total_events: int
    confirmed_events: int
    partial_events: int
    symbols_evaluated: Tuple[str, ...]
    economic_composite_digest: str
    evidence_manifest_digest: str
    manifest_summary: Dict[str, Any]
    status: str  # CANDIDATE_STRUCTURE_VALIDATED / SOURCE_VERIFIED_CANDIDATE

    @property
    def composite_digest(self) -> str:
        """Single canonical authority alias for backward-compatible economic composite digest."""
        return self.economic_composite_digest


class LaneBCandidateEvaluator:
    """Evaluates candidate events against fail-closed data contract rules."""

    def __init__(self, allowed_symbols: Optional[Set[str]] = None) -> None:
        self.allowed_symbols = frozenset(allowed_symbols) if allowed_symbols else LANE_B_CANDIDATE_UNIVERSE

    def evaluate_panel(self, events: Sequence[LaneBCandidateEvent]) -> LaneBCandidateEvaluationResult:
        """Validate an entire candidate panel and compute dual deterministic framed digests."""
        if not events:
            raise DataContractError("Candidate panel must not be empty.")

        seen_economic_keys: Dict[Tuple[str, date, str], LaneBCandidateEvent] = {}
        economic_records: List[bytes] = []
        evidence_records: List[bytes] = []
        symbols_present: Set[str] = set()

        confirmed_count = 0
        partial_count = 0

        for ev in events:
            # 1. Universe bounds
            if ev.symbol not in self.allowed_symbols:
                raise DataContractError(
                    f"Symbol '{ev.symbol}' is not within authorized candidate universe {sorted(self.allowed_symbols)}"
                )
            symbols_present.add(ev.symbol)

            # 2. GLD Grantor Trust Rule
            if ev.symbol == "GLD":
                raise DataContractError(
                    "GLD is a physical grantor trust with NO_CASH_DISTRIBUTION_ENTITLEMENT; "
                    "recording cash dividend events for GLD is strictly prohibited."
                )

            # 3. Fund legal identity check
            expected_fund_id = EXPECTED_FUND_IDENTITIES.get(ev.symbol)
            if expected_fund_id and ev.fund_legal_identity != expected_fund_id:
                raise DataContractError(
                    f"Fund legal identity mismatch for '{ev.symbol}': expected '{expected_fund_id}', "
                    f"got '{ev.fund_legal_identity}'."
                )

            # 4. Event type check
            if ev.event_type not in ALLOWED_EVENT_TYPES:
                raise DataContractError(
                    f"Disallowed event type '{ev.event_type}' for '{ev.symbol}'; "
                    f"allowed types are {sorted(ALLOWED_EVENT_TYPES)}."
                )

            # 5. Source authority check & Issuer domain binding
            if ev.authority_class not in VALID_AUTHORITY_CLASSES:
                raise DataContractError(
                    f"Event for '{ev.symbol}' on {ev.ex_date} has invalid authority class '{ev.authority_class}'; "
                    f"UNKNOWN_BASIS records are strictly rejected."
                )
            if not ev.source_url or not ev.source_document:
                raise DataContractError(
                    f"Event for '{ev.symbol}' on {ev.ex_date} lacks verifiable source URL or document identity."
                )

            if ev.confirmation_status not in ALLOWED_CONFIRMATION_STATUSES:
                raise DataContractError(
                    f"Malformed confirmation_status '{ev.confirmation_status}' for '{ev.symbol}' "
                    f"on {ev.ex_date}; allowed values are {sorted(ALLOWED_CONFIRMATION_STATUSES)}."
                )

            try:
                parsed_url = urlparse(ev.source_url)
                parsed_port = parsed_url.port
            except ValueError as exc:
                raise DataContractError(
                    f"Malformed source URL '{ev.source_url}' for '{ev.symbol}'."
                ) from exc
            if parsed_url.scheme != "https":
                raise DataContractError(
                    f"Source URL '{ev.source_url}' for '{ev.symbol}' must use https."
                )
            if parsed_url.username is not None or parsed_url.password is not None:
                raise DataContractError(
                    f"Source URL '{ev.source_url}' for '{ev.symbol}' must not embed credentials/userinfo."
                )
            if parsed_port is not None:
                raise DataContractError(
                    f"Source URL '{ev.source_url}' for '{ev.symbol}' must not specify an explicit port."
                )
            hostname = (parsed_url.hostname or "").lower()
            authorized_domains = AUTHORIZED_ISSUER_DOMAINS.get(ev.symbol, ())
            if not any(hostname == d or hostname.endswith(f".{d}") for d in authorized_domains):
                raise DataContractError(
                    f"Source URL '{ev.source_url}' for '{ev.symbol}' does not resolve to an authorized issuer domain: "
                    f"{authorized_domains}."
                )

            # 5b. Evidence binding: an authorized domain is a structural check,
            # NOT proof of event existence. Confirmation requires an identified
            # issuer source row/document; without it the event is partial.
            effective_confirmation = ev.confirmation_status
            if (
                effective_confirmation == "SOURCE_CONFIRMED_CANDIDATE"
                and not ev.source_row_ref.strip()
            ):
                effective_confirmation = "SOURCE_PARTIAL"

            # 6. Currency check
            if ev.currency not in ALLOWED_CURRENCIES:
                raise DataContractError(
                    f"Unsupported distribution currency '{ev.currency}'; strictly USD is allowed."
                )

            # 7. Amount bounds
            ensure_finite_decimal(ev.amount, field_name=f"{ev.symbol}_amount")
            validate_decimal128_bounds(ev.amount, field_name=f"{ev.symbol}_amount")
            if ev.amount <= Decimal("0"):
                raise DataContractError(
                    f"Event amount for '{ev.symbol}' on {ev.ex_date} must be positive; got {ev.amount}."
                )

            # 8. Date ordering invariant: ex_date <= record_date <= payable_date
            if ev.record_date < ev.ex_date:
                raise DataContractError(
                    f"Date ordering contradiction for '{ev.symbol}': record_date {ev.record_date} "
                    f"precedes ex_date {ev.ex_date}."
                )
            if ev.payable_date < ev.record_date:
                raise DataContractError(
                    f"Date ordering contradiction for '{ev.symbol}': payable_date {ev.payable_date} "
                    f"precedes record_date {ev.record_date}."
                )

            # 9. Canonical duplicate detection
            economic_key = (ev.symbol, ev.ex_date, ev.event_type)
            if economic_key in seen_economic_keys:
                prior = seen_economic_keys[economic_key]
                if (
                    prior.amount == ev.amount
                    and prior.payable_date == ev.payable_date
                    and prior.record_date == ev.record_date
                ):
                    raise DataContractError(
                        f"Duplicate identical event for '{ev.symbol}' on ex_date {ev.ex_date}; "
                        "redundant rows are prohibited to prevent digest inflation."
                    )
                raise DataContractError(
                    f"Contradictory duplicate event for '{ev.symbol}' on ex_date {ev.ex_date}: "
                    f"conflicting values {prior.amount} vs {ev.amount}."
                )
            seen_economic_keys[economic_key] = ev

            # 10. Confirmation status tracking (effective, post-binding)
            if effective_confirmation == "SOURCE_CONFIRMED_CANDIDATE":
                confirmed_count += 1
            else:
                partial_count += 1

            # 11. Deterministic serialization for dual digests.
            # Canonical, collision-free JSON (no unescaped delimiter joins).
            economic_payload = {
                "symbol": ev.symbol,
                "ex_date": ev.ex_date.isoformat(),
                "record_date": ev.record_date.isoformat(),
                "payable_date": ev.payable_date.isoformat(),
                "amount": str(ev.amount),
                "currency": ev.currency,
                "event_type": ev.event_type,
            }
            evidence_payload = {
                **economic_payload,
                "fund_legal_identity": ev.fund_legal_identity,
                "source_url": ev.source_url,
                "source_document": ev.source_document,
                "source_row_ref": ev.source_row_ref,
                "retrieval_status": ev.retrieval_status,
                "publication_date": ev.publication_date,
                "revision_status": ev.revision_status,
                "authority_class": ev.authority_class,
                "confirmation_status": effective_confirmation,
                "cusip": ev.cusip or "",
            }
            economic_records.append(
                CanonicalConfigSerializer.to_canonical_json(
                    economic_payload
                ).encode("utf-8")
            )
            evidence_records.append(
                CanonicalConfigSerializer.to_canonical_json(
                    evidence_payload
                ).encode("utf-8")
            )

        # Sort serialized records deterministically by content before hashing
        economic_records.sort()
        evidence_records.sort()

        economic_digest = compute_framed_composite_sha256(economic_records)
        evidence_digest = compute_framed_composite_sha256(evidence_records)

        # Status classification: Truthful separation of partial structure vs verified candidate
        if partial_count > 0:
            status = "CANDIDATE_STRUCTURE_VALIDATED"
        else:
            status = "SOURCE_VERIFIED_CANDIDATE"

        summary = {
            "total_events": len(events),
            "unique_events": len(seen_economic_keys),
            "confirmed_events": confirmed_count,
            "partial_events": partial_count,
            "symbols": sorted(symbols_present),
            "economic_composite_sha256": economic_digest,
            "evidence_manifest_sha256": evidence_digest,
            "status": status,
        }

        return LaneBCandidateEvaluationResult(
            total_events=len(events),
            confirmed_events=confirmed_count,
            partial_events=partial_count,
            symbols_evaluated=tuple(sorted(symbols_present)),
            economic_composite_digest=economic_digest,
            evidence_manifest_digest=evidence_digest,
            manifest_summary=summary,
            status=status,
        )
