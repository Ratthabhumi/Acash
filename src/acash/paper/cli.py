"""ACASH Paper Trading - E3.5 Operational CLI (``python -m acash.paper``).

Commands:
    run        Run (or resume) a real-feed paper session with the E3 black-box
               flight recorder active. NEVER places real orders - PAPER ONLY.
    status     Print operational status for a session (journal, supervisor
               stats, portfolio) - never a profitability dashboard.
    integrity  Run journal integrity + reconciliation check for a session.
    review     Build the E3.5 audit review package (OBSERVED/MODEL/DERIVED).

GOVERNANCE (E3.5):
==================
- Every run is PAPER_ONLY by construction; there is no LIVE mode in this CLI.
- Real-feed bars are EXECUTION/PAPER INFRASTRUCTURE ONLY and are NOT MACRO-001
  research evidence.
- A daily loss ceiling activates a kill switch that hard-stops decisions.
- Journal failure raises DataContractError (fail-closed).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from acash.core.domain.enums import BarTimeframe
from acash.core.domain.exceptions import DataContractError

# Worst-case default freshness horizons per timeframe (ms). Real providers can
# lag; these defaults are deliberately conservative: they only bound how old a
# bar may be before it is refused (never how fresh data claims to be).
_DEFAULT_MAX_AGE_MS: Dict[BarTimeframe, int] = {
    BarTimeframe.M1: 65_000,
    BarTimeframe.M5: 315_000,
    BarTimeframe.M15: 915_000,
    BarTimeframe.H1: 3_660_000,
    BarTimeframe.H4: 14_460_000,
    BarTimeframe.D1: 86_460_000,
}


def _provider_for(
    provider: str, symbol: str, timeframe: BarTimeframe
) -> Any:
    """Construct the requested real-feed provider (credential-free only)."""
    from acash.paper.feed import BinancePublicKlinesFeed, StooqCsvFeed

    if provider == "binance":
        return BinancePublicKlinesFeed(symbol=symbol, timeframe=timeframe)
    if provider == "stooq":
        return StooqCsvFeed(symbol=symbol, timeframe=timeframe)
    raise ValueError(f"unsupported provider: {provider!r} (use binance|stooq)")


def _json_default(obj: Any) -> Any:
    """JSON serializer fallback for datetime/Decimal values."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _dump_payload(payload: Dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, default=_json_default))


