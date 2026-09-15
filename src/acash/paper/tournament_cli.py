"""ACASH Paper Trading — Shadow Alpha Tournament CLI Entrypoint.

Command:
    python -m acash.paper.tournament_cli [options]

GOVERNANCE:
- SHADOW / SIMULATED RESEARCH INFRASTRUCTURE ONLY — NOT Paper GO / NOT Live
- NO_REAL_ORDERS=True | CANONICAL_CAPITAL_USD=$0.00
- Credential-free feed only (Binance public klines / Stooq CSV)
- Fail-closed on feed disconnect or stale data. Automatic Feed Reconnect is
  DISABLED BY DEFAULT: any transient feed connection failure immediately halts
  (exit code 2) and requires operator resume. Operators elect the controlled
  shadow recovery path explicitly with --enable-feed-recovery; it then resumes
  deterministically from the first unapplied bar within a bounded attempts /
  backoff / bar-wait budget, with every phase journaled fail-closed.
- Graceful shutdown with journal & manifest sealing on SIGINT/SIGTERM
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from acash.core.domain.enums import BarTimeframe
from acash.core.domain.exceptions import DataContractError
from acash.paper.feed import (
    BinancePublicKlinesFeed,
    FeedConnectionError,
    FeedContractError,
    StooqCsvFeed,
    feed_bar_to_synthetic_bar,
)
from acash.paper.health import HealthEventKind, TerminalReason
from acash.paper.metrics import MetricsRegistry, PaperMetricsServer
from acash.paper.recovery import (
    FeedRecoveryConfig,
    FeedRecoveryState,
    RECOVERY_PHASE_ABORTED,
    RECOVERY_PHASE_ATTEMPT,
    RECOVERY_PHASE_ATTEMPT_FAILED,
    RECOVERY_PHASE_BUDGET_EXHAUSTED,
    RECOVERY_PHASE_INVALID_BAR,
    RECOVERY_PHASE_POLLING,
    RECOVERY_PHASE_RESUMED,
    run_feed_recovery,
)
from acash.paper.runner import SignalSizingPolicy
from acash.paper.tournament import (
    CANONICAL_CAPITAL_USD,
    NO_REAL_ORDERS,
    ShadowTournamentSupervisor,
    create_default_shadow_tournament,
)
from acash.paper.tournament_api import ShadowApiServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger("acash.shadow.tournament")


# Recovery journal phases -> health event kinds (single mapping authority).
# RESUMED is intentionally absent: supervisor.exit_feed_recovery journals
# the authoritative FEED_RECOVERY_SUCCEEDED event.
_RECOVERY_PHASE_KIND: Dict[str, Optional[HealthEventKind]] = {
    RECOVERY_PHASE_ATTEMPT: HealthEventKind.FEED_RECOVERY_ATTEMPTED,
    RECOVERY_PHASE_ATTEMPT_FAILED: HealthEventKind.FEED_RECOVERY_ATTEMPTED,
    RECOVERY_PHASE_POLLING: None,
    RECOVERY_PHASE_RESUMED: None,
    RECOVERY_PHASE_BUDGET_EXHAUSTED: HealthEventKind.FEED_RECOVERY_BUDGET_EXHAUSTED,
    RECOVERY_PHASE_INVALID_BAR: HealthEventKind.FEED_RECOVERY_ABORTED,
    RECOVERY_PHASE_ABORTED: HealthEventKind.FEED_RECOVERY_ABORTED,
}


def _parse_backoff_seconds(value: str) -> Tuple[float, ...]:
    """Parse '2,5,10,20,30' into a bounded backoff schedule (fail-closed)."""
    try:
        parts = tuple(float(part.strip()) for part in value.split(",") if part.strip())
    except (ValueError, AttributeError) as exc:
        raise argparse.ArgumentTypeError(
            f"recovery backoff must be comma-separated positive numbers, got {value!r}"
        ) from exc
    if not parts or any(not math.isfinite(part) or part <= 0 for part in parts):
        raise argparse.ArgumentTypeError(
            f"recovery backoff must be finite positive numbers, got {value!r}"
        )
    return parts


def _parse_nav_sizing_pct(value: str) -> Decimal:
    """Parse the NAV-relative sizing percentage (strict, bounds-checked)."""
    try:
        pct = Decimal(value.strip())
    except (InvalidOperation, AttributeError) as exc:
        raise argparse.ArgumentTypeError(
            f"nav-sizing-notional-pct must be a decimal number, got {value!r}"
        ) from exc
    if not (Decimal("0") < pct <= Decimal("100")):
        raise argparse.ArgumentTypeError(
            f"nav-sizing-notional-pct must be in (0, 100], got {value!r}"
        )
    return pct


def _positive_int(value: str) -> int:
    """Strict integer validator: reject 0, negatives, and non-integers."""
    try:
        parsed = int(value)
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError(
            f"must be a positive integer, got {value!r}"
        ) from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError(
            f"must be a positive integer (>= 1), got {value!r}"
        )
    return parsed


def _positive_float(value: str) -> float:
    """Strict float validator: reject zero, negatives, non-numerics, and non-finite values."""
    try:
        parsed = float(value)
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError(
            f"must be a positive number, got {value!r}"
        ) from exc
    if not math.isfinite(parsed):
        raise argparse.ArgumentTypeError(
            f"must be a finite number, got {value!r}"
        )
    if parsed <= 0:
        raise argparse.ArgumentTypeError(
            f"must be a positive number (> 0), got {value!r}"
        )
    return parsed


def _non_negative_float(value: str) -> float:
    """Strict float validator: reject negatives, non-numerics, and non-finite values (zero allowed)."""
    try:
        parsed = float(value)
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError(
            f"must be a non-negative number, got {value!r}"
        ) from exc
    if not math.isfinite(parsed):
        raise argparse.ArgumentTypeError(
            f"must be a finite number, got {value!r}"
        )
    if parsed < 0:
        raise argparse.ArgumentTypeError(
            f"must be a non-negative number (>= 0), got {value!r}"
        )
    return parsed


def _detect_git_commit() -> Optional[str]:
    """Detect current Git commit SHA from environment or local repository."""
    env_sha = os.environ.get("ACASH_GIT_COMMIT", "").strip()
    if env_sha:
        return env_sha
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2.0,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return None


def _resolve_sizing(
    args: argparse.Namespace,
) -> Tuple[SignalSizingPolicy, Decimal]:
    """Resolve the tournament sizing policy from CLI flags (getattr-safe for
    hand-built Namespaces in tests). 'auto' derives NAV-relative sizing only
    when catalog auto-mounting is active."""
    mode = getattr(args, "infra_sizing_policy", "auto")
    auto_mount = bool(getattr(args, "auto_mount_infra_candidates", False))
    if mode == "legacy-fixed":
        policy = SignalSizingPolicy.INFRA_FIXED_QUANTITY
    elif mode == "nav-relative":
        policy = SignalSizingPolicy.NAV_RELATIVE_PERCENT
    else:  # auto
        policy = (
            SignalSizingPolicy.NAV_RELATIVE_PERCENT
            if auto_mount
            else SignalSizingPolicy.INFRA_FIXED_QUANTITY
        )
    nav_pct = getattr(args, "nav_sizing_notional_pct", Decimal("10.0"))
    effective_pct = (
        nav_pct
        if policy == SignalSizingPolicy.NAV_RELATIVE_PERCENT
        else Decimal("0")
    )
    return policy, effective_pct


def _load_candidate_requests(path: Path) -> List[Dict[str, str]]:
    """Fail-closed parse of the operator candidate-add file.

    Accepts a bare list [{slotId, strategyId}, ...] or a dict with an
    'addCandidates' key. Raises DataContractError for any structurally invalid
    input — operator input is never silently ignored or half-applied.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DataContractError(f"candidate-add file {path} unreadable: {exc}") from exc
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise DataContractError(
            f"candidate-add file {path} is not valid JSON: {exc}"
        ) from exc

    if isinstance(data, dict):
        requests = data.get("addCandidates", None)
        if requests is None:
            raise DataContractError(
                f"candidate-add file {path} is missing 'addCandidates'"
            )
    elif isinstance(data, list):
        requests = data
    else:
        raise DataContractError(
            f"candidate-add file {path} must be a list or an object"
        )
    if not isinstance(requests, list):
        raise DataContractError(
            f"candidate-add file {path} 'addCandidates' must be a list"
        )

    normalized: List[Dict[str, str]] = []
    for item in requests:
        if not isinstance(item, dict):
            raise DataContractError(
                f"candidate-add file {path} entries must be objects"
            )
        slot_id = item.get("slotId")
        strategy_id = item.get("strategyId")
        if (
            not isinstance(slot_id, str)
            or not isinstance(strategy_id, str)
            or not slot_id.strip()
            or not strategy_id.strip()
        ):
            raise DataContractError(
                f"candidate-add file {path} entries require non-empty "
                "string 'slotId' and 'strategyId'"
            )
        normalized.append({"slot_id": slot_id.strip(), "strategy_id": strategy_id.strip()})
    return normalized


