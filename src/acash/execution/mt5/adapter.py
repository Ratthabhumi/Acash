"""Phase 12 Slice 3: MetaTrader 5 Broker Adapter and Observation Source."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from acash.execution.broker_events import (
    BrokerEventKind,
    ReconciliationEvidence,
    normalize_broker_event,
)
from acash.execution.mt5.enums import (
    MT5ExecutionPolicy,
    MT5FillingMode,
    MT5OrderTime,
    MT5OrderType,
    MT5Retcode,
    MT5TradeAction,
)
from acash.execution.mt5.exceptions import (
    MT5DomainError,
    MT5RetcodeError,
    MT5TransportError,
    MT5ValidationError,
)
from acash.execution.mt5.mapping import (
    classify_trade_result_observation,
    map_order_intent_to_trade_request,
)
from acash.execution.mt5.normalizer import MT5SymbolNormalizer
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
    MT5HealthReport,
    MT5ReconciliationConfirmation,
    MT5TransportCommand,
    MT5TransportObservation,
    MT5TransportProtocol,
    MT5TransportSafetyState,
    TransportFailureCause,
)
from acash.execution.schema import OrderIntent, OrderSide, OrderType, TimeInForce
from acash.execution.state_machine import ExecutionEvent


class MT5BrokerObservation(BaseModel):
    """Raw broker observation emitted by MT5BrokerAdapter.

    INVARIANT:
    The adapter strictly returns raw broker observations and NEVER mutates order lifecycle state.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_kind: BrokerEventKind
    broker_order_id: str
    observed_at: datetime
    raw_retcode: int
    raw_deal: int = 0
    raw_order: int = 0
    volume: Decimal = Decimal("0.0")
    price: Optional[Decimal] = None
    comment: str = ""
    lineage: MT5ExecutionLineage
    requires_reconciliation: bool = False
    execution_event: ExecutionEvent
    evidence: Optional[ReconciliationEvidence] = None