def _run_session(
    args: argparse.Namespace,
    *,
    resume: bool,
) -> Dict[str, Any]:
    from acash.paper.feed import FeedConnectionError, FeedContractError
    from acash.paper.health import PaperHealthMonitor
    from acash.paper.manifest import PaperMode
    from acash.paper.runner import PaperSessionConfig, PaperSessionRunner
    from acash.paper.session import PaperFeedSessionSupervisor
    from acash.paper.shutdown import BoundedGracefulShutdown

    storage = Path(args.storage)
    storage.mkdir(parents=True, exist_ok=True)

    journal_path = storage / f"{args.session_id}.journal.jsonl"
    snapshot_path = storage / f"{args.session_id}.snapshots.jsonl"

    max_age = (
        int(args.max_market_data_age_ms)
        if args.max_market_data_age_ms is not None
        else _DEFAULT_MAX_AGE_MS[args.timeframe]
    )

    config = PaperSessionConfig(
        session_id=args.session_id,
        strategy_id="INFRA-TEST-MOMENTUM-SYNTHETIC-001",
        strategy_version="1.0.0",
        instrument="SYNTH-USD",
        initial_cash=Decimal(args.initial_cash),
        max_position_units=Decimal(args.max_position_units),
        max_notional=Decimal(args.max_notional),
        max_daily_loss=Decimal(args.max_daily_loss),
        fill_slippage_bps=Decimal(args.fill_slippage_bps),
        fill_commission_per_unit=Decimal(args.fill_commission_per_unit),
        prng_seed=args.prng_seed,
        git_commit=args.git_commit,
        component_version="0.1.0-e35",
        journal_path=journal_path,
        snapshot_path=snapshot_path,
        mode=PaperMode.PAPER_ONLY,
        data_source=f"feed:{args.provider}",
        market_domain=args.market_domain,
        max_market_data_age_ms=max_age,
    )

    runner = PaperSessionRunner(config)
    if resume and journal_path.exists():
        recovery_cid = runner.recover()
        print(json.dumps({"event": "RECOVERED", "correlation_id": recovery_cid}))

    health = PaperHealthMonitor(
        journal=runner.journal,
        session_id=config.session_id,
        component_version="0.1.0-e35",
    )
    feed = _provider_for(args.provider, args.symbol, args.timeframe)
    supervisor = PaperFeedSessionSupervisor(
        feed=feed,
        runner=runner,
        health=health,
        journal=runner.journal,
        strategy_symbol="SYNTH-USD",
    )

    runner.start()

    metrics_server = None
    metrics_port = getattr(args, "metrics_port", 9102)
    metrics_host = getattr(args, "metrics_host", "0.0.0.0")
    if metrics_port > 0:
        from acash.paper.metrics import PaperMetricsServer, build_operational_metrics
        from acash.paper.window import WindowState

        def _resolve_window_state() -> str:
            for candidate in (storage.parent, storage):
                w_dir = candidate / "windows"
                if w_dir.exists():
                    for marker_file in sorted(w_dir.glob("*.state.json")):
                        try:
                            data = json.loads(marker_file.read_text(encoding="utf-8"))
                            st = data.get("state")
                            if st in ("QUIESCENT", "OPEN", "SEALED", "VOID"):
                                return st
                        except Exception:
                            pass
            return WindowState.QUIESCENT.value

        session_started_at = datetime.now(timezone.utc)

        def _collect() -> Any:
            uptime = max(
                0.0,
                (datetime.now(timezone.utc) - session_started_at).total_seconds(),
            )
            violations = runner.journal.verify_integrity()
            integrity_status = "PASS" if not violations else "FAIL"
            return build_operational_metrics(
                event_count=runner.journal.event_count,
                journal_integrity_status=integrity_status,
                window_state=_resolve_window_state(),
                feed_failure_events=supervisor.stats.disconnect_count,
                auto_recovery_used=False,
                uptime_seconds=uptime,
            )

        metrics_server = PaperMetricsServer(
            registry=_collect,
            host=metrics_host,
            port=metrics_port,
        )
        metrics_server.start()

    try:
        supervisor.connect()
    except FeedConnectionError as exc:
        print(
            json.dumps(
                {
                    "event": "FEED_CONNECT_FAILED",
                    "session_id": config.session_id,
                    "reason": str(exc)[:200],
                }
            ),
            file=sys.stderr,
        )

    max_steps = args.max_polls
    step = 0
    shutdown_requested = False
    # Bounded SIGTERM/SIGINT handler: on a graceful-stop request the loop
    # breaks, disconnect() + stop() seal the manifest within the grace window
    # (D16.1); exceeding the grace bound exits non-zero (fail-closed).
    shutdown_ctrl = BoundedGracefulShutdown(grace_seconds=10.0)
    try:
        shutdown_ctrl.install()
        while max_steps is None or step < max_steps:
            if shutdown_ctrl.shutdown_requested:
                shutdown_requested = True
                break
            step += 1
            if supervisor.stats.halted:
                # In halted state (fail-closed, D6.1), no decisions made, no bars admitted.
                if args.poll_interval_ms > 0:
                    time.sleep(args.poll_interval_ms / 1000.0)
                continue
            try:
                supervisor.step_once()
            except FeedConnectionError as exc:
                # Halt: feeds never make decisions on disconnected data.
                print(
                    json.dumps(
                        {
                            "event": "FEED_DISCONNECTED",
                            "session_id": config.session_id,
                            "reason": str(exc)[:200],
                        }
                    ),
                    file=sys.stderr,
                )
                continue
            except FeedContractError as exc:
                raise DataContractError(
                    f"Feed contract violated (fail-closed): {exc}"
                ) from exc
            if args.poll_interval_ms > 0:
                time.sleep(args.poll_interval_ms / 1000.0)
    finally:
        shutdown_ctrl.restore()
        if metrics_server is not None:
            metrics_server.stop()

    supervisor.disconnect()
    manifest = runner.stop()

    exit_code = shutdown_ctrl.resolve()
    _dump_payload(
        {
            "event": "SESSION_COMPLETE",
            "session_id": config.session_id,
            "shutdown_requested": shutdown_requested,
            "graceful_stop_exit_code": exit_code,
            "manifest": manifest.model_dump(),
            "supervisor_stats": supervisor.stats.to_dict(),
        }
    )
    if exit_code != 0:
        sys.exit(exit_code)
    return {"session_id": config.session_id, "manifest": manifest.model_dump()}


