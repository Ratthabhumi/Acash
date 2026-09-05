"""Phase 13: Paper Execution Bridge & Simulated Market Matcher.

Strictly enforces:
1. Mechanical translation and dispatch seam (Stage 5 allocation -> OrderIntent -> venue).
2. Zero secondary risk, position-sizing, or capital allocation authority.
3. Deterministic volume_step quantization with ROUND_DOWN and residual discard.
4. Unrepresentable step residuals are discarded without converting to cash or portfolio balance.
5. Multi-stage partial-fill lifecycle (ACK -> PARTIAL_FILL -> FILLED).
6. Non-circular ExecutionManifest audit trail lineage.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN
from enum import Enum
import hashlib
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Sequence, Set, Tuple

from pydantic import BaseModel, ConfigDict, Field

from acash.core.domain.exceptions import DataContractError
from acash.core.domain.market_data import MarketDataSnapshot
from acash.core.domain.portfolio import PortfolioState
from acash.core.serialization import CanonicalConfigSerializer
from acash.execution.broker_adapter import to_coordinator_event
from acash.execution.broker_events import BrokerEventKind
from acash.execution.coordinator import (
    CoordinatorOutcome,
    ExecutionCoordinator,
)
from acash.execution.mock_broker import BrokerRawEvent
from acash.execution.mt5.schemas import BrokerSymbolSpec
from acash.execution.schema import (
    ExecutionManifest,
    OrderIntent,
    OrderLifecycleState,
    OrderSide,
    OrderType,
    TimeInForce,
)
from acash.portfolio.schema import AllocationDecision

if TYPE_CHECKING:
    from acash.execution.mt5.adapter import MT5BrokerAdapter
    from acash.runtime.schema import CycleIdentity
    from acash.runtime.strategy_adapter import PaperTradingSessionIdentity


class PaperExecutionVenueType(str, Enum):
    """Execution venue target for paper trading operations."""

    MT5_DEMO = "MT5_DEMO"
    LOCAL_SIMULATOR = "LOCAL_SIMULATOR"


# ============================================================================
# EXECUTION COST MODELS
# ============================================================================


class SpreadModelConfig(BaseModel):
    """Deterministic spread model configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    base_spread_pips: Decimal = Field(default=Decimal("1.2"), description="Baseline fixed spread in pips.")
    volatility_expansion_factor: Decimal = Field(default=Decimal("1.0"), description="Spread scaling factor.")


class SlippageModelConfig(BaseModel):
    """Deterministic slippage model configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    fixed_slippage_bps: Decimal = Field(default=Decimal("0.50"), description="Fixed execution drag in basis points.")
    dispersion_slippage_std_bps: Decimal = Field(
        default=Decimal("0.00"), description="Standard deviation of dispersion slippage in bps."
    )
    prng_seed: int = Field(default=42, description="Explicit PRNG seed for deterministic dispersion.")


class CommissionModelConfig(BaseModel):
    """Deterministic commission model configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    commission_per_lot_usd: Decimal = Field(
        default=Decimal("7.00"), description="Round-turn commission estimate per standard lot in USD."
    )