class MT5BrokerAdapter:
    """Sovereign Broker Adapter for MetaTrader 5.

    ARCHITECTURAL INVARIANTS:
    1. Zero Lifecycle Authority: order_send() and broker polling return raw observations
       (MT5BrokerObservation). The adapter NEVER calls transition_order().
    2. Fail-Closed Startup: Instantiates in DEGRADED state with is_reconciled=False.
    3. READY Invariant: can_dispatch() == True iff connected AND healthy AND trade-allowed
       AND is_reconciled AND safety_state != BLOCKED.
    4. Absorbing BLOCKED: BLOCKED state cannot be bypassed by health checks or reconciliation.
    """

    def __init__(
        self,
        broker_id: str,
        account_id: str,
        terminal_instance_id: str,
        transport: MT5TransportProtocol,
    ) -> None:
        if not broker_id or not broker_id.strip():
            raise MT5ValidationError("broker_id must be a non-empty string")
        if not account_id or not account_id.strip():
            raise MT5ValidationError("account_id must be a non-empty string")
        if not terminal_instance_id or not terminal_instance_id.strip():
            raise MT5ValidationError("terminal_instance_id must be a non-empty string")

        self.broker_id = broker_id.strip()
        self.account_id = account_id.strip()
        self.terminal_instance_id = terminal_instance_id.strip()
        self.transport = transport

        # Fail-closed construction baseline
        self.safety_state: MT5TransportSafetyState = MT5TransportSafetyState.DEGRADED
        self.is_reconciled: bool = False

    def can_dispatch(self) -> bool:
        """Evaluate whether adapter is in a safe, verified state to dispatch outbound requests."""
        return (
            self.safety_state == MT5TransportSafetyState.READY
            and self.is_reconciled is True
        )

    def mark_reconciliation_required(
        self,
        cause: TransportFailureCause,
        context: str = "",
    ) -> None:
        """Transition transport safety state to RECONCILIATION_REQUIRED due to transport uncertainty."""
        if self.safety_state == MT5TransportSafetyState.BLOCKED:
            return  # BLOCKED is strictly absorbing

        self.is_reconciled = False
        self.safety_state = MT5TransportSafetyState.RECONCILIATION_REQUIRED

    def confirm_reconciliation(
        self,
        confirmation: MT5ReconciliationConfirmation,
    ) -> None:
        """Confirm verified reconciliation evidence to unblock transport dispatch."""
        if self.safety_state == MT5TransportSafetyState.BLOCKED:
            raise MT5ValidationError("CANNOT_RECONCILE_BLOCKED_ADAPTER: adapter is administratively BLOCKED")

        if confirmation.broker_id != self.broker_id or confirmation.account_id != self.account_id:
            raise MT5ValidationError(
                f"RECONCILIATION_IDENTITY_MISMATCH: confirmation for ({confirmation.broker_id}, {confirmation.account_id}) "
                f"does not match adapter ({self.broker_id}, {self.account_id})"
            )

        if not confirmation.is_complete or confirmation.discrepancies_count != 0:
            raise MT5ValidationError(
                f"INCOMPLETE_RECONCILIATION_EVIDENCE: is_complete={confirmation.is_complete}, "
                f"discrepancies={confirmation.discrepancies_count}"
            )

        if not (
            confirmation.orders_verified
            and confirmation.deals_verified
            and confirmation.positions_verified
            and confirmation.account_verified
        ):
            raise MT5ValidationError(
                "UNVERIFIED_RECONCILIATION_DIMENSIONS: all 4 dimensions (orders, deals, positions, account) "
                "must be strictly verified"
            )

        self.is_reconciled = True
        health = self.check_health()
        if health.is_connected and health.is_healthy and health.is_trade_allowed:
            self.safety_state = MT5TransportSafetyState.READY
        else:
            self.safety_state = MT5TransportSafetyState.DEGRADED

    def mark_blocked(self, reason: str = "") -> None:
        """Hard stop: transition transport safety state to BLOCKED."""
        self.safety_state = MT5TransportSafetyState.BLOCKED

    def unblock_emergency(self, override_token: str) -> None:
        """Administrative override to unblock from BLOCKED state to RECONCILIATION_REQUIRED."""
        if self.safety_state != MT5TransportSafetyState.BLOCKED:
            raise MT5ValidationError(
                f"EMERGENCY_UNBLOCK_REQUIRES_BLOCKED_STATE: current state is {self.safety_state}"
            )
        if not override_token or not override_token.strip():
            raise MT5ValidationError("OVERRIDE_TOKEN_REQUIRED: override_token must be non-empty")

        self.is_reconciled = False
        self.safety_state = MT5TransportSafetyState.RECONCILIATION_REQUIRED

    def check_health(self) -> MT5HealthReport:
        """Authoritative health check reporting true physical health alongside safety state."""
        is_connected = False
        is_healthy = False
        is_trade_allowed = False
        failure_cause: Optional[TransportFailureCause] = None
        detail = ""

        terminal_info = self.transport.terminal_info()
        if terminal_info is None:
            is_connected = False
            is_healthy = False
            is_trade_allowed = False
            failure_cause = TransportFailureCause.TERMINAL_IPC_UNAVAILABLE
            detail = "Terminal IPC unreachable"
        elif not terminal_info.get("connected", False):
            is_connected = False
            is_healthy = False
            is_trade_allowed = False
            failure_cause = TransportFailureCause.TRADE_SERVER_DISCONNECTED
            detail = "Terminal disconnected from trade server"
        else:
            # IPC and Trade Server are connected
            is_connected = True
            account = self.transport.account_info()
            if account is None:
                is_healthy = False
                is_trade_allowed = False
                failure_cause = TransportFailureCause.TERMINAL_UNHEALTHY
                detail = "Failed to query account reality snapshot"
            else:
                is_healthy = True
                term_trade_allowed = bool(terminal_info.get("trade_allowed", False))
                term_trade_expert = bool(terminal_info.get("trade_expert", False))
                acc_trade_allowed = bool(account.trade_allowed)
                acc_trade_expert = bool(account.trade_expert)

                if not (term_trade_allowed and term_trade_expert and acc_trade_allowed and acc_trade_expert):
                    is_trade_allowed = False
                    failure_cause = TransportFailureCause.TRADING_PERMISSION_DISABLED
                    detail = (
                        f"Trading permissions disabled: terminal(allowed={term_trade_allowed}, expert={term_trade_expert}), "
                        f"account(allowed={acc_trade_allowed}, expert={acc_trade_expert})"
                    )
                else:
                    is_trade_allowed = True
                    failure_cause = None
                    detail = "Terminal, account, and trading permissions fully healthy"

        # Apply state machine transition policy
        if self.safety_state == MT5TransportSafetyState.BLOCKED:
            pass  # BLOCKED is strictly absorbing
        elif self.safety_state == MT5TransportSafetyState.RECONCILIATION_REQUIRED:
            pass  # RECONCILIATION_REQUIRED cannot be cleared by health check alone
        elif not is_connected or not is_healthy or not is_trade_allowed:
            self.safety_state = MT5TransportSafetyState.DEGRADED
        else:
            # Physical state is healthy and trade allowed
            if self.safety_state == MT5TransportSafetyState.DEGRADED and self.is_reconciled is True:
                self.safety_state = MT5TransportSafetyState.READY

        return MT5HealthReport(
            is_connected=is_connected,
            is_healthy=is_healthy,
            is_trade_allowed=is_trade_allowed,
            safety_state=self.safety_state,
            failure_cause=failure_cause,
            detail=detail,
        )

    def submit_order(
        self,
        intent: OrderIntent,
        symbol_spec: BrokerSymbolSpec,
        execution_policy: MT5ExecutionPolicy = MT5ExecutionPolicy.DEFAULT,
        magic: int = 0,
        comment: str = "",
    ) -> MT5BrokerObservation:
        """Submit order intent to MT5 transport and return typed MT5BrokerObservation.

        INVARIANT:
        The adapter strictly returns raw broker observations and NEVER mutates order lifecycle state.
        """
        if not self.can_dispatch():
            raise MT5DomainError(
                f"DISPATCH_BLOCKED: safety_state={self.safety_state}, is_reconciled={self.is_reconciled}"
            )

        # 1. Normalize volume and price
        normalized_volume = MT5SymbolNormalizer.normalize_volume(intent.quantity, symbol_spec)
        normalized_intent = intent.model_copy(update={"quantity": normalized_volume})

        if normalized_intent.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT) and normalized_intent.limit_price is not None:
            snapped_limit = MT5SymbolNormalizer.normalize_price(
                normalized_intent.limit_price,
                symbol_spec,
                MT5OrderType.BUY_LIMIT if normalized_intent.side == OrderSide.BUY else MT5OrderType.SELL_LIMIT,
            )
            normalized_intent = normalized_intent.model_copy(update={"limit_price": snapped_limit})

        # 2. Build Trade Request DTO
        request = map_order_intent_to_trade_request(
            intent=normalized_intent,
            symbol_spec=symbol_spec,
            execution_policy=execution_policy,
            magic=magic,
            comment=comment,
        )

        # 3. Build Execution Lineage & Transport Command Envelope
        lineage = MT5ExecutionLineage(
            broker_id=self.broker_id,
            account_id=self.account_id,
            terminal_instance_id=self.terminal_instance_id,
            strategy_id=intent.strategy_id,
            cycle_id=intent.intent_id,
            intent_id=intent.intent_id,
        )
        command = MT5TransportCommand(request=request, lineage=lineage)

        # 4. Dispatch to Transport with Fail-Closed Uncertainty Boundaries
        now = datetime.now(timezone.utc)
        source = f"mt5:{self.broker_id}:{self.account_id}"

        try:
            observation = self.transport.order_send(command)
        except (TimeoutError, ConnectionError, OSError, MT5TransportError) as e:
            self.mark_reconciliation_required(
                TransportFailureCause.ORDER_SEND_TIMEOUT_UNCERTAIN,
                f"order_send transport exception: {e}",
            )
            broker_order_id = f"UNKNOWN_{intent.intent_id}"
            exec_event, evidence = normalize_broker_event(
                broker_order_id=broker_order_id,
                event_kind=BrokerEventKind.CONNECTION_LOST,
                observed_at=now,
                source=source,
                broker_sequence=f"SEQ_ERR_{intent.intent_id}",
            )
            return MT5BrokerObservation(
                event_kind=BrokerEventKind.CONNECTION_LOST,
                broker_order_id=broker_order_id,
                observed_at=now,
                raw_retcode=MT5Retcode.TRADE_RETCODE_TIMEOUT.value,
                comment=str(e),
                lineage=lineage,
                requires_reconciliation=True,
                execution_event=exec_event,
                evidence=evidence,
            )

        # 5. Verify Lineage Integrity (Fail Closed)
        if observation.lineage != command.lineage:
            raise MT5ValidationError(
                f"LINEAGE_INTEGRITY_MISMATCH: outbound lineage {command.lineage} does not match inbound lineage {observation.lineage}"
            )

        # 6. Handle Broker Connection Lost (10031)
        res = observation.result
        if res.retcode == MT5Retcode.TRADE_RETCODE_CONNECTION.value:
            self.mark_reconciliation_required(
                TransportFailureCause.TRADE_SERVER_DISCONNECTED,
                "Trade server connection lost (10031)",
            )
            broker_order_id = str(res.order or f"UNKNOWN_{intent.intent_id}")
            exec_event, evidence = normalize_broker_event(
                broker_order_id=broker_order_id,
                event_kind=BrokerEventKind.CONNECTION_LOST,
                observed_at=observation.observed_at,
                source=source,
                broker_sequence=f"SEQ_10031_{res.order}",
            )
            return MT5BrokerObservation(
                event_kind=BrokerEventKind.CONNECTION_LOST,
                broker_order_id=broker_order_id,
                observed_at=observation.observed_at,
                raw_retcode=res.retcode,
                comment=res.comment,
                lineage=observation.lineage,
                requires_reconciliation=True,
                execution_event=exec_event,
                evidence=evidence,
            )

        # 7. Classify Observation & Normalize Broker Event
        event_kind = classify_trade_result_observation(res, authoritative_deal_confirmed=False)
        broker_order_id = str(res.order if res.order != 0 else (res.deal if res.deal != 0 else f"UNCONFIRMED_{intent.intent_id}"))
        broker_seq = str(res.deal if res.deal != 0 else (res.order if res.order != 0 else f"SEQ_{intent.intent_id}"))

        exec_event, evidence = normalize_broker_event(
            broker_order_id=broker_order_id,
            event_kind=event_kind,
            observed_at=observation.observed_at,
            source=source,
            broker_sequence=broker_seq,
        )

        return MT5BrokerObservation(
            event_kind=event_kind,
            broker_order_id=broker_order_id,
            observed_at=observation.observed_at,
            raw_retcode=res.retcode,
            raw_deal=res.deal,
            raw_order=res.order,
            volume=res.volume,
            price=res.price if res.price != Decimal("0.0") else None,
            comment=res.comment,
            lineage=observation.lineage,
            requires_reconciliation=False,
            execution_event=exec_event,
            evidence=evidence,
        )

    def cancel_order(
        self,
        order_ticket: int,
        symbol: str,
        magic: int = 0,
        comment: str = "",
    ) -> MT5BrokerObservation:
        """Issue order cancellation request to MT5."""
        if order_ticket <= 0:
            raise MT5ValidationError(f"order_ticket must be > 0, got: {order_ticket}")

        request = MT5TradeRequest(
            action=MT5TradeAction.TRADE_ACTION_REMOVE,
            order=order_ticket,
            symbol=symbol,
            volume=Decimal("0.0"),
            magic=magic,
            comment=comment[:31] if comment else "",
            type=MT5OrderType.BUY,  # default placeholder for REMOVE action
            type_filling=MT5FillingMode.ORDER_FILLING_FOK,
        )
        lineage = MT5ExecutionLineage(
            broker_id=self.broker_id,
            account_id=self.account_id,
            terminal_instance_id=self.terminal_instance_id,
            strategy_id="CANCEL_ROUTINE",
            cycle_id=f"CANCEL_{order_ticket}",
            intent_id=f"CANCEL_{order_ticket}",
            mt5_order_ticket=order_ticket,
        )
        command = MT5TransportCommand(request=request, lineage=lineage)
        now = datetime.now(timezone.utc)
        source = f"mt5:{self.broker_id}:{self.account_id}"

        try:
            obs = self.transport.order_send(command)
        except (TimeoutError, ConnectionError, OSError, MT5TransportError) as e:
            self.mark_reconciliation_required(
                TransportFailureCause.ORDER_SEND_TIMEOUT_UNCERTAIN,
                f"cancel_order transport exception: {e}",
            )
            exec_event, evidence = normalize_broker_event(
                broker_order_id=str(order_ticket),
                event_kind=BrokerEventKind.CONNECTION_LOST,
                observed_at=now,
                source=source,
                broker_sequence=f"SEQ_CANCEL_ERR_{order_ticket}",
            )
            return MT5BrokerObservation(
                event_kind=BrokerEventKind.CONNECTION_LOST,
                broker_order_id=str(order_ticket),
                observed_at=now,
                raw_retcode=MT5Retcode.TRADE_RETCODE_TIMEOUT.value,
                comment=str(e),
                lineage=lineage,
                requires_reconciliation=True,
                execution_event=exec_event,
                evidence=evidence,
            )

        # Verify Lineage Integrity
        if obs.lineage != command.lineage:
            raise MT5ValidationError(
                f"LINEAGE_INTEGRITY_MISMATCH: outbound lineage {command.lineage} does not match inbound lineage {obs.lineage}"
            )

        res = obs.result
        event_kind = classify_trade_result_observation(res, authoritative_deal_confirmed=False)
        exec_event, evidence = normalize_broker_event(
            broker_order_id=str(order_ticket),
            event_kind=event_kind,
            observed_at=obs.observed_at,
            source=source,
            broker_sequence=f"SEQ_CANCEL_{order_ticket}",
            cancel_was_requested=True,
        )

        return MT5BrokerObservation(
            event_kind=event_kind,
            broker_order_id=str(order_ticket),
            observed_at=obs.observed_at,
            raw_retcode=res.retcode,
            raw_deal=res.deal,
            raw_order=res.order,
            volume=res.volume,
            comment=res.comment,
            lineage=obs.lineage,
            requires_reconciliation=False,
            execution_event=exec_event,
            evidence=evidence,
        )

    # --- 4-Dimensional Reconciliation Observation Queries ---

    def fetch_open_orders(self, symbol: Optional[str] = None) -> Tuple[MT5OrderReality, ...]:
        return self.transport.orders_get(symbol=symbol)

    def fetch_history_orders(
        self,
        ticket: Optional[int] = None,
        position: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[MT5OrderReality, ...]:
        return self.transport.history_orders_get(
            ticket=ticket,
            position=position,
            date_from=date_from,
            date_to=date_to,
        )

    def fetch_history_deals(
        self,
        ticket: Optional[int] = None,
        position: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[MT5DealReality, ...]:
        return self.transport.history_deals_get(
            ticket=ticket,
            position=position,
            date_from=date_from,
            date_to=date_to,
        )

    def fetch_open_positions(self, symbol: Optional[str] = None) -> Tuple[MT5PositionReality, ...]:
        return self.transport.positions_get(symbol=symbol)

    def fetch_account_state(self) -> Optional[MT5AccountReality]:
        return self.transport.account_info()