def _status_session(args: argparse.Namespace) -> Dict[str, Any]:
    from acash.paper.journal import PaperEventJournal
    from acash.paper.reconcile import PaperReconciliationEngine

    storage = Path(args.storage)
    journal_path = storage / f"{args.session_id}.journal.jsonl"
    if not journal_path.exists():
        raise FileNotFoundError(f"no journal found at {journal_path}")

    journal = PaperEventJournal(
        session_id=args.session_id,
        persistence_path=journal_path,
        git_commit="cli-status",
        component_version="0.1.0-e35",
    )
    events = journal.read_all()
    integrity_violations = journal.verify_integrity()
    recon = PaperReconciliationEngine(
        session_id=args.session_id, journal=journal
    ).run_full_reconciliation()

    result: Dict[str, Any] = {
        "session_id": args.session_id,
        "event_count": len(events),
        "journal_integrity": "PASS" if not integrity_violations else "FAIL",
        "integrity_violations": len(integrity_violations),
        "reconciliation_status": recon.status.value,
        "reconciliation_violations": recon.total_violations,
    }
    print(json.dumps(result, indent=2))
    return result


def _integrity_session(args: argparse.Namespace) -> Dict[str, Any]:
    from acash.paper.journal import PaperEventJournal

    storage = Path(args.storage)
    journal_path = storage / f"{args.session_id}.journal.jsonl"
    if not journal_path.exists():
        raise FileNotFoundError(f"no journal found at {journal_path}")

    journal = PaperEventJournal(
        session_id=args.session_id,
        persistence_path=journal_path,
        git_commit="cli-integrity",
        component_version="0.1.0-e35",
    )
    violations = journal.verify_integrity()
    result = {
        "session_id": args.session_id,
        "status": "PASS" if not violations else "FAIL",
        "violations": violations,
    }
    print(json.dumps(result, indent=2))
    return result


def _review_session(args: argparse.Namespace) -> Dict[str, Any]:
    from acash.paper.journal import PaperEventJournal
    from acash.paper.manifest import PaperSessionManifest
    from acash.paper.review import build_review_package
    from acash.paper.runner import PaperPortfolioState
    from acash.paper.snapshot import DailySnapshotStore

    storage = Path(args.storage)
    journal_path = storage / f"{args.session_id}.journal.jsonl"
    manifest_path = storage / f"{args.session_id}.manifest.json"
    snapshot_path = storage / f"{args.session_id}.snapshots.jsonl"

    if not journal_path.exists():
        raise FileNotFoundError(f"no journal found at {journal_path}")
    if not manifest_path.exists():
        raise FileNotFoundError(f"no sealed manifest found at {manifest_path}")
    if not snapshot_path.exists():
        raise FileNotFoundError(f"no snapshots file found at {snapshot_path}")

    journal = PaperEventJournal(
        session_id=args.session_id,
        persistence_path=journal_path,
        git_commit="cli-review",
        component_version="0.1.0-e35",
    )
    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = PaperSessionManifest.model_validate_json(fh.read())

    # Reconstruct portfolio summary from the sealed manifest (authoritative post-run).
    summary = manifest.final_portfolio_summary
    portfolio = PaperPortfolioState(
        cash=Decimal(str(summary["cash"])),
        position=Decimal(str(summary.get("position", "0"))),
        avg_entry_price=Decimal(str(summary.get("avg_entry_price", "0"))),
        realized_pnl=Decimal(str(summary.get("realized_pnl", "0"))),
        total_fees=Decimal(str(summary.get("total_fees", "0"))),
        trade_count=int(summary.get("trade_count", 0)),
        order_count=int(summary.get("order_count", 0)),
        rejected_order_count=int(summary.get("rejected_order_count", 0)),
    )

    snapshots = DailySnapshotStore(snapshot_path).read_all()
    package = build_review_package(
        session_id=args.session_id,
        journal=journal,
        manifest=manifest,
        portfolio=portfolio,
        snapshots=snapshots,
    )

    result: Dict[str, Any] = {
        "package_id": package.package_id,
        "session_id": package.session_id,
        "generated_at_utc": package.generated_at_utc.isoformat(),
        "item_count": len(package.items),
        "sections": {
            section: [i.to_dict() for i in items]
            for section, items in package.sections().items()
        },
    }
    print(json.dumps(result, indent=2))
    return result


