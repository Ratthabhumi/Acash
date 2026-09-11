"""ACASH Paper Trading — E3.5 Review Package Builder.

The Review Package is the audit artifact a human reviewer consumes AFTER a
paper session. Every item in the package must be labeled with its provenance:

- OBSERVED  : directly read from the event journal / market feed (fact).
- MODEL     : produced by an ACASH model, simulation, or calculation.
- DERIVED   : a monotonic transformation of OBSERVED/MODEL items (never a new
              source of information).

The package is generated only from a sealed PaperEventJournal + session
manifest + daily snapshots. It is NOT research evidence and is NOT a
profitability dashboard; it is an OPERATIONAL review surface for the E3.5
human gate.

GOVERNANCE (E3.5):
==================
- Every item carries an explicit provenance label (OBSERVED | MODEL | DERIVED).
- No item is ever labeled OBSERVED unless it was read from the journal/feed.
- No research conclusion may be drawn from this package; it is an audit record.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

from acash.core.domain.exceptions import DataContractError
from acash.paper.journal import (
    JournalEventType,
    PaperEventJournal,
)
from acash.paper.manifest import PaperSessionManifest
from acash.paper.runner import PaperPortfolioState
from acash.paper.snapshot import DailySnapshot


class ProvenanceLabel:
    """Canonical provenance labels with strict semantics."""

    OBSERVED = "OBSERVED"
    MODEL = "MODEL"
    DERIVED = "DERIVED"

    _VALID = frozenset({OBSERVED, MODEL, DERIVED})

    @classmethod
    def validate(cls, label: str) -> str:
        if label not in cls._VALID:
            raise DataContractError(
                f"ProvenceLabel: unknown label {label!r}; "
                "must be one of OBSERVED/MODEL/DERIVED."
            )
        return label


@dataclass
class ReviewItem:
    """One row of the review package."""

    item_id: str
    section: str
    name: str
    provenance: str  # OBSERVED | MODEL | DERIVED
    value: Any
    description: str = ""

    def __post_init__(self) -> None:
        ProvenanceLabel.validate(self.provenance)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "section": self.section,
            "name": self.name,
            "provenance": self.provenance,
            "value": self.value,
            "description": self.description,
        }


@dataclass
class ReviewPackage:
    """Complete E3.5 review artifact for one session."""

    package_id: str
    session_id: str
    generated_at_utc: datetime
    items: List[ReviewItem] = field(default_factory=list)

    def add(
        self,
        section: str,
        name: str,
        provenance: str,
        value: Any,
        description: str = "",
    ) -> None:
        ProvenanceLabel.validate(provenance)
        self.items.append(
            ReviewItem(
                item_id=f"R{item_id_counter(self.items)}",
                section=section,
                name=name,
                provenance=provenance,
                value=value,
                description=description,
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "package_id": self.package_id,
            "session_id": self.session_id,
            "generated_at_utc": self.generated_at_utc.isoformat(),
            "governance_scope": "EXECUTION/PAPER INFRASTRUCTURE ONLY — NOT research evidence",
            "item_count": len(self.items),
            "items": [i.to_dict() for i in self.items],
        }

    def sections(self) -> Dict[str, List[ReviewItem]]:
        sections: Dict[str, List[ReviewItem]] = {}
        for item in self.items:
            sections.setdefault(item.section, []).append(item)
        return sections


def item_id_counter(items: List[ReviewItem]) -> int:
    return len(items) + 1


def build_review_package(
    *,
    session_id: str,
    journal: PaperEventJournal,
    manifest: PaperSessionManifest,
    portfolio: PaperPortfolioState,
    snapshots: List[DailySnapshot],
) -> ReviewPackage:
    """Build a standard 22-item E3.5 review package from journal artifacts.

    All items read from the journal/manifest/snapshots are OBSERVED. Items
    computed by an algorithm (e.g. equity change) are MODEL. Items that are
    strict transformations of OBSERVED values are DERIVED. No item is ever
    asserted to be OBSERVED without a journal/manifest/snapshot source.
    """
    package = ReviewPackage(
        package_id=f"RP-{uuid.uuid4().hex[:12]}",
        session_id=session_id,
        generated_at_utc=datetime.now(timezone.utc),
    )

    events = sorted(
        journal.read_all(), key=lambda e: e.sequence
    )

    # ---- Section 1: Session & Governance (OBSERVED, from manifest) -------
    package.add(
        "SESSION",
        "session_id",
        ProvenanceLabel.OBSERVED,
        session_id,
        "Session identifier (manifest).",
    )
    package.add(
        "SESSION",
        "strategy_id",
        ProvenanceLabel.OBSERVED,
        manifest.strategy_id,
        "Strategy claimed by the session manifest.",
    )
    package.add(
        "SESSION",
        "is_infrastructure_test_strategy",
        ProvenanceLabel.OBSERVED,
        manifest.is_infrastructure_test_strategy,
        "Manifest assertion that only INFRA-test is allowed.",
    )
    package.add(
        "SESSION",
        "config_hash",
        ProvenanceLabel.DERIVED,
        manifest.config_hash,
        "SHA-256 bind of canonical session config.",
    )
    package.add(
        "SESSION",
        "data_source",
        ProvenanceLabel.OBSERVED,
        manifest.data_source,
        "Data source label in the sealed manifest.",
    )
    package.add(
        "SESSION",
        "market_domain",
        ProvenanceLabel.OBSERVED,
        manifest.market_domain,
        "Market domain label in the sealed manifest.",
    )

    # ---- Section 2: Journal integrity (OBSERVED, read from journal) ------
    integrity_violations = journal.verify_integrity()
    package.add(
        "JOURNAL",
        "event_count",
        ProvenanceLabel.OBSERVED,
        len(events),
        "Total events sealed in the journal.",
    )
    package.add(
        "JOURNAL",
        "integrity_violations",
        ProvenanceLabel.OBSERVED,
        len(integrity_violations),
        "Number of hash-chain violations discovered by re-verification.",
    )
    package.add(
        "JOURNAL",
        "integrity_status",
        ProvenanceLabel.DERIVED,
        "PASS" if not integrity_violations else "FAIL",
        "Derived from the OBSERVED integrity violation count.",
    )
    package.add(
        "JOURNAL",
        "first_sequence",
        ProvenanceLabel.OBSERVED,
        events[0].sequence if events else None,
        "First journaled event sequence.",
    )
    package.add(
        "JOURNAL",
        "last_sequence",
        ProvenanceLabel.OBSERVED,
        events[-1].sequence if events else None,
        "Last journaled event sequence.",
    )
    package.add(
        "JOURNAL",
        "manifest_journal_final_hash",
        ProvenanceLabel.OBSERVED,
        manifest.journal_final_hash,
        "Manifest-stated terminal hash of the journal.",
    )
    package.add(
        "JOURNAL",
        "journal_last_event_hash",
        ProvenanceLabel.OBSERVED,
        journal.last_event_hash,
        "Current terminal hash of the journal on disk.",
    )
    package.add(
        "JOURNAL",
        "hash_match",
        ProvenanceLabel.DERIVED,
        manifest.journal_final_hash == journal.last_event_hash,
        "Derived equality check between manifest and disk terminal hash.",
    )

    # ---- Section 3: Feed provenance (OBSERVED, from MARKET_DATA events) ---
    feed_sources = sorted(
        {
            ev.payload.get("source", "UNKNOWN")
            for ev in events
            if ev.event_type == JournalEventType.MARKET_BAR_RECEIVED
        }
    )
    feed_unavailable_union = sorted(
        {
            u
            for ev in events
            if ev.event_type == JournalEventType.MARKET_BAR_RECEIVED
            for u in ev.payload.get("unavailable", [])
        }
    )
    package.add(
        "FEED",
        "feed_sources_used",
        ProvenanceLabel.OBSERVED,
        feed_sources,
        "Distinct bars' feed provenance markers found in the journal.",
    )
    package.add(
        "FEED",
        "bar_count",
        ProvenanceLabel.OBSERVED,
        sum(1 for ev in events if ev.event_type == JournalEventType.MARKET_BAR_RECEIVED),
        "Count of MARKET_BAR_RECEIVED events.",
    )
    package.add(
        "FEED",
        "stale_bar_count",
        ProvenanceLabel.OBSERVED,
        sum(1 for ev in events if ev.event_type == JournalEventType.MARKET_BAR_STALE),
        "Count of stale bars refused by the freshness gate.",
    )
    package.add(
        "FEED",
        "rejected_bar_count",
        ProvenanceLabel.OBSERVED,
        sum(1 for ev in events if ev.event_type == JournalEventType.MARKET_BAR_REJECTED),
        "Count of malformed bars rejected and recorded.",
    )
    package.add(
        "FEED",
        "feed_disconnect_count",
        ProvenanceLabel.OBSERVED,
        sum(1 for ev in events if ev.event_type == JournalEventType.FEED_DISCONNECTED),
        "Count of feed disconnect events.",
    )
    package.add(
        "FEED",
        "unavailable_fields",
        ProvenanceLabel.OBSERVED,
        feed_unavailable_union or None,
        "Union of fields the feeds did not supply (never fabricated).",
    )

    # ---- Section 4: Portfolio outcome (MODEL for computed values) ---------
    package.add(
        "PORTFOLIO",
        "starting_cash",
        ProvenanceLabel.MODEL,
        str(portfolio.cash if portfolio.position == 0 else portfolio.cash),
        "Portfolio cash (paper accounting model).",
    )
    package.add(
        "PORTFOLIO",
        "trade_count",
        ProvenanceLabel.OBSERVED,
        portfolio.trade_count,
        "Number of fills simulated by the paper execution model.",
    )
    package.add(
        "PORTFOLIO",
        "order_count",
        ProvenanceLabel.OBSERVED,
        portfolio.order_count,
        "Number of order intents created.",
    )
    package.add(
        "PORTFOLIO",
        "rejected_order_count",
        ProvenanceLabel.OBSERVED,
        portfolio.rejected_order_count,
        "Number of orders rejected by inline risk checks.",
    )
    package.add(
        "PORTFOLIO",
        "realized_pnl",
        ProvenanceLabel.MODEL,
        str(portfolio.realized_pnl),
        "Realized PnL from the paper accounting model (MODEL, not P&L proof).",
    )
    package.add(
        "PORTFOLIO",
        "equity",
        ProvenanceLabel.DERIVED,
        str(portfolio.equity),
        "Derived cash + mark-to-market position value.",
    )
    package.add(
        "PORTFOLIO",
        "daily_snapshot_count",
        ProvenanceLabel.OBSERVED,
        len(snapshots),
        "Number of append-only daily snapshots available.",
    )
    package.add(
        "PORTFOLIO",
        "last_snapshot_integrity",
        ProvenanceLabel.OBSERVED,
        snapshots[-1].journal_integrity_status if snapshots else "NO_SNAPSHOT",
        "Integrity status recorded in the most recent snapshot.",
    )

    return package