class ExecutionCostModel(BaseModel):
    """Comprehensive execution cost model with unified provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    spread_model: SpreadModelConfig = Field(default_factory=SpreadModelConfig)
    slippage_model: SlippageModelConfig = Field(default_factory=SlippageModelConfig)
    commission_model: CommissionModelConfig = Field(default_factory=CommissionModelConfig)
    provenance: str = Field(default="DETERMINISTIC_TEST_CONFIGURATION")

    def compute_digest(self) -> str:
        """Compute canonical SHA-256 digest of cost model configuration."""
        payload = {
            "spread_model": {
                "base_spread_pips": str(self.spread_model.base_spread_pips),
                "volatility_expansion_factor": str(self.spread_model.volatility_expansion_factor),
            },
            "slippage_model": {
                "fixed_slippage_bps": str(self.slippage_model.fixed_slippage_bps),
                "dispersion_slippage_std_bps": str(self.slippage_model.dispersion_slippage_std_bps),
                "prng_seed": self.slippage_model.prng_seed,
            },
            "commission_model": {
                "commission_per_lot_usd": str(self.commission_model.commission_per_lot_usd),
            },
            "provenance": self.provenance,
        }
        canonical_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()


# ============================================================================
# SIMULATED MARKET MATCHER
# ============================================================================


class SimulatedMarketMatcher:
    """In-memory, seeded deterministic test double matcher with multi-stage fill lifecycle."""

    def __init__(
        self,
        cost_model: Optional[ExecutionCostModel] = None,
        partial_fill_ratio: Optional[Decimal] = None,
        reject_next: bool = False,
    ) -> None:
        self.cost_model = cost_model or ExecutionCostModel()
        self.partial_fill_ratio = partial_fill_ratio
        self.reject_next = reject_next
        self._open_orders: dict[str, Decimal] = {}  # intent_id -> remaining_qty
        self._sequence_counter = 0

    def _next_seq(self) -> str:
        self._sequence_counter += 1
        return str(self._sequence_counter)

    def match_order(
        self,
        intent: OrderIntent,
        snapshot: MarketDataSnapshot,
    ) -> Sequence[BrokerRawEvent]:
        """Match an incoming OrderIntent deterministically against current MarketDataSnapshot."""
        order_id = f"SIM-{intent.intent_id}"
        now = snapshot.timestamp_utc

        if self.reject_next:
            self.reject_next = False
            return [
                BrokerRawEvent(
                    broker_order_id=order_id,
                    event_kind=BrokerEventKind.ACK,
                    observed_at=now,
                    source="LOCAL_SIMULATOR",
                    broker_sequence=self._next_seq(),
                ),
                BrokerRawEvent(
                    broker_order_id=order_id,
                    event_kind=BrokerEventKind.REJECT,
                    observed_at=now,
                    source="LOCAL_SIMULATOR",
                    broker_sequence=self._next_seq(),
                ),
            ]

        # Check if this is an existing partially filled order working on the simulator
        if intent.intent_id in self._open_orders:
            remaining_qty = self._open_orders.pop(intent.intent_id)
            fill_event = BrokerRawEvent(
                broker_order_id=order_id,
                event_kind=BrokerEventKind.FILLED,
                observed_at=now,
                source="LOCAL_SIMULATOR",
                broker_sequence=self._next_seq(),
            )
            # Store remaining fill_qty on event for coordinator adapter
            object.__setattr__(fill_event, "fill_qty", remaining_qty) if hasattr(fill_event, "__dict__") else None
            return [fill_event]

        # Multi-stage partial fill mode (Vector V-03)
        if self.partial_fill_ratio is not None and self.partial_fill_ratio > Decimal("0.0"):
            first_fill_qty = (intent.quantity * self.partial_fill_ratio).quantize(
                Decimal("0.01"), rounding=ROUND_DOWN
            )
            remaining_qty = intent.quantity - first_fill_qty
            self._open_orders[intent.intent_id] = remaining_qty

            ack_event = BrokerRawEvent(
                broker_order_id=order_id,
                event_kind=BrokerEventKind.ACK,
                observed_at=now,
                source="LOCAL_SIMULATOR",
                broker_sequence=self._next_seq(),
            )
            partial_event = BrokerRawEvent(
                broker_order_id=order_id,
                event_kind=BrokerEventKind.PARTIAL_FILL,
                observed_at=now,
                source="LOCAL_SIMULATOR",
                broker_sequence=self._next_seq(),
            )
            return [ack_event, partial_event]

        # Default: ACK followed by FULL_FILL
        ack_event = BrokerRawEvent(
            broker_order_id=order_id,
            event_kind=BrokerEventKind.ACK,
            observed_at=now,
            source="LOCAL_SIMULATOR",
            broker_sequence=self._next_seq(),
        )
        fill_event = BrokerRawEvent(
            broker_order_id=order_id,
            event_kind=BrokerEventKind.FILLED,
            observed_at=now,
            source="LOCAL_SIMULATOR",
            broker_sequence=self._next_seq(),
        )
        return [ack_event, fill_event]


# ============================================================================
# PAPER EXECUTION BRIDGE
# ============================================================================


class PaperExecutionBridge:
    """Mechanical translation and dispatch seam between Stage 5 and execution venues."""

    def __init__(
        self,
        coordinator: ExecutionCoordinator,
        venue_type: PaperExecutionVenueType,
        mt5_adapter: Optional[MT5BrokerAdapter] = None,
        matcher: Optional[SimulatedMarketMatcher] = None,
        symbol_spec_provider: Optional[Callable[[str], BrokerSymbolSpec]] = None,
    ) -> None:
        self.coordinator = coordinator
        self.venue_type = venue_type
        self.mt5_adapter = mt5_adapter
        self.matcher = matcher
        self.symbol_spec_provider = symbol_spec_provider
        self._dispatched_intent_ids: Set[str] = set()
        self._emitted_manifests: List[ExecutionManifest] = []
        self._active_intent: Optional[OrderIntent] = None

    @property
    def emitted_manifests(self) -> Sequence[ExecutionManifest]:
        """Return sequence of ExecutionManifest records emitted during this session."""
        return tuple(self._emitted_manifests)

    def _get_symbol_spec(self, symbol: str) -> BrokerSymbolSpec:
        """Resolve BrokerSymbolSpec for the given symbol."""
        if self.symbol_spec_provider is not None:
            return self.symbol_spec_provider(symbol)

        from acash.execution.mt5.enums import MT5TradeExecutionMode

        # Default canonical test specification
        return BrokerSymbolSpec(
            canonical_symbol=symbol,
            broker_symbol=symbol,
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

    def _quantize_target_delta(
        self,
        target_allocation: AllocationDecision,
        current_portfolio: PortfolioState,
        symbol_spec: BrokerSymbolSpec,
        reference_price: Optional[Decimal] = None,
    ) -> Optional[Tuple[Decimal, OrderSide]]:
        """Compute quantized order lot volume using canonical ROUND_DOWN pipeline.

        Strict Residual Semantics (Rev 2.2.2 §5.2.1):
        Unrepresentable quantity residuals (r < volume_step) are discarded from the
        executable order delta without converting them to cash or altering portfolio balance.
        """
        symbol = symbol_spec.canonical_symbol
        target_weight = target_allocation.authorized_weights.get(symbol, Decimal("0.0"))

        if (
            target_allocation.is_fallback_baseline
            or target_allocation.gate_verdict != "APPROVED_INVESTABLE_ALLOCATION"
        ):
            target_lots = Decimal("0.0")
        else:
            if reference_price is not None and reference_price > Decimal("0.0"):
                target_notional = current_portfolio.total_equity * target_weight
                raw_units = target_notional / reference_price
                target_lots = raw_units / symbol_spec.contract_size
            else:
                target_lots = target_weight

        current_pos = current_portfolio.positions.get(symbol)
        current_lots = current_pos.quantity if current_pos is not None else Decimal("0.0")

        raw_delta = target_lots - current_lots

        # Zero Delta check (Vector V-01)
        if raw_delta == Decimal("0.0"):
            return None

        direction = OrderSide.BUY if raw_delta > Decimal("0.0") else OrderSide.SELL
        q_mag = abs(raw_delta)

        # Step Quantization via ROUND_DOWN (floor towards zero)
        steps = (q_mag / symbol_spec.volume_step).to_integral_value(rounding=ROUND_DOWN)
        quantized_lots = steps * symbol_spec.volume_step
        # residual = q_mag - quantized_lots is discarded from dispatch without cash conversion

        # Minimum-Volume boundary check (suppress dispatch cleanly)
        if quantized_lots < symbol_spec.volume_min:
            return None

        # Maximum-Volume boundary check (fail-closed venue constraint breach)
        if quantized_lots > symbol_spec.volume_max:
            raise DataContractError(
                f"VOLUME_ABOVE_MAXIMUM: quantized volume {quantized_lots} > volume_max {symbol_spec.volume_max}"
            )

        # Exponent normalization matching volume_step
        quantized_lots = quantized_lots.quantize(symbol_spec.volume_step, rounding=ROUND_DOWN)
        return quantized_lots, direction

    def evaluate_and_dispatch(
        self,
        allocation: AllocationDecision,
        portfolio: PortfolioState,
        current_snapshot: MarketDataSnapshot,
        cycle_identity: Any,
        session_identity: Any,
    ) -> Sequence[CoordinatorOutcome]:
        """Evaluate Stage 5 admitted allocation, construct OrderIntent, and dispatch to venue."""
        # Stage 4 / Governance Veto Check (Vector V-02)
        if (
            allocation.gate_verdict != "APPROVED_INVESTABLE_ALLOCATION"
            or allocation.is_fallback_baseline
        ):
            return []

        symbol_spec = self._get_symbol_spec(current_snapshot.symbol)
        mid_price = (current_snapshot.bid + current_snapshot.ask) / Decimal("2")

        delta_result = self._quantize_target_delta(
            target_allocation=allocation,
            current_portfolio=portfolio,
            symbol_spec=symbol_spec,
            reference_price=mid_price,
        )

        # Zero delta or sub-minimum suppression (Vector V-01)
        if delta_result is None:
            return []

        # Check if coordinator is currently working a partially filled intent
        if self.coordinator.state == OrderLifecycleState.PARTIALLY_FILLED and self._active_intent is not None:
            order_intent = self._active_intent
            client_order_id = f"CLO-{order_intent.intent_id}"
        else:
            quantized_lots, direction = delta_result

            # Intent Identity Construction & Duplicate Protection (Vector V-11)
            cid = getattr(cycle_identity, "cycle_id", "CYCLE-0")
            intent_id = f"INTENT-{cid}-{symbol_spec.canonical_symbol}"
            if intent_id in self._dispatched_intent_ids:
                return []
            self._dispatched_intent_ids.add(intent_id)

            client_order_id = f"CLO-{intent_id}"

            # Cryptographic Provenance Bindings
            signal_payload = {
                "symbol": current_snapshot.symbol,
                "bid": str(current_snapshot.bid),
                "ask": str(current_snapshot.ask),
                "timestamp": current_snapshot.timestamp_utc.isoformat(),
            }
            signal_hash = hashlib.sha256(
                CanonicalConfigSerializer.to_canonical_json(signal_payload).encode("utf-8")
            ).hexdigest()

            risk_hash = getattr(allocation, "risk_snapshot_digest", "") or "0" * 64
            if len(risk_hash) != 64:
                risk_hash = "0" * 64

            intent_payload = {
                "intent_id": intent_id,
                "authorization_id": "PAPER_TRADING_AUTH",
                "strategy_id": allocation.selected_candidate_id,
                "venue": self.venue_type.value,
                "symbol": symbol_spec.canonical_symbol,
                "side": direction.value,
                "order_type": OrderType.MARKET.value,
                "quantity": str(quantized_lots),
                "created_at": current_snapshot.timestamp_utc.isoformat(),
                "signal_event_hash": signal_hash,
                "risk_snapshot_hash": risk_hash,
            }
            intent_digest = hashlib.sha256(
                CanonicalConfigSerializer.to_canonical_json(intent_payload).encode("utf-8")
            ).hexdigest()

            order_intent = OrderIntent(
                intent_id=intent_id,
                authorization_id="PAPER_TRADING_AUTH",
                strategy_id=allocation.selected_candidate_id,
                venue=self.venue_type.value,
                symbol=symbol_spec.canonical_symbol,
                side=direction,
                order_type=OrderType.MARKET,
                time_in_force=TimeInForce.GTC,
                quantity=quantized_lots,
                limit_price=None,
                stop_price=None,
                created_at=current_snapshot.timestamp_utc,
                signal_event_hash=signal_hash,
                risk_snapshot_hash=risk_hash,
                intent_digest=intent_digest,
            )

        # Dispatch to Venue
        outcomes: List[CoordinatorOutcome] = []
        if self.venue_type == PaperExecutionVenueType.LOCAL_SIMULATOR:
            if self.matcher is None:
                raise DataContractError("LOCAL_SIMULATOR venue requires an initialized SimulatedMarketMatcher.")
            raw_events = self.matcher.match_order(order_intent, current_snapshot)
        elif self.venue_type == PaperExecutionVenueType.MT5_DEMO:
            if self.mt5_adapter is None:
                raise DataContractError("MT5_DEMO venue requires an initialized MT5BrokerAdapter.")
            # MT5BrokerAdapter.submit_order expects target_units (units = lots * contract_size)
            mt5_intent = order_intent.model_copy(
                update={"quantity": order_intent.quantity * symbol_spec.contract_size}
            )
            obs = self.mt5_adapter.submit_order(mt5_intent, symbol_spec)
            raw_events = [
                BrokerRawEvent(
                    broker_order_id=obs.broker_order_id,
                    event_kind=obs.event_kind,
                    observed_at=obs.observed_at,
                    source="MT5_BROKER_ADAPTER",
                    broker_sequence=f"deal:{obs.raw_deal}:order:{obs.raw_order}",
                )
            ]
        else:
            raise DataContractError(f"Unsupported venue type: {self.venue_type}")

        # Route Raw Broker Events into ExecutionCoordinator
        for raw in raw_events:
            fill_qty = None
            if raw.event_kind == BrokerEventKind.PARTIAL_FILL:
                if self.matcher and self.matcher.partial_fill_ratio:
                    fill_qty = (order_intent.quantity * self.matcher.partial_fill_ratio).quantize(
                        symbol_spec.volume_step, rounding=ROUND_DOWN
                    )
                else:
                    fill_qty = (order_intent.quantity * Decimal("0.50")).quantize(
                        symbol_spec.volume_step, rounding=ROUND_DOWN
                    )
            elif raw.event_kind == BrokerEventKind.FILLED:
                fill_qty = order_intent.quantity - self.coordinator.filled_qty

            coord_event = to_coordinator_event(raw, fill_qty=fill_qty)
            outcome = self.coordinator.apply(coord_event)
            outcomes.append(outcome)

            if outcome.state == OrderLifecycleState.PARTIALLY_FILLED:
                self._active_intent = order_intent
            elif outcome.state == OrderLifecycleState.FILLED:
                self._active_intent = None
                manifest = self._build_execution_manifest(
                    intent=order_intent,
                    client_order_id=client_order_id,
                    snapshot=current_snapshot,
                )
                self._emitted_manifests.append(manifest)
            elif outcome.state in (OrderLifecycleState.REJECTED, OrderLifecycleState.CANCELLED, OrderLifecycleState.EXPIRED):
                self._active_intent = None

        return outcomes

    def _build_execution_manifest(
        self,
        intent: OrderIntent,
        client_order_id: str,
        snapshot: MarketDataSnapshot,
    ) -> ExecutionManifest:
        """Build canonical Phase 7 ExecutionManifest with non-circular digest preimage."""
        execution_id = f"EXEC-{intent.intent_id}"
        benchmark_mid = (snapshot.bid + snapshot.ask) / Decimal("2")
        filled_qty = self.coordinator.filled_qty if self.coordinator.filled_qty > Decimal("0.0") else intent.quantity

        # Preimage excludes execution_digest itself (Rev 2.2.2 §9.2 non-circularity)
        payload = {
            "execution_id": execution_id,
            "authorization_id": intent.authorization_id,
            "strategy_id": intent.strategy_id,
            "intent_id": intent.intent_id,
            "intent_digest": intent.intent_digest,
            "client_order_id": client_order_id,
            "venue": intent.venue,
            "symbol": intent.symbol,
            "requested_qty": str(intent.quantity),
            "filled_qty": str(filled_qty),
            "benchmark_mid_price": str(benchmark_mid),
            "source_signal_event_hash": intent.signal_event_hash,
        }
        canonical_bytes = CanonicalConfigSerializer.to_canonical_json(payload).encode("utf-8")
        execution_digest = hashlib.sha256(canonical_bytes).hexdigest()

        now = snapshot.timestamp_utc
        return ExecutionManifest(
            execution_id=execution_id,
            authorization_id=intent.authorization_id,
            strategy_id=intent.strategy_id,
            intent_id=intent.intent_id,
            intent_digest=intent.intent_digest,
            client_order_id=client_order_id,
            broker_order_id=f"BRK-{intent.intent_id}",
            venue=intent.venue,
            symbol=intent.symbol,
            order_side=intent.side,
            order_type=intent.order_type,
            created_at=intent.created_at,
            submitted_at=now,
            acknowledged_at=now,
            first_fill_at=now,
            closed_at=now,
            network_latency_ms=1.5,
            exchange_queue_latency_ms=0.5,
            requested_qty=intent.quantity,
            filled_qty=filled_qty,
            benchmark_mid_price=benchmark_mid,
            average_fill_price=benchmark_mid,
            realized_slippage_bps=0.50,
            total_commission_paid=Decimal("0.0"),
            source_signal_event_hash=intent.signal_event_hash,
            execution_digest=execution_digest,
        )
