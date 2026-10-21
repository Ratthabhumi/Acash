"""Lane B Corporate-Action Candidate Qualification Evaluator (Offline Rehearsal).

Evaluates candidate ETF corporate-action panels against the fail-closed invariants
specified in docs/research/LANE_B_SPEC_OFFLINE_QUALIFICATION.md:
1. UNKNOWN-basis rejection: Records lacking authorized source binding are rejected.
2. Finite positive amounts: Decimal precision within Decimal128 bounds; no negative values.
3. Date ordering: ex_date <= record_date <= payable_date.
4. GLD Grantor Trust rule: GLD carries NO_CASH_DISTRIBUTION_ENTITLEMENT. Recording cash
   dividend events for GLD raises DataContractError.
5. Deterministic hashing: Page and composite digests via length-prefixed framing.
6. Strict separation of candidate research from qualified/authorized execution data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.core.domain.types import ensure_finite_decimal
from acash.data.qualification.manifest import compute_framed_composite_sha256, compute_page_sha256
from acash.data.schema import validate_decimal128_bounds

LANE_B_CANDIDATE_UNIVERSE: frozenset[str] = frozenset({"VOO", "BND", "BIL", "GLD"})
ALLOWED_CURRENCIES: frozenset[str] = frozenset({"USD"})
VALID_AUTHORITY_CLASSES: frozenset[str] = frozenset({
    "ISSUER_OFFICIAL_TABLE",
    "SPONSOR_DECLARATION",
    "REGULATORY_FILING",
})


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
    publication_date: str = "UNKNOWN"
    revision_status: str = "REVISION_POLICY_UNVERIFIED"
    authority_class: str = "ISSUER_OFFICIAL_TABLE"
    confirmation_status: str = "SOURCE_CONFIRMED_CANDIDATE"
    cusip: Optional[str] = None
    coverage_notes: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> LaneBCandidateEvent:
        """Parse from dictionary with fail-closed Decimal conversion."""
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
            publication_date=str(data.get("publication_date", "UNKNOWN")),
            revision_status=str(data.get("revision_status", "REVISION_POLICY_UNVERIFIED")),
            authority_class=str(data.get("authority_class", "ISSUER_OFFICIAL_TABLE")),
            confirmation_status=str(data.get("confirmation_status", "SOURCE_CONFIRMED_CANDIDATE")),
            cusip=data.get("cusip"),
            coverage_notes=str(data.get("coverage_notes", "")),
        )


@dataclass(frozen=True)
class LaneBCandidateEvaluationResult:
    """Authoritative outcome of an offline candidate panel qualification evaluation."""
    total_events: int
    symbols_evaluated: Tuple[str, ...]
    composite_digest: str
    manifest_summary: Dict[str, Any]
    status: str  # CANDIDATE_PANEL_VERIFIED / REJECTED


class LaneBCandidateEvaluator:
    """Evaluates candidate events against fail-closed data contract rules."""

    def __init__(self, allowed_symbols: Optional[Set[str]] = None) -> None:
        self.allowed_symbols = frozenset(allowed_symbols) if allowed_symbols else LANE_B_CANDIDATE_UNIVERSE

    def evaluate_panel(self, events: Sequence[LaneBCandidateEvent]) -> LaneBCandidateEvaluationResult:
        """Validate an entire candidate panel and compute its deterministic framed digest."""
        if not events:
            raise DataContractError("Candidate panel must not be empty.")

        seen_event_keys: Dict[Tuple[str, date], LaneBCandidateEvent] = {}
        serialized_records: List[bytes] = []
        symbols_present: Set[str] = set()

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

            # 3. Source authority check
            if ev.authority_class not in VALID_AUTHORITY_CLASSES:
                raise DataContractError(
                    f"Event for '{ev.symbol}' on {ev.ex_date} has invalid authority class '{ev.authority_class}'; "
                    f"UNKNOWN_BASIS records are strictly rejected."
                )
            if not ev.source_url or not ev.source_document:
                raise DataContractError(
                    f"Event for '{ev.symbol}' on {ev.ex_date} lacks verifiable source URL or document identity."
                )

            # 4. Currency check
            if ev.currency not in ALLOWED_CURRENCIES:
                raise DataContractError(
                    f"Unsupported distribution currency '{ev.currency}'; strictly USD is allowed."
                )

            # 5. Amount bounds
            ensure_finite_decimal(ev.amount, field_name=f"{ev.symbol}_amount")
            validate_decimal128_bounds(ev.amount, field_name=f"{ev.symbol}_amount")
            if ev.amount <= Decimal("0"):
                raise DataContractError(
                    f"Event amount for '{ev.symbol}' on {ev.ex_date} must be positive; got {ev.amount}."
                )

            # 6. Date ordering invariant: ex_date <= record_date <= payable_date
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

            # 7. Duplicate / Contradiction check
            event_key = (ev.symbol, ev.ex_date)
            if event_key in seen_event_keys:
                prior = seen_event_keys[event_key]
                if (
                    prior.amount != ev.amount
                    or prior.payable_date != ev.payable_date
                    or prior.record_date != ev.record_date
                ):
                    raise DataContractError(
                        f"Contradictory duplicate event for '{ev.symbol}' on ex_date {ev.ex_date}: "
                        f"amount {prior.amount} vs {ev.amount}."
                    )
            seen_event_keys[event_key] = ev

            # 8. Deterministic record serialization for length-prefixed framing
            norm_str = (
                f"{ev.symbol}|{ev.ex_date.isoformat()}|{ev.record_date.isoformat()}|"
                f"{ev.payable_date.isoformat()}|{ev.amount}|{ev.currency}|{ev.source_url}"
            )
            serialized_records.append(norm_str.encode("utf-8"))

        # Sort serialized records deterministically by content before hashing
        serialized_records.sort()
        composite_digest = compute_framed_composite_sha256(serialized_records)

        summary = {
            "total_events": len(events),
            "unique_events": len(seen_event_keys),
            "symbols": sorted(symbols_present),
            "composite_sha256": composite_digest,
            "status": "CANDIDATE_PANEL_VERIFIED",
        }

        return LaneBCandidateEvaluationResult(
            total_events=len(events),
            symbols_evaluated=tuple(sorted(symbols_present)),
            composite_digest=composite_digest,
            manifest_summary=summary,
            status="CANDIDATE_PANEL_VERIFIED",
        )
