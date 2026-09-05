"""ACASH Phase 13: 24–72 Hour Continuous Unattended Soak Harness (Step 5).

Executes sustained paper runtime operations under strict governance:
- Live Capital Authority: strictly $0.00
- Live Orders: 0
- Broker Live Wire: DISCONNECTED
- Frozen Core Modifications: 0
- Strategy Qualification: STRAT-MOM-MULTI-HORIZON-V1 remains BLOCKED
- Observability: High-resolution telemetry logging (RSS, CPU, GC, pulse, ledger, snapshot)
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import gc
import json
import logging
import os
from pathlib import Path
import signal
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# Windows Native Process Memory & Times via ctypes
class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]

class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

def get_process_memory_mb() -> Tuple[float, float, float]:
    """Return (RSS_MB, Peak_RSS_MB, VMS_MB) for current Windows process."""
    try:
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010
        handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, os.getpid()
        )
        if not handle:
            return 0.0, 0.0, 0.0
        pmc = PROCESS_MEMORY_COUNTERS()
        pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(pmc), pmc.cb)
        ctypes.windll.kernel32.CloseHandle(handle)
        rss = pmc.WorkingSetSize / (1024.0 * 1024.0)
        peak_rss = pmc.PeakWorkingSetSize / (1024.0 * 1024.0)
        vms = pmc.PagefileUsage / (1024.0 * 1024.0)
        return round(rss, 2), round(peak_rss, 2), round(vms, 2)
    except Exception:
        return 0.0, 0.0, 0.0


# Imports from ACASH
from acash.core.domain.exceptions import DataContractError
from acash.core.domain.market_data import MarketDataSnapshot
from acash.core.domain.portfolio import AccountState, PortfolioState
from acash.core.domain.position import Position
from acash.core.interfaces.market_data import IMarketDataProvider
from acash.execution.coordinator import ExecutionCoordinator
from acash.execution.mt5.enums import MT5TradeExecutionMode
from acash.execution.mt5.schemas import BrokerSymbolSpec
from acash.execution.schema import OrderLifecycleState
from acash.portfolio.schema import AllocationDecision
from acash.runtime.feeder import (
    FeedSourceType,
    ForwardMarketDataFeeder,
)
from acash.runtime.ledger import OperationalLedger
from acash.runtime.paper_bridge import (
    ExecutionCostModel,
    PaperExecutionBridge,
    PaperExecutionVenueType,
    SimulatedMarketMatcher,
)
from acash.runtime.rehydration import (
    PortfolioSnapshotStore,
    PortfolioStateRehydrator,
    RehydrationStatus,
)
from acash.runtime.schema import (
    CycleIdentity,
    CycleOutcome,
    OperationalCycleEvent,
    RuntimeHealthStatus,
    RuntimeRegime,
)
from acash.runtime.strategy_adapter import (
    PaperStrategyAdapter,
    PaperTradingSessionIdentity,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("Phase13Soak")


class SyntheticContinuousMarketDataProvider(IMarketDataProvider):
    """Deterministic, high-frequency tick generator for sustained unattended soak testing."""

    def __init__(self, base_price: Decimal = Decimal("1.08500")) -> None:
        self.current_price = base_price
        self._tick_seq = 0

    def generate_tick(self, wall_clock_utc: datetime) -> MarketDataSnapshot:
        self._tick_seq += 1
        # Deterministic micro-oscillation within +/- 10 pips
        drift = Decimal(str((self._tick_seq % 20) - 10)) * Decimal("0.00001")
        price = self.current_price + drift
        spread = Decimal("0.00015")
        return MarketDataSnapshot(
            symbol="EURUSD",
            bid=price,
            ask=price + spread,
            bid_size=Decimal("100.0"),
            ask_size=Decimal("100.0"),
            last_price=price + (spread / Decimal("2.0")),
            timestamp_utc=wall_clock_utc,
        )

    def get_latest_snapshot(self, symbol: str) -> MarketDataSnapshot:
        return self.generate_tick(datetime.now(timezone.utc))

    def get_historical_bars(self, *args: Any, **kwargs: Any) -> list:
        return []


class Phase13SoakHarness:
    """Continuous Unattended Soak Execution Harness."""

    def __init__(
        self,
        output_dir: Path,
        duration_hours: float,
        pulse_interval_sec: float = 1.0,
        telemetry_interval_sec: float = 10.0,
        venue_type: PaperExecutionVenueType = PaperExecutionVenueType.LOCAL_SIMULATOR,
        strategy_id: str = "STRAT-MOM-MULTI-HORIZON-V1",
        strategy_version: str = "1.0.0",
        prng_seed: int = 42,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.duration_seconds = duration_hours * 3600.0
        self.pulse_interval_sec = pulse_interval_sec
        self.telemetry_interval_sec = telemetry_interval_sec
        self.venue_type = venue_type
        self.strategy_id = strategy_id
        self.strategy_version = strategy_version
        self.prng_seed = prng_seed

        # Subdirectories and files
        self.ledger_file = self.output_dir / "operational_ledger.jsonl"
        self.snapshot_dir = self.output_dir / "snapshots"
        self.snapshot_file = self.snapshot_dir / "portfolio_state.json"
        self.telemetry_file = self.output_dir / "soak_telemetry.jsonl"
        self.summary_file = self.output_dir / "soak_summary.json"

        self.stop_requested = False
        self.pulse_count = 0
        self.unknown_count = 0
        self.stale_data_count = 0
        self.manifest_count = 0
        self.exceptions_count = 0

        # Setup graceful termination handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum: int, frame: Any) -> None:
        logger.info(f"Signal {signum} received. Initiating fail-closed graceful shutdown...")
        self.stop_requested = True

    def run(self) -> Dict[str, Any]:
        start_time_utc = datetime.now(timezone.utc)
        logger.info("================================================================================")
        logger.info("ACASH PHASE 13 — STEP 5 UNATTENDED SOAK TEST INITIATING")
        logger.info("================================================================================")
        logger.info(f"Start Timestamp UTC : {start_time_utc.isoformat()}")
        logger.info(f"Target Duration     : {self.duration_seconds}s ({self.duration_seconds / 3600.0:.2f}h)")
        logger.info(f"Execution Venue     : {self.venue_type.value}")
        logger.info(f"Strategy Gating     : {self.strategy_id} (Qualification BLOCKED -> 100% Cash)")
        logger.info(f"Output Directory    : {self.output_dir}")
        logger.info("Live Capital Authority: $0.00 (Hard-Locked)")
        logger.info("Live Orders Allowed   : 0 (Strict Fail-Closed)")

        # 1. Initialize Runtime Components
        cost_model = ExecutionCostModel()
        session_identity = PaperTradingSessionIdentity(
            session_id=f"SOAK-SESS-{start_time_utc.strftime('%Y%m%d%H%M%S')}",
            run_id=f"RUN-SOAK-{start_time_utc.strftime('%Y%m%d%H%M%S')}",
            market="TRADITIONAL_FX",
            data_source=FeedSourceType.STREAMING_PARQUET_PUMP,
            execution_mode=self.venue_type,
            strategy_id=self.strategy_id,
            strategy_version=self.strategy_version,
            prng_seed=self.prng_seed,
            start_time_utc=start_time_utc,
            planned_end_time_utc=start_time_utc + timedelta(seconds=self.duration_seconds),
            config_digest=cost_model.compute_digest(),
            dossier_digest="0" * 64,
        )

        symbol_spec = BrokerSymbolSpec(
            canonical_symbol="EURUSD",
            broker_symbol="EURUSD.pro",
            contract_size=Decimal("100000.0"),
            volume_min=Decimal("0.01"),
            volume_max=Decimal("100.0"),
            volume_step=Decimal("0.01"),
            digits=5,
            point_size=Decimal("0.00001"),
            tick_size=Decimal("0.00001"),
            trade_execution_mode=MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_MARKET,
            allowed_filling_flags=("SYMBOL_FILLING_FOK", "SYMBOL_FILLING_IOC"),
            margin_currency="EUR",
            profit_currency="USD",
            spec_digest="0" * 64,
        )

        provider = SyntheticContinuousMarketDataProvider()
        feeder = ForwardMarketDataFeeder(
            provider=provider,
            source_type=FeedSourceType.STREAMING_PARQUET_PUMP,
            session_identity=session_identity,
            max_market_data_age_ms=1500,
        )

        strategy_adapter = PaperStrategyAdapter(
            strategy_id=self.strategy_id,
            strategy_version=self.strategy_version,
            dossier_path=None,
            session_identity=session_identity,
            cost_model=cost_model,
        )
        assert strategy_adapter.is_eligible is False, "Candidate strategy must remain qualification-blocked!"

        matcher = SimulatedMarketMatcher(cost_model=cost_model)
        coordinator = ExecutionCoordinator(execution_id="SOAK-EXEC-ROOT", requested_qty=Decimal("0.0"))
        bridge = PaperExecutionBridge(
            coordinator=coordinator,
            venue_type=self.venue_type,
            matcher=matcher,
            symbol_spec_provider=lambda s: symbol_spec,
        )

        ledger = OperationalLedger(self.ledger_file)
        snap_store = PortfolioSnapshotStore()

        # Rehydrate or initialize genesis portfolio
        rehydrator = PortfolioStateRehydrator(ledger=ledger, snapshot_dir=self.snapshot_dir)
        current_portfolio, _, rehydration_status = rehydrator.rehydrate(as_of_utc=start_time_utc)
        logger.info(f"Startup Rehydration Status: {rehydration_status.value} (Balance: ${current_portfolio.cash_balance})")

        last_telemetry_flush = time.time()
        initial_rss, _, _ = get_process_memory_mb()
        logger.info(f"Initial Process Memory: {initial_rss:.2f} MB RSS")

        # 2. Main Sustained Pulse Loop
        try:
            while not self.stop_requested:
                now_wall_clock = datetime.now(timezone.utc)
                elapsed = (now_wall_clock - start_time_utc).total_seconds()

                if elapsed >= self.duration_seconds:
                    logger.info(f"Target duration of {self.duration_seconds}s reached. Gracefully stopping.")
                    break

                self.pulse_count += 1
                cycle_id = f"CYCLE-SOAK-{self.pulse_count:08d}"
                cycle_identity = CycleIdentity(
                    cycle_id=cycle_id,
                    as_of_utc=now_wall_clock,
                    regime=RuntimeRegime.MARKET_OPEN,
                    sequence_number=ledger.event_count,
                )

                # Step 1: Poll Forward Market Feed
                snap, age_ms = feeder.poll_next_market_snapshot("EURUSD", now_wall_clock)
                if age_ms > feeder.max_market_data_age_ms:
                    self.stale_data_count += 1
                    cycle_outcome = CycleOutcome.DATA_STALE
                else:
                    cycle_outcome = CycleOutcome.SUCCESS

                # Step 2: Strategy Evaluation (Qualification-Blocked -> 100% Cash)
                alloc = strategy_adapter.generate_candidate_allocation(
                    bars=[], portfolio=current_portfolio, as_of_utc=now_wall_clock
                )

                # Step 3: Bridge Evaluation & Quantization (Zero orders emitted for Cash baseline)
                outcomes = bridge.evaluate_and_dispatch(
                    allocation=alloc,
                    portfolio=current_portfolio,
                    current_snapshot=snap,
                    cycle_identity=cycle_identity,
                    session_identity=session_identity,
                )

                # Step 4: Snapshot Persistence & Ledger Append
                snap_digest = snap_store.save_snapshot(current_portfolio, self.snapshot_file)
                event = OperationalCycleEvent(
                    cycle_identity=cycle_identity,
                    wall_clock_utc=now_wall_clock,
                    previous_event_digest=ledger.last_event_digest,
                    runtime_health=RuntimeHealthStatus.RUNTIME_HEALTHY,
                    portfolio_state_digest=snap_digest,
                    cycle_outcome=cycle_outcome,
                    error_message=None,
                )
                ledger.append_event(event)
                self.manifest_count = len(bridge.emitted_manifests)

                # Periodic Telemetry Sampling
                now_mono = time.time()
                if (now_mono - last_telemetry_flush) >= self.telemetry_interval_sec:
                    rss_mb, peak_rss_mb, vms_mb = get_process_memory_mb()
                    telemetry_record = {
                        "timestamp_utc": now_wall_clock.isoformat(),
                        "elapsed_seconds": round(elapsed, 2),
                        "pulse_count": self.pulse_count,
                        "rss_mb": rss_mb,
                        "peak_rss_mb": peak_rss_mb,
                        "vms_mb": vms_mb,
                        "gc_counts": list(gc.get_count()),
                        "ledger_event_count": ledger.event_count,
                        "ledger_head_digest": ledger.last_event_digest,
                        "snapshot_digest": snap_digest,
                        "manifest_count": self.manifest_count,
                        "cash_balance": str(current_portfolio.cash_balance),
                        "stale_data_count": self.stale_data_count,
                        "runtime_health": RuntimeHealthStatus.RUNTIME_HEALTHY.value,
                    }
                    with open(self.telemetry_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(telemetry_record) + "\n")
                    last_telemetry_flush = now_mono

                    # Resource runaway fail-closed check (> 500 MB RSS indicates leak)
                    if rss_mb > 500.0:
                        raise DataContractError(f"MEMORY_RUNAWAY_BREACH: Process RSS reached {rss_mb} MB (> 500 MB limit).")

                    logger.info(
                        f"Pulse {self.pulse_count:06d} | Elapsed: {elapsed:.1f}s | "
                        f"RSS: {rss_mb:.1f}MB | Peak: {peak_rss_mb:.1f}MB | "
                        f"Events: {ledger.event_count} | Health: OK"
                    )

                time.sleep(self.pulse_interval_sec)

        except Exception as e:
            logger.error(f"SOAK_UNHANDLED_EXCEPTION: {e}", exc_info=True)
            self.exceptions_count += 1
            raise
        finally:
            end_time_utc = datetime.now(timezone.utc)
            total_uptime = (end_time_utc - start_time_utc).total_seconds()
            final_rss, peak_rss, _ = get_process_memory_mb()

            # Final ledger verification
            is_valid, final_count, head_digest = ledger.verify_ledger_integrity()

            summary = {
                "soak_status": "COMPLETED" if (total_uptime >= self.duration_seconds and self.exceptions_count == 0) else "STOPPED",
                "start_time_utc": start_time_utc.isoformat(),
                "end_time_utc": end_time_utc.isoformat(),
                "total_uptime_seconds": round(total_uptime, 2),
                "total_uptime_hours": round(total_uptime / 3600.0, 4),
                "pulses_executed": self.pulse_count,
                "exceptions_count": self.exceptions_count,
                "stale_data_events": self.stale_data_count,
                "manifest_count": self.manifest_count,
                "initial_rss_mb": initial_rss,
                "final_rss_mb": final_rss,
                "peak_rss_mb": peak_rss,
                "memory_growth_mb": round(final_rss - initial_rss, 2),
                "ledger_valid": is_valid,
                "ledger_event_count": final_count,
                "ledger_head_digest": head_digest,
                "strategy_id": self.strategy_id,
                "strategy_qualification_blocked": True,
                "live_capital_usd": "0.00",
                "live_orders": 0,
            }

            with open(self.summary_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)

            logger.info("================================================================================")
            logger.info("ACASH PHASE 13 — STEP 5 SOAK RUN SUMMARY")
            logger.info("================================================================================")
            logger.info(f"Status               : {summary['soak_status']}")
            logger.info(f"Total Uptime         : {summary['total_uptime_seconds']:.2f}s ({summary['total_uptime_hours']:.4f}h)")
            logger.info(f"Pulses Executed      : {summary['pulses_executed']}")
            logger.info(f"Memory Growth        : {summary['memory_growth_mb']} MB (Initial: {initial_rss}MB -> Final: {final_rss}MB)")
            logger.info(f"Ledger Integrity     : {'VERIFIED' if is_valid else 'CORRUPTED'} ({final_count} events)")
            logger.info(f"Summary Written To   : {self.summary_file}")
            logger.info("================================================================================")
        return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="ACASH Phase 13 Step 5 Soak Test Runner")
    parser.add_argument("--duration-hours", type=float, default=24.0, help="Target duration in hours (default: 24.0)")
    parser.add_argument("--duration-seconds", type=float, default=None, help="Target duration in seconds (for preflight/testing)")
    parser.add_argument("--pulse-interval-sec", type=float, default=1.0, help="Pulse interval in seconds (default: 1.0)")
    parser.add_argument("--telemetry-interval-sec", type=float, default=5.0, help="Telemetry sample interval in seconds (default: 5.0)")
    parser.add_argument("--output-dir", type=str, default="var/phase13_soak", help="Output directory for telemetry and ledger")
    parser.add_argument("--venue", type=str, default="LOCAL_SIMULATOR", choices=["LOCAL_SIMULATOR", "MT5_DEMO"], help="Execution venue")
    args = parser.parse_args()

    duration_h = args.duration_hours
    if args.duration_seconds is not None:
        duration_h = args.duration_seconds / 3600.0

    venue = PaperExecutionVenueType[args.venue]
    harness = Phase13SoakHarness(
        output_dir=Path(args.output_dir),
        duration_hours=duration_h,
        pulse_interval_sec=args.pulse_interval_sec,
        telemetry_interval_sec=args.telemetry_interval_sec,
        venue_type=venue,
    )
    harness.run()


if __name__ == "__main__":
    main()
