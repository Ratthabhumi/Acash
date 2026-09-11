"""ACASH Paper Trading Infrastructure — E3 Black-Box Flight Recorder.

This package implements the complete Paper Trading layer (E3) for ACASH V5.

IMPORTANT GOVERNANCE NOTICE:
=============================
This package provides EXECUTION INFRASTRUCTURE ONLY.

It is NOT:
- Research evidence for MACRO-001
- HYP_003 or any new hypothesis
- R1 authorization
- Backtest authorization
- Live trading authorization
- Evidence that D17-E is resolved

The existence and operation of this infrastructure does NOT constitute:
- Strategy validation
- Statistical qualification
- Capital authorization
- Any change to MACRO-001 governance state

Infrastructure-test strategies in this package are labeled:
    INFRASTRUCTURE_TEST_STRATEGY_ONLY
and MUST NOT be treated as ACASH research evidence.

Architecture:
    E0 (Execution Architecture) → E1 (Synthetic Broker) → E2 (Broker Boundary)
    → E3 (Paper Trading + Black-Box Flight Recorder)

Modules:
    journal     — PaperEventJournal: hash-chained, append-only, 7-layer event recording
    trace       — DecisionTrace: query complete chain by correlation_id
    replay      — ReplayEngine: deterministic replay from journal
    manifest    — PaperSessionManifest: session sealing with cryptographic lineage
    reconcile   — PaperReconciliationEngine: cross-check journal ↔ orders ↔ fills ↔ positions
    strategy    — InfrastructureTestStrategy: INFRA-ONLY test strategy
    runner      — PaperSessionRunner: E3 wiring
    analytics   — PaperAnalyticsEngine: observed metrics (NOT strategy qualification)
    health      — PaperHealthMonitor: system health recording
    snapshot    — DailySnapshot: daily operational summary
    feed        — E3.5 provider-agnostic real market data feed (IMarketDataFeed)
    session     — E3.5 PaperFeedSessionSupervisor: real-feed → runner wiring
    review      — E3.5 ReviewPackage builder (OBSERVED/MODEL/DERIVED audit artifact)
    cli         — E3.5 operational CLI (python -m acash.paper)
"""

from acash.paper.journal import (
    JournalEvent,
    JournalEventType,
    JournalLayer,
    PaperEventJournal,
)
from acash.paper.manifest import (
    PaperMode,
    PaperSessionManifest,
)
from acash.paper.trace import DecisionTrace, DecisionTraceStep
from acash.paper.reconcile import (
    PaperReconciliationEngine,
    ReconciliationResult,
    ReconciliationStatus,
)
from acash.paper.replay import ReplayEngine, ReplayResult, ReplayStatus
from acash.paper.strategy import InfrastructureTestStrategy, StrategySignal, SignalDirection
from acash.paper.runner import PaperSessionRunner, PaperSessionConfig, SyntheticBar
from acash.paper.health import PaperHealthMonitor, HealthEventKind
from acash.paper.analytics import PaperAnalyticsEngine, PaperAnalyticsReport
from acash.paper.snapshot import DailySnapshot, DailySnapshotStore
from acash.paper.feed import (
    FeedBar,
    FeedStatus,
    FeedContractError,
    FeedConnectionError,
    FeedMalformedResponseError,
    FeedDataValidationError,
    IMarketDataFeed,
    BinancePublicKlinesFeed,
    StooqCsvFeed,
    feed_bar_to_synthetic_bar,
)
from acash.paper.session import (
    FeedSupervisorStats,
    PaperFeedSessionSupervisor,
)
from acash.paper.review import (
    ProvenanceLabel,
    ReviewItem,
    ReviewPackage,
    build_review_package,
)

__all__ = [
    # Journal
    "JournalEvent",
    "JournalEventType",
    "JournalLayer",
    "PaperEventJournal",
    # Manifest
    "PaperMode",
    "PaperSessionManifest",
    # Trace
    "DecisionTrace",
    "DecisionTraceStep",
    # Reconciliation
    "PaperReconciliationEngine",
    "ReconciliationResult",
    "ReconciliationStatus",
    # Replay
    "ReplayEngine",
    "ReplayResult",
    "ReplayStatus",
    # Strategy
    "InfrastructureTestStrategy",
    "StrategySignal",
    "SignalDirection",
    # Runner
    "PaperSessionRunner",
    "PaperSessionConfig",
    # Health
    "PaperHealthMonitor",
    "HealthEventKind",
    # Analytics
    "PaperAnalyticsEngine",
    "PaperAnalyticsReport",
    # Snapshot
    "DailySnapshot",
    "DailySnapshotStore",
    # E3.5 Feed
    "FeedBar",
    "FeedStatus",
    "FeedContractError",
    "FeedConnectionError",
    "FeedMalformedResponseError",
    "FeedDataValidationError",
    "IMarketDataFeed",
    "BinancePublicKlinesFeed",
    "StooqCsvFeed",
    "feed_bar_to_synthetic_bar",
    # E3.5 Session
    "FeedSupervisorStats",
    "PaperFeedSessionSupervisor",
    # E3.5 Review Package
    "ProvenanceLabel",
    "ReviewItem",
    "ReviewPackage",
    "build_review_package",
]
