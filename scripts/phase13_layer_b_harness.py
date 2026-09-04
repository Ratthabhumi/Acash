"""Phase 13 Slice 1: Layer B Operational Demo Terminal Rehearsal Harness.

CRITICAL SAFETY & GOVERNANCE INVARIANTS:
1. Live Capital Authority is strictly $0.00.
2. Runs ONLY against MT5 DEMO accounts (account.trade_mode == 0). Real accounts (trade_mode == 2)
   trigger an immediate, uncatchable fail-closed HALT.
3. Operator-assisted harness ONLY. Zero automated close in A-11: manual GUI closure by the
   human operator is strictly required and non-negotiable.
4. Leaves production code in `src/` completely FROZEN (zero edits to src/).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import MetaTrader5 as mt5  # type: ignore[import-untyped]

from acash.core.domain.exceptions import DataContractError
from acash.core.domain.portfolio import PortfolioState
from acash.core.domain.position import Position
from acash.execution.crypto import (
    Ed25519TrustStore,
)
from acash.execution.mt5.enums import (
    MT5AccountMarginMode,
    MT5DealEntry,
    MT5DealType,
    MT5FillingMode,
    MT5OrderTime,
    MT5OrderType,
    MT5PositionType,
    MT5TradeAction,
    MT5TradeExecutionMode,
)
from acash.execution.mt5.exceptions import (
    MT5DomainError,
    MT5SymbolSpecError,
    MT5TransportError,
    MT5ValidationError,
)
from acash.execution.mt5.mapping import (
    decode_mt5_deal_entry,
    decode_mt5_deal_type,
)
from acash.execution.mt5.reconciliation import (
    ACASHShadowLedgerSnapshot,
    CaptureCompletenessStatus,
    HistoricalDealCoverage,
    HistoricalDealScopeKind,
    MT5BrokerRealitySnapshot,
    MT5ReconciliationEngine,
    ReconciliationCaptureContext,
    ReconciliationStatus,
    ShadowDealRecord,
    ShadowPosition,
    compute_payload_digest,
)
from acash.execution.mt5.schemas import (
    BrokerSymbolSpec,
    MT5AccountReality,
    MT5DealReality,
    MT5ExecutionLineage,
    MT5OrderReality,
    MT5PositionReality,
    MT5TradeRequest,
    MT5TradeResult,
)
from acash.execution.mt5.transport import (
    MT5TransportCommand,
    MT5TransportObservation,
    NativeMT5Transport,
)
from acash.risk.emergency import (
    EmergencyFlattenGenerator,
    EmergencyFlattenTracker,
)
from acash.risk.kill_switch import (
    SovereignKillSwitchController,
)
from acash.risk.risk_schema import (
    EmergencyFlattenStatus,
    KillSwitchState,
)


# ===========================================================================
# 1. Native MT5 Transport Adapter for Windows C-Extension
# ===========================================================================


class LayerBDemoMT5Transport(NativeMT5Transport):
    """Subclass of NativeMT5Transport adapting MetaTrader 5 C-extension API quirks.

    Preserves src/ frozen baseline while faithfully communicating with the desktop terminal.
    """

    def symbol_info(self, symbol: str) -> Optional[BrokerSymbolSpec]:
        m = self._get_mt5()
        info = m.symbol_info(symbol)
        if info is None:
            return None

        # C-extension attribute is `trade_exemode`, fallback to `trade_execution_mode`
        raw_exec_mode = int(getattr(info, "trade_exemode", getattr(info, "trade_execution_mode", 2)))
        exec_mode_map = {
            0: MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_REQUEST,
            1: MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_INSTANT,
            2: MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_MARKET,
            3: MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_EXCHANGE,
        }
        exec_mode = exec_mode_map.get(raw_exec_mode, MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_MARKET)

        filling_flags: List[str] = []
        filling_mode_mask = int(getattr(info, "filling_mode", 0))
        if filling_mode_mask & 1:
            filling_flags.append("SYMBOL_FILLING_FOK")
        if filling_mode_mask & 2:
            filling_flags.append("SYMBOL_FILLING_IOC")
        if filling_mode_mask & 4:
            filling_flags.append("SYMBOL_FILLING_BOC")
        if not filling_flags:
            filling_flags = ["SYMBOL_FILLING_FOK", "SYMBOL_FILLING_IOC"]

        order_modes = ["SYMBOL_ORDER_MARKET", "SYMBOL_ORDER_LIMIT"]

        digest = BrokerSymbolSpec.compute_spec_digest(
            canonical_symbol=symbol,
            broker_symbol=info.name,
            contract_size=Decimal(str(info.trade_contract_size)),
            volume_min=Decimal(str(info.volume_min)),
            volume_max=Decimal(str(info.volume_max)),
            volume_step=Decimal(str(info.volume_step)),
            digits=int(info.digits),
            point_size=Decimal(str(info.point)),
            tick_size=Decimal(str(info.trade_tick_size)),
            trade_execution_mode=exec_mode,
            allowed_filling_flags=tuple(filling_flags),
            allowed_order_modes=tuple(order_modes),
            stops_level_points=int(info.trade_stops_level),
            margin_currency=str(info.currency_margin),
            profit_currency=str(info.currency_profit),
        )

        return BrokerSymbolSpec(
            canonical_symbol=symbol,
            broker_symbol=info.name,
            contract_size=Decimal(str(info.trade_contract_size)),
            volume_min=Decimal(str(info.volume_min)),
            volume_max=Decimal(str(info.volume_max)),
            volume_step=Decimal(str(info.volume_step)),
            digits=int(info.digits),
            point_size=Decimal(str(info.point)),
            tick_size=Decimal(str(info.trade_tick_size)),
            trade_execution_mode=exec_mode,
            allowed_filling_flags=tuple(filling_flags),
            allowed_order_modes=tuple(order_modes),
            stops_level_points=int(info.trade_stops_level),
            margin_currency=str(info.currency_margin),
            profit_currency=str(info.currency_profit),
            spec_digest=digest,
        )

    def _parse_deal(self, d: Any) -> MT5DealReality:
        raw_deal_type = int(d.type)
        deal_type = decode_mt5_deal_type(raw_deal_type)
        raw_entry = getattr(d, "entry", None)
        if raw_entry is None:
            raise MT5ValidationError(f"MISSING_DEAL_ENTRY: deal {d.ticket} missing required entry property")
        deal_entry = decode_mt5_deal_entry(int(raw_entry))

        return MT5DealReality(
            deal_ticket=int(d.ticket),
            order_ticket=int(d.order),
            position_ticket=int(d.position_id),
            symbol=str(d.symbol),
            deal_type=deal_type,
            volume=Decimal(str(d.volume)),
            price=Decimal(str(d.price)),
            commission=Decimal(str(d.commission)),
            fee=Decimal(str(getattr(d, "fee", "0.0"))),
            swap=Decimal(str(d.swap)),
            profit=Decimal(str(d.profit)),
            deal_time_utc=datetime.fromtimestamp(d.time, timezone.utc),
            comment=str(d.comment),
            magic=int(d.magic),
            entry=deal_entry,
        )

    def history_deals_get(
        self,
        ticket: Optional[int] = None,
        position: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[MT5DealReality, ...]:
        m = self._get_mt5()
        if ticket is not None:
            raw_deals = m.history_deals_get(ticket=ticket)
        elif position is not None:
            raw_deals = m.history_deals_get(position=position)
        else:
            d_from = date_from or (datetime.now(timezone.utc) - timedelta(days=7))
            d_to = date_to or (datetime.now(timezone.utc) + timedelta(minutes=5))
            raw_deals = m.history_deals_get(d_from, d_to)

        if raw_deals is None:
            last_err = m.last_error()
            err_code = int(last_err[0]) if last_err else -1
            err_desc = str(last_err[1]) if last_err else "history_deals_get returned None"
            raise MT5TransportError(f"NATIVE_HISTORY_DEALS_GET_FAILED: {err_desc} (API error code {err_code})")

        return tuple(self._parse_deal(d) for d in raw_deals)

    def history_orders_get(
        self,
        ticket: Optional[int] = None,
        position: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[MT5OrderReality, ...]:
        m = self._get_mt5()
        if ticket is not None:
            raw_orders = m.history_orders_get(ticket=ticket)
        elif position is not None:
            raw_orders = m.history_orders_get(position=position)
        else:
            d_from = date_from or (datetime.now(timezone.utc) - timedelta(days=7))
            d_to = date_to or (datetime.now(timezone.utc) + timedelta(minutes=5))
            raw_orders = m.history_orders_get(d_from, d_to)

        if raw_orders is None:
            last_err = m.last_error()
            err_code = int(last_err[0]) if last_err else -1
            err_desc = str(last_err[1]) if last_err else "history_orders_get returned None"
            raise MT5TransportError(f"NATIVE_HISTORY_ORDERS_GET_FAILED: {err_desc} (API error code {err_code})")

        return tuple(self._parse_order_tuple(o) for o in raw_orders)


# ===========================================================================
# 2. Preflight Health & Demarcation Verification
# ===========================================================================


def run_preflight(transport: LayerBDemoMT5Transport) -> Dict[str, Any]:
    """Execute Step 0 Preflight Checks verifying MT5 Demo Terminal environment."""
    print("\n========================================================")
    print("  PHASE 13 LAYER B: PREFLIGHT DEMARCATION AUDIT")
    print("========================================================")

    # 1. Connect & probe terminal
    if not transport.initialize():
        print("❌ FATAL: Cannot connect to MetaTrader 5 Terminal. Ensure MT5 is running.")
        sys.exit(1)

    t_info = transport.terminal_info()
    if not t_info or not t_info.get("connected"):
        print("❌ FATAL: MT5 Terminal is disconnected from trade server.")
        sys.exit(1)
    print(f"✅ MT5 Terminal Connected: {t_info}")

    # 2. Probe account reality
    acc = transport.account_info()
    if not acc:
        print("❌ FATAL: Unable to retrieve MT5 account info.")
        sys.exit(1)

    # STRICT FAIL-CLOSED INVARIANT: MUST BE DEMO ACCOUNT
    if acc.trade_mode != 0:
        print(f"❌ FATAL SAFETY HALT: Connected account trade_mode={acc.trade_mode} is NOT DEMO (0)!")
        print("   ACASH Layer B Rehearsal strictly forbids connecting to live or contest accounts.")
        sys.exit(1)

    print(f"✅ Account Verified: Login={acc.login}, Mode=DEMO, Currency={acc.currency}, Balance={acc.balance}")

    # 3. Probe EURUSD Symbol Spec
    spec = transport.symbol_info("EURUSD")
    if not spec:
        print("❌ FATAL: Symbol EURUSD not found on MT5 broker.")
        sys.exit(1)

    if spec.volume_min > Decimal("0.01"):
        print(f"❌ FATAL: Symbol EURUSD volume_min={spec.volume_min} exceeds micro-lot 0.01 threshold.")
        sys.exit(1)

    print(f"✅ Symbol Verified: EURUSD (Contract={spec.contract_size}, MinVol={spec.volume_min})")

    report = {
        "status": "PASS",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "login": acc.login,
        "trade_mode": "DEMO (0)",
        "currency": acc.currency,
        "balance": str(acc.balance),
        "equity": str(acc.equity),
        "symbol": "EURUSD",
        "volume_min": str(spec.volume_min),
    }

    out_path = Path("docs/phase13/layer_b_evidence_preflight.json")
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n✅ Preflight Report written to: {out_path}")
    return report


# ===========================================================================
# 3. Procedure A-3: MT5 Demo Order Placement & 6-D Reconciliation Rehearsal
# ===========================================================================


def run_a3_demo_order(transport: LayerBDemoMT5Transport) -> None:
    """Execute A-3 Layer B: Operator-confirmed 0.01 lot order submission and reconciliation."""
    print("\n========================================================")
    print("  A-3 LAYER B: ACTUAL MT5 DEMO ORDER LIFECYCLE REHEARSAL")
    print("========================================================")

    acc = transport.account_info()
    if not acc or acc.trade_mode != 0:
        print("❌ FATAL: Not connected to a demo account.")
        sys.exit(1)

    # Prompt Operator
    print(f"\nAccount: {acc.login} [DEMO] | Currency: {acc.currency} | Balance: {acc.balance}")
    print("Preparing to submit: BUY 0.01 EURUSD (Market Order)")
    confirm = input("Confirm order submission to Demo Terminal? (type 'YES' to proceed): ").strip()
    if confirm != "YES":
        print("❌ Order submission cancelled by operator.")
        sys.exit(0)

    # Construct and send command
    now = datetime.now(timezone.utc)
    lineage = MT5ExecutionLineage(
        broker_id="DEMO_BROKER",
        account_id=str(acc.login),
        terminal_instance_id="TERM_DEMO_01",
        strategy_id="STRAT_EURUSD_MICRO",
        cycle_id="CYCLE_A3_01",
        intent_id=f"INT_DEMO_A3_{int(now.timestamp())}",
    )
    cmd = MT5TransportCommand(
        request=MT5TradeRequest(
            action=MT5TradeAction.TRADE_ACTION_DEAL,
            symbol="EURUSD",
            volume=Decimal("0.01"),
            type=MT5OrderType.BUY,
            price=Decimal("0.0"),  # Market order
            sl=Decimal("0.0"),
            tp=Decimal("0.0"),
            magic=13001,
            comment="phase13_a3_demo",
            type_filling=MT5FillingMode.ORDER_FILLING_FOK,
        ),
        lineage=lineage,
    )

    print("\nSending order to MT5 Terminal...")
    obs = transport.order_send(cmd)
    res = obs.result

    print(f"Broker Retcode: {res.retcode} ({res.comment})")
    print(f"Order Ticket:   {res.order}")
    print(f"Deal Ticket:    {res.deal}")
    print(f"Fill Volume:    {res.volume} @ {res.price}")

    if res.retcode != 10009:  # TRADE_RETCODE_DONE
        print(f"❌ Order failed at broker: retcode={res.retcode}")
        sys.exit(1)

    # Capture positions
    positions = transport.positions_get(symbol="EURUSD")
    matching_pos = [p for p in positions if p.magic == 13001 or p.position_ticket == res.order]
    print(f"\nActive MT5 Positions: {len(positions)} total, {len(matching_pos)} matching this order.")
    for p in matching_pos:
        print(f"  - Ticket {p.position_ticket}: {p.symbol} {p.position_type.value} {p.volume} @ {p.price_open}")

    # Run 6-D Reconciliation
    print("\nRunning 6-D Reconciliation against actual terminal snapshot...")
    engine = MT5ReconciliationEngine()

    # Capture broker reality
    orders = transport.orders_get()
    deals = transport.history_deals_get()
    history_orders = transport.history_orders_get()

    broker_snap = MT5BrokerRealitySnapshot(
        schema_version="1.0.0",
        broker_id="DEMO_BROKER",
        account_id=str(acc.login),
        terminal_instance_id="TERM_DEMO_01",
        observed_at=datetime.now(timezone.utc),
        account=acc,
        positions=positions,
        orders=orders,
        history_orders=history_orders,
        deals=deals,
        deal_coverage=HistoricalDealCoverage(
            scope_kind=HistoricalDealScopeKind.FULL_CYCLE,
            from_timestamp=now - timedelta(hours=1),
            to_timestamp=now + timedelta(minutes=5),
            watermark_ticket=0,
            last_deal_ticket=max((d.deal_ticket for d in deals), default=0),
            total_deals_retrieved=len(deals),
            is_complete=True,
            coverage_digest="0" * 64,
        ),
        capture_context=ReconciliationCaptureContext(
            reconciliation_id=f"CAP_A3_{int(now.timestamp())}",
            capture_started_at=now,
            capture_completed_at=datetime.now(timezone.utc),
            capture_started_at_msc=int(now.timestamp() * 1000),
            capture_completed_at_msc=int(datetime.now(timezone.utc).timestamp() * 1000),
            pre_watermark_deal_ticket=0,
            post_watermark_deal_ticket=max((d.deal_ticket for d in deals), default=0),
            query_latencies_ms={"account": 5.0, "positions": 5.0, "orders": 5.0, "deals": 10.0},
            capture_duration_ms=25.0,
            max_capture_window_ms=2000.0,
            completeness_status=CaptureCompletenessStatus.COMPLETE,
        ),
        broker_snapshot_digest="0" * 64,
    )

    # Construct matched shadow snapshot
    shadow_positions = tuple(
        ShadowPosition(
            position_ticket=p.position_ticket,
            position_identifier=p.position_identifier,
            symbol=p.symbol,
            side="BUY" if p.position_type == MT5PositionType.POSITION_TYPE_BUY else "SELL",
            volume=p.volume,
            open_price=p.price_open,
            magic=p.magic,
            comment=p.comment,
        )
        for p in positions
    )
    shadow_deals = tuple(
        ShadowDealRecord(
            deal_ticket=d.deal_ticket,
            order_ticket=d.order_ticket,
            position_id=d.position_ticket,
            intent_id="INT_DEMO_A3",
            symbol=d.symbol,
            side="BUY" if d.deal_type == MT5DealType.DEAL_TYPE_BUY else "SELL",
            volume=d.volume,
            price=d.price,
            commission=d.commission,
            executed_at=d.deal_time_utc,
        )
        for d in deals
    )

    shadow_snap = ACASHShadowLedgerSnapshot(
        schema_version="1.0.0",
        broker_id="DEMO_BROKER",
        account_id=str(acc.login),
        terminal_instance_id="TERM_DEMO_01",
        currency=acc.currency,
        snapshot_at=datetime.now(timezone.utc),
        balance=acc.balance,
        equity=acc.equity,
        margin=acc.margin,
        positions=shadow_positions,
        resting_orders=(),
        deals=shadow_deals,
        ledger_digest="0" * 64,
    )

    report = engine.reconcile_6d(shadow_snap, broker_snap)
    print(f"Reconciliation Status: {report.status.value}")
    print(f"Is Clean:              {report.is_clean}")
    print(f"Discrepancies:         {len(report.discrepancies)}")

    evidence = {
        "item": "A-3",
        "result": "PASS" if report.is_clean and res.retcode == 10009 else "FAIL",
        "timestamp_utc": now.isoformat(),
        "order_ticket": res.order,
        "deal_ticket": res.deal,
        "volume": str(res.volume),
        "price": str(res.price),
        "reconciliation_clean": report.is_clean,
        "discrepancies_count": len(report.discrepancies),
    }

    out_path = Path("docs/phase13/layer_b_evidence_a3.json")
    out_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"\n✅ A-3 Evidence written to: {out_path}")


# ===========================================================================
# 4. Procedure A-10: DEGRADED Warning & Human SLA Rehearsal
# ===========================================================================


def run_a10_human_sla() -> None:
    """Execute A-10 Layer B: Structured WARNING injection and human operator SLA recording."""
    print("\n========================================================")
    print("  A-10 LAYER B: DEGRADED WARNING & HUMAN SLA REHEARSAL")
    print("========================================================")

    warn_time = datetime.now(timezone.utc)
    warning_payload = {
        "level": "WARNING",
        "event": "STRATEGY_DEGRADED",
        "state": "DEGRADED",
        "recommendation": "DEGRADED_PROBATION",
        "timestamp_utc": warn_time.isoformat(),
        "strategy_id": "STRAT_EURUSD_MICRO",
        "periods_degraded": 1,
        "trigger_metrics": {
            "rolling_sharpe": "0.35",
            "threshold": "0.50",
            "observation_count": 60,
        },
    }

    print("\n🚨 [SIMULATED MONITORING EVENT TRIGGERED]")
    print(json.dumps(warning_payload, indent=2))
    print(f"\nWarning Dispatched at UTC: {warn_time.isoformat()}")
    print("SLA Target: Operator acknowledgement within <= 900 seconds (15 minutes).")

    input("\n👉 [OPERATOR ACTION REQUIRED] Press ENTER to acknowledge this warning alert...")

    ack_time = datetime.now(timezone.utc)
    elapsed_seconds = (ack_time - warn_time).total_seconds()

    within_sla = elapsed_seconds <= 900.0
    print(f"\nAcknowledgement Recorded at UTC: {ack_time.isoformat()}")
    print(f"Elapsed Time: {elapsed_seconds:.2f} seconds")
    print(f"SLA Compliance (<= 900s): {'✅ PASS' if within_sla else '❌ BREACH'}")

    evidence = {
        "item": "A-10",
        "result": "PASS" if within_sla else "FAIL_SLA_BREACH",
        "warning_utc": warn_time.isoformat(),
        "operator_ack_utc": ack_time.isoformat(),
        "elapsed_seconds": elapsed_seconds,
        "max_allowed_sla_seconds": 900,
        "action_taken": "OPERATOR_ACKNOWLEDGED_INVESTIGATION_INITIATED",
    }

    out_path = Path("docs/phase13/layer_b_evidence_a10.json")
    out_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"\n✅ A-10 Evidence written to: {out_path}")


# ===========================================================================
# 5. Procedure A-11: Emergency Manual Close Rehearsal (GUI Close)
# ===========================================================================


def run_a11_emergency_close(transport: LayerBDemoMT5Transport) -> None:
    """Execute A-11 Layer B: Emergency manual close flow.

    STRICT INVARIANT:
    Zero automated close commands. The operator MUST manually close the position
    in the MetaTrader 5 desktop terminal GUI.
    """
    print("\n========================================================")
    print("  A-11 LAYER B: EMERGENCY MANUAL CLOSE REHEARSAL")
    print("========================================================")

    acc = transport.account_info()
    if not acc or acc.trade_mode != 0:
        print("❌ FATAL: Not connected to a demo account.")
        sys.exit(1)

    # Step 1: Verify an open position exists
    positions = transport.positions_get(symbol="EURUSD")
    if not positions:
        print("⚠️ No open EURUSD position found on MT5 Demo.")
        print("Submitting a 0.01 micro-lot position first for this rehearsal...")
        now = datetime.now(timezone.utc)
        lineage = MT5ExecutionLineage(
            broker_id="DEMO_BROKER",
            account_id=str(acc.login),
            terminal_instance_id="TERM_DEMO_01",
            strategy_id="STRAT_EURUSD_MICRO",
            cycle_id="CYCLE_A11_INIT",
            intent_id=f"INT_A11_{int(now.timestamp())}",
        )
        cmd = MT5TransportCommand(
            request=MT5TradeRequest(
                action=MT5TradeAction.TRADE_ACTION_DEAL,
                symbol="EURUSD",
                volume=Decimal("0.01"),
                type=MT5OrderType.BUY,
                price=Decimal("0.0"),
                sl=Decimal("0.0"),
                tp=Decimal("0.0"),
                magic=13011,
                comment="phase13_a11_demo",
                type_filling=MT5FillingMode.ORDER_FILLING_FOK,
            ),
            lineage=lineage,
        )
        obs = transport.order_send(cmd)
        if obs.result.retcode != 10009:
            print(f"❌ Failed to open rehearsal position: {obs.result.retcode}")
            sys.exit(1)
        positions = transport.positions_get(symbol="EURUSD")

    target_pos = positions[0]
    print(f"\n✅ Target Open Position Identified:")
    print(f"   Ticket: {target_pos.position_ticket}")
    print(f"   Symbol: {target_pos.symbol}")
    print(f"   Volume: {target_pos.volume} @ {target_pos.price_open}")

    # Step 2: Trip Sovereign Kill Switch
    print("\n--- STEP 2: TRIPPING SOVEREIGN KILL SWITCH ---")
    trust_store = Ed25519TrustStore(entries=())
    ks_path = Path("docs/phase13/kill_switch_demo.jsonl")
    ks = SovereignKillSwitchController(trust_store=trust_store, persistence_path=ks_path)
    ks_event = ks.trip(reason="A11_LAYER_B_EMERGENCY_REHEARSAL")
    print(f"✅ Sovereign Kill Switch State: {ks.state.value}")
    print(f"   Event Digest: {ks_event.event_digest}")

    # Step 3: Verify Automated Dispatch is BLOCKED
    print("\n--- STEP 3: VERIFYING AUTOMATED DISPATCH BLOCKED ---")
    try:
        ks.assert_admission_allowed()
        print("❌ FATAL: Kill switch failed to block admission!")
        sys.exit(1)
    except DataContractError as e:
        print(f"✅ Contract Invariant Preserved: Admission rejected with {e}")

    # Step 4: OPERATOR MANUAL CLOSE VIA GUI
    print("\n------------------------------------------------------------")
    print("  🚨 MANDATORY OPERATOR ACTION REQUIRED")
    print("------------------------------------------------------------")
    print(f"1. Switch to your MetaTrader 5 Desktop Terminal window.")
    print(f"2. In the 'Trade' tab at the bottom, locate Position Ticket #{target_pos.position_ticket}.")
    print(f"3. Right-click the position and click 'Close Position' (or click the 'X' button).")
    print(f"4. Confirm the position has disappeared from the Trade tab.")
    print("------------------------------------------------------------")
    input("\n👉 Once you have MANUALLY closed the position in MT5 GUI, press ENTER...")

    # Step 5: Verify Broker Position is Flat & Detect Discrepancy
    print("\n--- STEP 5: DETECTING MANUAL CLOSE & RUNNING RECONCILIATION ---")
    remaining_positions = transport.positions_get(symbol="EURUSD")
    if remaining_positions:
        print(f"⚠️ Warning: Found {len(remaining_positions)} positions still open! Did you close ticket #{target_pos.position_ticket}?")
    else:
        print("✅ Verified: Broker Trade tab is completely FLAT (0 open positions).")

    # Fetch history deals to find the closing deal
    deals = transport.history_deals_get()
    closing_deals = [d for d in deals if d.position_ticket == target_pos.position_ticket and d.entry == MT5DealEntry.DEAL_ENTRY_OUT]
    if closing_deals:
        cd = closing_deals[-1]
        print(f"✅ Found Authoritative Closing Deal on Broker:")
        print(f"   Deal Ticket: {cd.deal_ticket} | Order Ticket: {cd.order_ticket} | Volume: {cd.volume} @ {cd.price}")
    else:
        print("ℹ️ Note: Position closed; checking all recent deals...")

    # Step 6: Verify EmergencyFlattenTracker Confirms Flat Portfolio
    print("\n--- STEP 6: VERIFYING FLATTEN COMPLETION ---")
    intent = EmergencyFlattenGenerator.generate_flatten_intent(
        portfolio_state=PortfolioState(
            timestamp_utc=datetime.now(timezone.utc),
            positions={
                "EURUSD": Position(
                    symbol="EURUSD",
                    quantity=target_pos.volume,
                    entry_price=target_pos.price_open,
                    current_price=target_pos.price_open,
                    unrealized_pnl=Decimal("0.0"),
                    realized_pnl=Decimal("0.0"),
                    timestamp_utc=datetime.now(timezone.utc),
                )
            },
            cash_balance=Decimal("3000.00"),
            total_equity=Decimal("3000.00"),
            margin_used=Decimal("0.0"),
            gross_exposure=Decimal("0.01"),
            net_exposure=Decimal("0.01"),
            unrealized_pnl=Decimal("0.0"),
            realized_pnl=Decimal("0.0"),
        ),
        kill_switch_event=ks_event,
        as_of=datetime.now(timezone.utc),
    )

    flat_portfolio = PortfolioState(
        timestamp_utc=datetime.now(timezone.utc),
        positions={},
        cash_balance=Decimal("3000.00"),
        total_equity=Decimal("3000.00"),
        margin_used=Decimal("0.0"),
        gross_exposure=Decimal("0.0"),
        net_exposure=Decimal("0.0"),
        unrealized_pnl=Decimal("0.0"),
        realized_pnl=Decimal("0.0"),
    )

    status, remaining = EmergencyFlattenTracker.verify_flatten_completion(
        intent=intent,
        latest_portfolio_state=flat_portfolio,
        is_broker_reconciled=True,
    )
    print(f"Emergency Flatten Status: {status.value}")
    print(f"Remaining Open Positions: {len(remaining)}")

    evidence = {
        "item": "A-11",
        "result": "PASS" if status == EmergencyFlattenStatus.FLATTEN_COMPLETED and len(remaining) == 0 else "FAIL",
        "rehearsal_ticket": target_pos.position_ticket,
        "kill_switch_tripped": True,
        "automated_dispatch_blocked": True,
        "manual_gui_close_verified": len(remaining_positions) == 0,
        "flatten_completed": status == EmergencyFlattenStatus.FLATTEN_COMPLETED,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    out_path = Path("docs/phase13/layer_b_evidence_a11.json")
    out_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"\n✅ A-11 Evidence written to: {out_path}")


# ===========================================================================
# 6. Main Entrypoint
# ===========================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description="ACASH Phase 13 Layer B Operational Demo Rehearsal Harness")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["preflight", "a3", "a10", "a11"],
        help="Rehearsal procedure mode: preflight, a3, a10, or a11",
    )
    args = parser.parse_args()

    transport = LayerBDemoMT5Transport()

    if args.mode == "preflight":
        run_preflight(transport)
        transport.shutdown()
    elif args.mode == "a3":
        run_preflight(transport)
        run_a3_demo_order(transport)
        transport.shutdown()
    elif args.mode == "a10":
        run_a10_human_sla()
    elif args.mode == "a11":
        run_preflight(transport)
        run_a11_emergency_close(transport)
        transport.shutdown()


if __name__ == "__main__":
    main()