def _add_run_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--session-id", default=None, help="Session identifier (auto-generated if omitted)")
    parser.add_argument(
        "--provider",
        choices=["binance", "stooq"],
        required=True,
        help="Credential-free real market data provider (binance|stooq).",
    )
    parser.add_argument(
        "--symbol",
        required=True,
        help="Provider symbol, e.g. BTCUSDT (binance) or eurusd (stooq).",
    )
    parser.add_argument(
        "--timeframe",
        choices=[tf.value for tf in BarTimeframe],
        default=BarTimeframe.M1.value,
        help="Bar timeframe (binance supports all; stooq is D1 only).",
    )
    parser.add_argument("--storage", default="var/paper", help="Storage root for journals/snapshots.")
    parser.add_argument("--initial-cash", default="100000", help="Paper initial cash.")
    parser.add_argument("--max-position-units", default="10", help="Max open position (units).")
    parser.add_argument("--max-notional", default="500000", help="Max position notional.")
    parser.add_argument("--max-daily-loss", default="5000", help="Daily loss ceiling (kill switch).")
    parser.add_argument("--fill-slippage-bps", default="0.5", help="Simulated fill slippage (bps).")
    parser.add_argument("--fill-commission-per-unit", default="7.0", help="Commission per unit.")
    parser.add_argument("--prng-seed", default=42, type=int, help="Deterministic PRNG seed.")
    parser.add_argument("--git-commit", default="unknown", help="Repository commit for manifest lineage.")
    parser.add_argument("--market-domain", default="SPOT", help="Market domain label (SPOT|FX|...).")
    parser.add_argument("--max-polls", default=None, type=int, help="Max poll steps (run loop).")
    parser.add_argument("--poll-interval-ms", default=1000, type=int, help="Milliseconds between polls.")
    parser.add_argument(
        "--max-market-data-age-ms",
        default=None,
        type=int,
        help="Freshness horizon in ms (default derived from timeframe).",
    )
    parser.add_argument(
        "--metrics-host",
        default="0.0.0.0",
        help="Host to bind the Prometheus /metrics listener (default: 0.0.0.0).",
    )
    parser.add_argument(
        "--metrics-port",
        default=9102,
        type=int,
        help="Port to bind the Prometheus /metrics listener (default: 9102, 0 to disable).",
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="acash.paper", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run (or resume) a real-feed paper session.")
    _add_run_args(run_p)
    run_p.add_argument("--resume", action="store_true", help="Resume an existing session journal.")

    status_p = sub.add_parser("status", help="Operational status for a session.")
    status_p.add_argument("--session-id", required=True)
    status_p.add_argument("--storage", default="var/paper")

    integrity_p = sub.add_parser("integrity", help="Journal integrity + reconciliation check.")
    integrity_p.add_argument("--session-id", required=True)
    integrity_p.add_argument("--storage", default="var/paper")

    review_p = sub.add_parser("review", help="Build the E3.5 audit review package for a sealed session.")
    review_p.add_argument("--session-id", required=True)
    review_p.add_argument("--storage", default="var/paper")

    args = parser.parse_args(argv)

    if args.command == "run":
        if args.session_id is None:
            args.session_id = f"E3.5-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        args.timeframe = BarTimeframe(args.timeframe)
        _run_session(args, resume=args.resume)
    elif args.command == "status":
        _status_session(args)
    elif args.command == "integrity":
        _integrity_session(args)
    elif args.command == "review":
        _review_session(args)
    else:
        parser.print_help()
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())