def _write_candidate_results(path: Path, results: List[Dict[str, Any]]) -> None:
    """Atomically persist operator-action results for audit."""
    payload = {
        "processedAtUtc": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }
    tmp_path = path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.flush()
    tmp_path.replace(path)


def _run_recovery_episode(
    *,
    supervisor: ShadowTournamentSupervisor,
    feed: Any,
    reason: str,
    last_accepted_utc: Optional[datetime],
    timeframe: BarTimeframe,
    max_data_age_ms: Optional[int],
    config: FeedRecoveryConfig,
    symbol: str,
    should_stop: Callable[[], bool],
) -> Dict[str, Any]:
    """Execute one controlled transient recovery episode (fail-closed).

    Returns a result dict {state, reason, resumed_bar}. The supervisor is left
    in the correct state for every outcome:
    - RESUMED:            slots restored to RUNNING; resumed_bar is ready for
                          re-processing in the main loop (resumed from the first
                          unapplied bar, not from an arbitrary reconnect).
    - BUDGET_EXHAUSTED / INVALID_BAR: supervisor halted FEED_RECOVERY_FAILED.
    - OPERATOR_STOP:      slots remain FEED_RECOVERING; the caller's finally-halt
                          seals them as STOPPED (operator terminal cause).
    """
    correlation_id = supervisor.enter_feed_recovery(reason)

    def journal_callback(phase: str, details: Dict[str, Any]) -> None:
        kind = _RECOVERY_PHASE_KIND.get(phase)
        if kind is None:
            return
        supervisor.journal_system_event(
            kind, correlation_id, {"phase": phase, **details}
        )

    result = run_feed_recovery(
        feed=feed,
        config=config,
        last_accepted_utc=last_accepted_utc,
        timeframe=timeframe,
        max_data_age_ms=max_data_age_ms,
        should_stop=should_stop,
        journal_event=journal_callback,
    )

    if result.state == FeedRecoveryState.RESUMED and result.resumed_bar is not None:
        supervisor.exit_feed_recovery(
            correlation_id,
            result.resumed_bar.timestamp_utc.isoformat(),
        )
        resumed_bar = feed_bar_to_synthetic_bar(
            result.resumed_bar, strategy_symbol=symbol
        )
        return {
            "state": result.state.value,
            "reason": result.reason,
            "resumed_bar": resumed_bar,
        }

    if result.state in (
        FeedRecoveryState.BUDGET_EXHAUSTED,
        FeedRecoveryState.INVALID_BAR,
    ):
        supervisor.fail_feed_recovery(
            correlation_id, result.reason or "feed recovery failed"
        )
        return {"state": result.state.value, "reason": result.reason, "resumed_bar": None}

    # OPERATOR_STOP (or any other terminal): supervisor left as-is; the
    # caller's shutdown path seals manifests.
    return {"state": result.state.value, "reason": result.reason, "resumed_bar": None}


def parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ACASH Shadow Alpha Tournament Runtime Entrypoint",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--provider",
        choices=["binance", "stooq"],
        default="binance",
        help="Public market data provider",
    )
    parser.add_argument(
        "--symbol",
        default="BTCUSDT",
        help="Trading pair symbol",
    )
    parser.add_argument(
        "--timeframe",
        type=BarTimeframe,
        choices=list(BarTimeframe),
        default=BarTimeframe.M1,
        help="Candle timeframe",
    )
    parser.add_argument(
        "--storage",
        type=Path,
        default=Path("/data/docker/acash/tournament"),
        help="Storage directory for tournament journals and status",
    )
    parser.add_argument(
        "--api-port",
        type=int,
        default=9103,
        help="Port for read-only HTTP status API (/api/shadow/status)",
    )
    parser.add_argument(
        "--metrics-port",
        type=int,
        default=9102,
        help="Port for Prometheus telemetry metrics (/metrics)",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=2.0,
        help="Seconds between feed polls",
    )
    detected_commit = _detect_git_commit()
    parser.add_argument(
        "--git-commit",
        default=detected_commit,
        required=detected_commit is None,
        help="Current ACASH commit SHA for provenance audit (required in deployment)",
    )
    parser.add_argument(
        "--max-data-age-ms",
        type=int,
        default=65_000,
        help="Max allowed market data staleness in milliseconds before fail-closed halt",
    )
    parser.add_argument(
        "--num-slots",
        type=int,
        default=3,
        help="Number of tournament slot coordinates in [1, 26] (default: 3)",
    )
    parser.add_argument(
        "--auto-mount-infra-candidates",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Default operational layout: mount the deterministic "
            "INFRASTRUCTURE_TEST catalog candidates (A..J) so the default run "
            "exercises an infrastructure-testing tournament (3 candidate slots). "
            "Zero alpha candidates are ever mounted by this flag, and auto-mount "
            "alone does NOT authorize or constitute runtime strategy trading. "
            "Pass --no-auto-mount-infra-candidates to run slot-A-injected alone."
        ),
    )
    parser.add_argument(
        "--infra-mount-count",
        type=int,
        default=3,
        help=(
            "Number of CATALOG candidates to auto-mount (injected strategies are "
            "not counted against this budget). Must be in [1, num-slots]."
        ),
    )
    parser.add_argument(
        "--infra-sizing-policy",
        choices=["auto", "legacy-fixed", "nav-relative"],
        default="auto",
        help=(
            "Signal sizing policy: 'auto' derives NAV_RELATIVE when auto-mounting "
            "catalog candidates (safe notional share) and legacy fixed quantity "
            "otherwise; 'legacy-fixed' always keeps canonical fixed quantities; "
            "'nav-relative' enables safe %%-of-NAV sizing everywhere."
        ),
    )
    parser.add_argument(
        "--nav-sizing-notional-pct",
        type=_parse_nav_sizing_pct,
        default="10.0",
        help="NAV-relative notional share in (0, 100] (default 10%% of virtual NAV).",
    )
    parser.add_argument(
        "--enable-feed-recovery",
        action="store_true",
        default=False,
        help=(
            "EXPLICIT OPT-IN: enable the controlled transient feed-recovery "
            "mechanism. Default OFF — any transient feed connection failure "
            "immediately halts fail-closed with operator resume required. "
            "When enabled, recovery only ever handles transient "
            "FeedConnectionError events inside a bounded attempts / backoff / "
            "bar-wait budget."
        ),
    )
    parser.add_argument(
        "--max-recovery-attempts",
        type=_positive_int,
        default=5,
        help="Max consecutive reconnect attempts per recovery episode (>= 1).",
    )
    parser.add_argument(
        "--recovery-backoff-seconds",
        type=_parse_backoff_seconds,
        default="2,5,10,20,30",
        help="Comma-separated backoff schedule (seconds, each > 0) applied "
        "between recovery attempts (attempt n uses the n-th entry).",
    )
    parser.add_argument(
        "--recovery-poll-interval-seconds",
        type=_non_negative_float,
        default=2.0,
        help="Poll interval (>= 0) while waiting for a bar during a recovery episode.",
    )
    parser.add_argument(
        "--recovery-bar-wait-timeout-seconds",
        type=_positive_float,
        default=90.0,
        help="Monotonic budget (> 0) for the first bar after a successful "
        "reconnect; a timeout consumes that attempt's retry budget.",
    )
    parser.add_argument(
        "--candidate-add-file",
        type=Path,
        default=None,
        help=(
            "Optional JSON file with operator-driven late-join candidates, e.g. "
            '{"addCandidates":[{"slotId":"D","strategyId":"INFRA_TEST_001"}]}. '
            "Edited files are re-read; results are written to "
            "<storage>/<tournament>.candidate-adds.json. Feature is OFF unless "
            "this flag is explicitly provided."
        ),
    )
    return parser.parse_args(args)


