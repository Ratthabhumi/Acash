"""ACASH Paper Trading — Shadow Alpha Tournament CLI Entrypoint.

Command:
    python -m acash.paper.tournament_cli [options]

GOVERNANCE:
- SHADOW / SIMULATED RESEARCH INFRASTRUCTURE ONLY — NOT Paper GO / NOT Live
- NO_REAL_ORDERS=True | CANONICAL_CAPITAL_USD=$0.00
- Credential-free feed only (Binance public klines / Stooq CSV)
- Fail-closed on feed disconnect or stale data (zero automatic reconnect)
- Graceful shutdown with journal & manifest sealing on SIGINT/SIGTERM
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

from acash.core.domain.enums import BarTimeframe
from acash.paper.feed import (
    BinancePublicKlinesFeed,
    FeedConnectionError,
    FeedContractError,
    StooqCsvFeed,
    feed_bar_to_synthetic_bar,
)
from acash.paper.metrics import MetricsRegistry, PaperMetricsServer
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
    supervisor = create_default_shadow_tournament(
        storage_dir=storage_dir,
        acash_commit_sha=args.git_commit,
        metrics_registry=metrics_reg,
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

    try:
        while not shutdown_requested:
            try:
                feed_bar = feed.poll_next_bar()
                if feed_bar is not None:
                    synthetic_bar = feed_bar_to_synthetic_bar(feed_bar, strategy_symbol=args.symbol)
                    results = supervisor.process_bar(synthetic_bar)
                    supervisor.export_status_json(status_file)
                    logger.debug("Processed bar %s (decisions: %s)", synthetic_bar.timestamp_utc, results)
                else:
                    # Inspect feed freshness and connection state even when poll returns None
                    feed_status = feed.status()
                    if not feed_status.is_connected:
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
                supervisor.halt(f"Unexpected error: {exc}")
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

        supervisor.halt("Tournament shutdown complete")
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