def run_tournament(args: argparse.Namespace) -> int:
    logger.info("================================================================")
    logger.info(" ACASH SHADOW ALPHA TOURNAMENT RUNTIME")
    logger.info(" GOVERNANCE: SIMULATED RESEARCH INFRASTRUCTURE ONLY")
    logger.info(" CANONICAL CAPITAL = $0.00 | REAL ORDERS = 0 | NO_REAL_ORDERS = true")
    logger.info("================================================================")

    storage_dir: Path = args.storage
    storage_dir.mkdir(parents=True, exist_ok=True)
    status_file = storage_dir / "status.json"

    # Setup Public Feed
    feed: Any
    data_source: str
    market_domain: str
    if args.provider == "binance":
        feed = BinancePublicKlinesFeed(symbol=args.symbol, timeframe=args.timeframe)
        data_source = feed.provider_id
        market_domain = "SPOT"
    elif args.provider == "stooq":
        feed = StooqCsvFeed(symbol=args.symbol, timeframe=args.timeframe)
        data_source = feed.provider_id
        market_domain = "EQUITY_OR_FX"
    else:
        logger.error("Unsupported provider: %s", args.provider)
        return 1

    # Setup Metrics Registry and Supervisor with explicit real-feed provenance
    metrics_reg = MetricsRegistry()

    sizing_policy, effective_nav_pct = _resolve_sizing(args)
    infra_mount_count = (
        getattr(args, "infra_mount_count", None)
        if bool(getattr(args, "auto_mount_infra_candidates", False))
        else None
    )
    recovery_enabled = bool(getattr(args, "enable_feed_recovery", False))
    candidate_file = getattr(args, "candidate_add_file", None)

    supervisor = create_default_shadow_tournament(
        storage_dir=storage_dir,
        acash_commit_sha=args.git_commit,
        metrics_registry=metrics_reg,
        num_slots=args.num_slots,
        auto_mount_infrastructure_candidates=args.auto_mount_infra_candidates,
        infra_mount_count=infra_mount_count,
        signal_sizing_policy=sizing_policy,
        nav_sizing_notional_pct=effective_nav_pct,
        instrument=args.symbol,
        data_source=data_source,
        market_domain=market_domain,
        max_market_data_age_ms=args.max_data_age_ms,
    )

    # Start Prometheus Metrics Server
    metrics_server = PaperMetricsServer(
        registry=metrics_reg,
        host="0.0.0.0",
        port=args.metrics_port,
    )
    metrics_server.start()
    logger.info("Metrics server listening on port %d", args.metrics_port)

    # Start Read-Only HTTP Status API Server
    api_server = ShadowApiServer(
        supervisor=supervisor,
        host="0.0.0.0",
        port=args.api_port,
        metrics_registry=metrics_reg,
    )
    api_server.start()
    logger.info("Status API server listening on port %d", args.api_port)

    # Signal Handling for Graceful Shutdown
    shutdown_requested = False

    def handle_signal(signum: int, frame: Any) -> None:
        nonlocal shutdown_requested
        logger.info("Received termination signal %d; initiating graceful shutdown...", signum)
        shutdown_requested = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Candidate-add reload flag (SIGHUP is POSIX-only; the file-mtime re-check
    # path below gives Windows an equivalent deterministic operator trigger).
    reload_requested = False

    def handle_sighup(signum: int, frame: Any) -> None:
        nonlocal reload_requested
        reload_requested = True
        logger.info("SIGHUP received; re-reading candidate-add file if configured...")

    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, handle_sighup)

    # Note: argparse types already enforce strict bounds (max_attempts >= 1,
    # poll interval >= 0, bar-wait timeout > 0, backoff values > 0), so the
    # config cannot receive silently-clamped values from the CLI surface.
    recovery_config = FeedRecoveryConfig(
        max_attempts=int(getattr(args, "max_recovery_attempts", 5)),
        backoff_seconds=tuple(getattr(args, "recovery_backoff_seconds", (2.0, 5.0, 10.0, 20.0, 30.0))),
        poll_interval_seconds=float(
            getattr(args, "recovery_poll_interval_seconds", 2.0)
        ),
        bar_wait_timeout_seconds=float(
            getattr(args, "recovery_bar_wait_timeout_seconds", 90.0)
        ),
    )
    recovery_totals = {"success": 0, "failure": 0}

    # Lifecycle Invariant: Connect feed BEFORE starting tournament slots
    logger.info("Connecting to market data feed (%s, %s)...", args.provider, args.symbol)
    try:
        feed.connect()
    except (FeedConnectionError, Exception) as exc:
        logger.error("Feed connection failed on startup: %s. Halting fail-closed.", exc)
        supervisor.record_feed_disconnect(str(exc))
        supervisor.export_status_json(status_file)
        api_server.stop()
        metrics_server.stop()
        return 2

    # Feed connected successfully -> Start tournament slots
    supervisor.start()
    supervisor.export_status_json(status_file)
    logger.info("Tournament %s started. Monitoring feed for %s...", supervisor.tournament_id, args.symbol)

    exit_code = 0

    def _handle_recovery_outcome(
        outcome: Dict[str, Any],
    ) -> Optional[int]:
        """Apply a completed recovery episode's outcome to the tournament.

        Returns an exit code when the runtime must terminate (recovery failed),
        else None to continue the main loop.
        """
        state = outcome["state"]
        if state == FeedRecoveryState.RESUMED.value:
            recovery_totals["success"] += 1
            resumed_bar = outcome["resumed_bar"]
            logger.info(
                "Feed recovery RESUME (%d warnings total, %d failures): re-processing "
                "bar %s from the first unapplied bar.",
                recovery_totals["success"],
                recovery_totals["failure"],
                resumed_bar.timestamp_utc,
            )
            supervisor.process_bar(resumed_bar)
            supervisor.export_status_json(status_file)
            return None

        recovery_totals["failure"] += 1
        reason = outcome["reason"]
        if state == FeedRecoveryState.OPERATOR_STOP.value:
            logger.info("Feed recovery aborted by operator shutdown: %s", reason)
            supervisor.export_status_json(status_file)
            return 0
        if state == FeedRecoveryState.BUDGET_EXHAUSTED.value:
            logger.error("Feed recovery budget exhausted: %s. Halting fail-closed.", reason)
            supervisor.export_status_json(status_file)
            return 5
        if state == FeedRecoveryState.INVALID_BAR.value:
            logger.error("Feed recovery returned an invalid bar: %s. Halting fail-closed.", reason)
            supervisor.export_status_json(status_file)
            return 6
        supervisor.export_status_json(status_file)
        return 2

    def _stage_candidate_file() -> None:
        """Read and stage operator candidate adds when the file changed."""
        nonlocal reload_requested
        if candidate_file is None:
            return
        try:
            mtime = candidate_file.stat().st_mtime
        except OSError:
            return  # file not created yet (operator will provide it)
        if not reload_requested and mtime <= candidate_file_mtime["value"]:
            return
        candidate_file_mtime["value"] = mtime
        reload_requested = False
        try:
            requests = _load_candidate_requests(candidate_file)
        except DataContractError as exc:
            logger.error("Candidate-add file rejected (fail-closed, no adds staged): %s", exc)
            return
        results = []
        for req in requests:
            results.append(
                supervisor.stage_candidate_add(
                    req["slot_id"], req["strategy_id"]
                )
            )
        _write_candidate_results(
            storage_dir / f"{supervisor.tournament_id}.candidate-adds.json",
            results,
        )

    candidate_file_mtime = {"value": 0.0}

    try:
        while not shutdown_requested:
            # Operator-driven candidate adds are staged at the top of each loop
            # and materialized at the next finalized-bar boundary (process_bar).
            if candidate_file is not None:
                _stage_candidate_file()

            try:
                feed_bar = feed.poll_next_bar()

                # --- Unified post-poll freshness gate ---
                # Applied to EVERY poll result (FeedBar or None) before any
                # call to supervisor.process_bar(). This is the canonical
                # M1 Shadow staleness check (65,000 ms policy).
                if feed_bar is not None and args.max_data_age_ms is not None:
                    bar_age_ms = feed_bar.data_age_ms()
                    if bar_age_ms > args.max_data_age_ms:
                        logger.error(
                            "Returned bar is stale: age=%dms > max_data_age_ms=%dms."
                            " Halting fail-closed without processing.",
                            bar_age_ms,
                            args.max_data_age_ms,
                        )
                        supervisor.record_feed_stale(bar_age_ms, args.max_data_age_ms)
                        supervisor.export_status_json(status_file)
                        exit_code = 4
                        break

                if feed_bar is not None:
                    synthetic_bar = feed_bar_to_synthetic_bar(feed_bar, strategy_symbol=args.symbol)
                    results = supervisor.process_bar(synthetic_bar)
                    supervisor.export_status_json(status_file)
                    logger.debug("Processed bar %s (decisions: %s)", synthetic_bar.timestamp_utc, results)
                else:
                    # Inspect feed freshness and connection state when poll returns None
                    feed_status = feed.status()
                    if not feed_status.is_connected:
                        # Transient disconnection: controlled recovery episode
                        # (quiescent — zero bars consumed, zero decisions) or,
                        # when disabled, the legacy fail-closed operator-resume
                        # halt.
                        if recovery_enabled and not supervisor.feed_recovery_active:
                            outcome = _run_recovery_episode(
                                supervisor=supervisor,
                                feed=feed,
                                reason=(
                                    feed_status.last_error
                                    or "Feed connection lost during polling"
                                ),
                                last_accepted_utc=supervisor._last_data_timestamp_utc,
                                timeframe=args.timeframe,
                                max_data_age_ms=args.max_data_age_ms,
                                config=recovery_config,
                                symbol=args.symbol,
                                should_stop=lambda: shutdown_requested,
                            )
                            rc = _handle_recovery_outcome(outcome)
                            if rc is not None:
                                exit_code = rc
                                break
                            continue
                        logger.error("Feed connection lost during polling: %s (fail-closed halt)", feed_status.last_error)
                        supervisor.record_feed_disconnect(feed_status.last_error or "Feed disconnected")
                        supervisor.export_status_json(status_file)
                        exit_code = 2
                        break

                    if feed_status.last_bar_utc is not None and args.max_data_age_ms is not None:
                        if feed_status.data_age_ms > args.max_data_age_ms:
                            logger.error(
                                "Feed data stale: observed %dms > allowed %dms. Fail-closed halt.",
                                feed_status.data_age_ms,
                                args.max_data_age_ms,
                            )
                            supervisor.record_feed_stale(feed_status.data_age_ms, args.max_data_age_ms)
                            supervisor.export_status_json(status_file)
                            exit_code = 4
                            break

            except FeedConnectionError as exc:
                # Transient connection failure: controlled recovery episode or
                # the legacy strict fail-closed halt.
                if recovery_enabled and not supervisor.feed_recovery_active:
                    outcome = _run_recovery_episode(
                        supervisor=supervisor,
                        feed=feed,
                        reason=f"Feed connection failure: {exc}",
                        last_accepted_utc=supervisor._last_data_timestamp_utc,
                        timeframe=args.timeframe,
                        max_data_age_ms=args.max_data_age_ms,
                        config=recovery_config,
                        symbol=args.symbol,
                        should_stop=lambda: shutdown_requested,
                    )
                    rc = _handle_recovery_outcome(outcome)
                    if rc is not None:
                        exit_code = rc
                        break
                    continue
                logger.error("Feed connection failure: %s (fail-closed halt)", exc)
                supervisor.record_feed_disconnect(str(exc))
                supervisor.export_status_json(status_file)
                exit_code = 2
                break
            except FeedContractError as exc:
                logger.error("Feed contract violation: %s (fail-closed halt)", exc)
                supervisor.record_feed_disconnect(str(exc))
                supervisor.export_status_json(status_file)
                exit_code = 3
                break
            except Exception as exc:
                logger.error("Unexpected runtime failure: %s", exc, exc_info=True)
                supervisor.halt(
                    f"Unexpected error: {exc}",
                    terminal_reason=TerminalReason.INTERNAL_ERROR,
                )
                supervisor.export_status_json(status_file)
                exit_code = 1
                break

            time.sleep(args.poll_interval_seconds)

    finally:
        logger.info("Halting tournament, disconnecting feed, and sealing manifests...")
        try:
            feed.disconnect()
        except Exception as exc:
            logger.error("Error disconnecting feed: %s", exc)

        # No-op if already halted (feed disconnect/stale preserved first cause);
        # otherwise records an operator-driven stop (e.g. SIGINT/SIGTERM).
        supervisor.halt(
            "Tournament shutdown complete",
            terminal_reason=TerminalReason.OPERATOR_STOP,
        )
        supervisor.export_status_json(status_file)

        api_server.stop()
        metrics_server.stop()
        logger.info("Shutdown complete. Exit code: %d", exit_code)

    return exit_code


def main() -> None:
    args = parse_args()
    sys.exit(run_tournament(args))


if __name__ == "__main__":
    main()
