r"""Phase 12 Slice 4: Authoritative 6-Dimensional Reconciliation Engine (RECON-6D).

Implements the multi-venue execution reconciliation loop defined in
docs/phase12/contract_specification_v1.md.

Authority Separation Invariant:
$$\boxed{\mathbf{ReconciliationEngine} \neq \mathbf{StateAuthority} \quad \land \quad \mathbf{BrokerAdapter} \neq \mathbf{StateAuthority}}$$

The reconciliation engine is an Evidence Emission Authority. It compares the
authoritative broker reality against the ACASH sovereign shadow ledger across 6
mandatory dimensions:
$$\text{Reconciliation} = (\text{Balance}, \text{Equity}, \text{Margin}, \text{Positions}, \text{Resting Orders}, \text{Historical Deals})$$
It produces typed ReconciliationEvidence for in-flight orders, detects operational
anomalies (phantom positions, orphan orders, equity drift, boundary activity ambiguity),
and issues MT5ReconciliationConfirmation if and only if zero critical discrepancies exist.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
import math
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Protocol, Sequence, Set, Tuple

from pydantic import BaseModel, ConfigDict, Field

from acash.execution.broker_events import (
    BrokerEventKind,
    ReconciliationEvidence,
    normalize_broker_event,
)
from acash.execution.coordinator import CoordinatorOutcome, ExecutionCoordinator
from acash.execution.operational_restriction import (
    OperationalRestrictionRequest,
    RestrictionReason,
    RestrictionScope,
)
from acash.execution.schema import OrderLifecycleState
from acash.execution.mt5.adapter import MT5BrokerAdapter
from acash.execution.mt5.enums import (
    MT5AccountMarginMode,
    MT5DealEntry,
    MT5DealType,
    MT5OrderState,
    MT5OrderType,
    MT5PositionType,
)
from acash.execution.mt5.exceptions import (
    MT5DomainError,
    MT5ReconciliationError,
    MT5TransportError,
    MT5ValidationError,
    ReconciliationIntegrityError,
)
from acash.execution.mt5.schemas import (
    MT5AccountReality,
    MT5DealReality,
    MT5OrderReality,
    MT5PositionReality,
)
from acash.execution.mt5.transport import (
    MT5HealthReport,
    MT5ReconciliationConfirmation,
    MT5TransportProtocol,
    MT5TransportSafetyState,
)


# ============================================================================
# 1. CANONICAL SERIALIZATION & HASHING HELPERS
# ============================================================================


def _normalize_for_canonical_json(obj: Any) -> Any:
    """Recursively normalize objects for deterministic JSON encoding."""
    if isinstance(obj, Decimal):
        if not obj.is_finite():
            raise MT5ValidationError("CANONICAL_JSON_NON_FINITE_DECIMAL")
        # Strip trailing zeros deterministically
        return f"{obj.normalize():f}"
    if isinstance(obj, datetime):
        utc_dt = obj.astimezone(timezone.utc)
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, BaseModel):
        return _normalize_for_canonical_json(obj.model_dump())
    if isinstance(obj, dict):
        return {str(k): _normalize_for_canonical_json(v) for k, v in sorted(obj.items())}
    if isinstance(obj, (list, tuple)):
        return [_normalize_for_canonical_json(item) for item in obj]
    return obj


def canonical_json(data: Any) -> str:
    """Deterministic JSON serialization: sorted keys, stripped decimals, ISO UTC timestamps."""
    normalized = _normalize_for_canonical_json(data)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"))


def compute_payload_digest(payload: Any) -> str:
    """Compute deterministic SHA-256 digest over canonical JSON representation."""
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


# ============================================================================
# 2. DISCREPANCY TAXONOMY & TOLERANCE CONFIGURATION
# ============================================================================


class MT5DiscrepancyKind(str, Enum):
    """Canonical classification of reconciliation discrepancies."""

    BALANCE_MISMATCH = "BALANCE_MISMATCH"
    EQUITY_MISMATCH = "EQUITY_MISMATCH"
    MARGIN_MISMATCH = "MARGIN_MISMATCH"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    PHANTOM_POSITION = "PHANTOM_POSITION"
    MISSING_POSITION = "MISSING_POSITION"
    POSITION_VOLUME_MISMATCH = "POSITION_VOLUME_MISMATCH"
    POSITION_SIDE_MISMATCH = "POSITION_SIDE_MISMATCH"
    ORPHAN_RESTING_ORDER = "ORPHAN_RESTING_ORDER"
    MISSING_RESTING_ORDER = "MISSING_RESTING_ORDER"
    ORDER_PARAMETER_MISMATCH = "ORDER_PARAMETER_MISMATCH"
    UNTRACKED_TRADE_DEAL = "UNTRACKED_TRADE_DEAL"
    STALE_SNAPSHOT = "STALE_SNAPSHOT"
    INCOMPLETE_HISTORY_SCOPE = "INCOMPLETE_HISTORY_SCOPE"
    INCOHERENT_SNAPSHOT = "INCOHERENT_SNAPSHOT"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    DISPUTED_STATE = "DISPUTED_STATE"


class MT5DiscrepancySeverity(str, Enum):
    """Severity category for discrepancies."""

    CRITICAL = "CRITICAL"
    WARNING = "WARNING"


class MT5Discrepancy(BaseModel):
    """Immutable forensic record of an individual reconciliation discrepancy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: MT5DiscrepancyKind
    severity: MT5DiscrepancySeverity
    dimension: str
    identifier: str
    expected_value: str
    observed_value: str
    delta: Optional[Decimal] = None
    detail: str = ""


class ReconciliationToleranceConfig(BaseModel):
    """Configurable numerical tolerance thresholds denominated in account currency."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    balance_tolerance: Decimal = Field(default=Decimal("0.05"), ge=Decimal("0.0"))
    equity_tolerance: Decimal = Field(default=Decimal("0.10"), ge=Decimal("0.0"))
    margin_tolerance: Decimal = Field(default=Decimal("0.05"), ge=Decimal("0.0"))
    max_snapshot_age_seconds: float = Field(default=30.0, gt=0.0)
    max_capture_window_ms: float = Field(default=2000.0, gt=0.0)


# ============================================================================
# 3. CANONICAL DEAL DECODING & ARCHITECTURAL CATEGORIZATION
# ============================================================================

# Protocol Boundary Decode Table — maps raw external MQL5 integer to canonical MT5DealType
_MQL5_DEAL_TYPE_DECODE_MAP: Dict[int, MT5DealType] = {
    0: MT5DealType.DEAL_TYPE_BUY,
    1: MT5DealType.DEAL_TYPE_SELL,
    2: MT5DealType.DEAL_TYPE_BALANCE,
    3: MT5DealType.DEAL_TYPE_CREDIT,
    4: MT5DealType.DEAL_TYPE_CHARGE,
    5: MT5DealType.DEAL_TYPE_CORRECTION,
    6: MT5DealType.DEAL_TYPE_BONUS,
    7: MT5DealType.DEAL_TYPE_COMMISSION,
    8: MT5DealType.DEAL_TYPE_COMMISSION_DAILY,
    9: MT5DealType.DEAL_TYPE_COMMISSION_MONTHLY,
    10: MT5DealType.DEAL_TYPE_COMMISSION_AGENT_DAILY,
    11: MT5DealType.DEAL_TYPE_INTEREST,
    12: MT5DealType.DEAL_DIVIDEND,
    13: MT5DealType.DEAL_DIVIDEND_FRANKED,
    14: MT5DealType.DEAL_TAX,
    15: MT5DealType.DEAL_TYPE_COMMISSION_AGENT_MONTHLY,
    16: MT5DealType.DEAL_TYPE_BUY_CANCELED,
    17: MT5DealType.DEAL_TYPE_SELL_CANCELED,
}


def decode_mt5_deal_type(raw_dtype: int) -> MT5DealType:
    """Protocol boundary decoder: maps raw external MQL5 integer to canonical MT5DealType."""
    if raw_dtype not in _MQL5_DEAL_TYPE_DECODE_MAP:
        raise MT5DomainError(f"UNKNOWN_MQL5_DEAL_TYPE: {raw_dtype}")
    return _MQL5_DEAL_TYPE_DECODE_MAP[raw_dtype]


class MT5DealCategory(str, Enum):
    """Architectural classification of canonical deal types."""

    TRADE_EXECUTION_DEAL = "TRADE_EXECUTION_DEAL"
    CANCELED_TRADE_DEAL = "CANCELED_TRADE_DEAL"
    ACCOUNTING_DEAL = "ACCOUNTING_DEAL"
    CORPORATE_ACTION_DEAL = "CORPORATE_ACTION_DEAL"
    UNKNOWN_DEAL_TYPE = "UNKNOWN_DEAL_TYPE"


DEAL_CATEGORY_MAP: Dict[MT5DealType, MT5DealCategory] = {
    MT5DealType.DEAL_TYPE_BUY: MT5DealCategory.TRADE_EXECUTION_DEAL,
    MT5DealType.DEAL_TYPE_SELL: MT5DealCategory.TRADE_EXECUTION_DEAL,
    MT5DealType.DEAL_TYPE_BUY_CANCELED: MT5DealCategory.CANCELED_TRADE_DEAL,
    MT5DealType.DEAL_TYPE_SELL_CANCELED: MT5DealCategory.CANCELED_TRADE_DEAL,
    MT5DealType.DEAL_TYPE_BALANCE: MT5DealCategory.ACCOUNTING_DEAL,
    MT5DealType.DEAL_TYPE_CREDIT: MT5DealCategory.ACCOUNTING_DEAL,
    MT5DealType.DEAL_TYPE_CHARGE: MT5DealCategory.ACCOUNTING_DEAL,
    MT5DealType.DEAL_TYPE_CORRECTION: MT5DealCategory.ACCOUNTING_DEAL,
    MT5DealType.DEAL_TYPE_BONUS: MT5DealCategory.ACCOUNTING_DEAL,
    MT5DealType.DEAL_TYPE_COMMISSION: MT5DealCategory.ACCOUNTING_DEAL,
    MT5DealType.DEAL_TYPE_COMMISSION_DAILY: MT5DealCategory.ACCOUNTING_DEAL,
    MT5DealType.DEAL_TYPE_COMMISSION_MONTHLY: MT5DealCategory.ACCOUNTING_DEAL,
    MT5DealType.DEAL_TYPE_COMMISSION_AGENT_DAILY: MT5DealCategory.ACCOUNTING_DEAL,
    MT5DealType.DEAL_TYPE_COMMISSION_AGENT_MONTHLY: MT5DealCategory.ACCOUNTING_DEAL,
    MT5DealType.DEAL_TYPE_INTEREST: MT5DealCategory.ACCOUNTING_DEAL,
    MT5DealType.DEAL_DIVIDEND: MT5DealCategory.CORPORATE_ACTION_DEAL,
    MT5DealType.DEAL_DIVIDEND_FRANKED: MT5DealCategory.CORPORATE_ACTION_DEAL,
    MT5DealType.DEAL_TAX: MT5DealCategory.CORPORATE_ACTION_DEAL,
}


def categorize_deal(canonical_type: MT5DealType) -> MT5DealCategory:
    """Classify canonical MT5DealType into architectural category (zero raw integer business logic)."""
    if canonical_type not in DEAL_CATEGORY_MAP:
        raise MT5DomainError(f"UNMAPPED_CANONICAL_DEAL_TYPE: {canonical_type}")
    return DEAL_CATEGORY_MAP[canonical_type]


# ============================================================================
# 4. HISTORICAL DEAL SCOPE & CAPTURE CONTEXT
# ============================================================================


class HistoricalDealScopeKind(str, Enum):
    """Coverage scope for historical deal queries."""

    FULL_CYCLE = "FULL_CYCLE"
    WATERMARK_INCREMENTAL = "WATERMARK_INCREMENTAL"
    TARGETED_LINEAGE = "TARGETED_LINEAGE"


class HistoricalDealCoverage(BaseModel):
    """Explicit coverage contract proving completeness of historical deal observation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    scope_kind: HistoricalDealScopeKind
    from_timestamp: datetime
    to_timestamp: datetime
    watermark_ticket: Optional[int] = None
    watermark_time_msc: Optional[int] = None
    last_deal_ticket: Optional[int] = None
    total_deals_retrieved: int
    is_complete: bool
    coverage_digest: str


class CaptureCompletenessStatus(str, Enum):
    """Status of observation capture query cycle."""

    COMPLETE = "COMPLETE"
    BOUNDARY_ACTIVITY_DETECTED = "BOUNDARY_ACTIVITY_DETECTED"
    CAPTURE_TIMEOUT = "CAPTURE_TIMEOUT"
    PARTIAL_QUERY_FAILED = "PARTIAL_QUERY_FAILED"


class ReconciliationCaptureContext(BaseModel):
    """Observation capture metadata defining temporal bounds, latencies, and multi-pass provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reconciliation_id: str
    capture_started_at: datetime
    capture_completed_at: datetime
    capture_started_at_msc: int
    capture_completed_at_msc: int
    pre_watermark_deal_ticket: int
    post_watermark_deal_ticket: int
    query_latencies_ms: Dict[str, float]
    capture_duration_ms: float
    max_capture_window_ms: float
    completeness_status: CaptureCompletenessStatus
    boundary_activity_detected: bool = False
    recapture_attempt: int = 0
    prior_capture_context: Optional["ReconciliationCaptureContext"] = None

    @property
    def is_coherent(self) -> bool:
        return (
            self.completeness_status == CaptureCompletenessStatus.COMPLETE
            and not self.boundary_activity_detected
            and self.capture_duration_ms <= self.max_capture_window_ms
        )


# ============================================================================
# 5. SHADOW LEDGER & BROKER REALITY SNAPSHOTS
# ============================================================================


class ShadowPosition(BaseModel):
    """ACASH shadow ledger position state supporting netting reversals and hedging."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    position_ticket: int = Field(gt=0)
    position_identifier: int = Field(gt=0)
    symbol: str = Field(min_length=1)
    side: str
    volume: Decimal = Field(gt=Decimal("0.0"))
    open_price: Decimal = Field(gt=Decimal("0.0"))
    magic: int = 0
    comment: str = ""


class ShadowRestingOrder(BaseModel):
    """ACASH shadow ledger resting order state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    intent_id: str
    order_ticket: int = Field(gt=0)
    symbol: str = Field(min_length=1)
    order_type: str
    volume: Decimal = Field(gt=Decimal("0.0"))
    price: Optional[Decimal] = None
    magic: int = 0
    comment: str = ""


class ShadowDealRecord(BaseModel):
    """ACASH shadow ledger recorded trade execution deal."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    deal_ticket: int = Field(gt=0)
    order_ticket: int = Field(gt=0)
    position_id: int = Field(ge=0)
    intent_id: str
    symbol: str = Field(min_length=1)
    side: str
    volume: Decimal = Field(gt=Decimal("0.0"))
    price: Decimal = Field(gt=Decimal("0.0"))
    commission: Decimal = Decimal("0.0")
    executed_at: datetime


class ACASHShadowLedgerSnapshot(BaseModel):
    """Immutable snapshot of the sovereign ACASH shadow ledger for an account."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0.0"
    broker_id: str
    account_id: str
    terminal_instance_id: str
    currency: str
    snapshot_at: datetime
    balance: Decimal
    equity: Decimal
    margin: Decimal
    positions: Tuple[ShadowPosition, ...]
    resting_orders: Tuple[ShadowRestingOrder, ...]
    deals: Tuple[ShadowDealRecord, ...]
    ledger_digest: str


class ACASHShadowLedger(Protocol):
    """Account-wide shadow ledger interface aggregating cash, margin, and order states."""

    def snapshot_reconciliation_state(self) -> ACASHShadowLedgerSnapshot:
        """Return an immutable account-wide snapshot across all 6 dimensions."""
        ...


class MT5BrokerRealitySnapshot(BaseModel):
    """Immutable coherent-enough bounded observation of raw broker reality."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0.0"
    broker_id: str
    account_id: str
    terminal_instance_id: str
    observed_at: datetime
    account: MT5AccountReality
    positions: Tuple[MT5PositionReality, ...]
    orders: Tuple[MT5OrderReality, ...]
    history_orders: Tuple[MT5OrderReality, ...]
    deals: Tuple[MT5DealReality, ...]
    deal_coverage: HistoricalDealCoverage
    capture_context: ReconciliationCaptureContext
    broker_snapshot_digest: str


# ============================================================================
# 6. RECONCILIATION REPORT & CONFIRMATION
# ============================================================================


class ReconciliationStatus(str, Enum):
    """Overall outcome of the 6-D reconciliation audit."""

    CLEAN = "CLEAN"
    DISCREPANCIES_DETECTED = "DISCREPANCIES_DETECTED"
    RECONCILIATION_FAILED = "RECONCILIATION_FAILED"


class MT56DReconciliationReport(BaseModel):
    """Comprehensive, tamper-evident audit report across all 6 dimensions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0.0"
    reconciliation_id: str
    broker_id: str
    account_id: str
    terminal_instance_id: str
    reconciled_at: datetime
    status: ReconciliationStatus
    tolerances: ReconciliationToleranceConfig
    dimension_verification: Dict[str, bool]
    failure_reason: Optional[MT5DiscrepancyKind] = None
    discrepancies: Tuple[MT5Discrepancy, ...]
    confirmation: Optional[MT5ReconciliationConfirmation] = None
    resolved_orders: Tuple[ReconciliationEvidence, ...] = ()
    ledger_digest: str
    broker_snapshot_digest: str
    report_digest: str

    @property
    def is_clean(self) -> bool:
        return self.status == ReconciliationStatus.CLEAN and len(self.discrepancies) == 0


# ============================================================================
# 7. DOMAIN PREDICATES & EVALUATION FUNCTIONS
# ============================================================================


def match_position_identity(
    shadow_pos: ShadowPosition,
    broker_pos: MT5PositionReality,
    margin_mode: MT5AccountMarginMode,
) -> bool:
    """Strict margin-mode-aware position matching predicate.

    Zero loose OR conditions. All matches require symbol equality and valid position_identifier.
    """
    if not broker_pos.position_identifier or broker_pos.position_identifier <= 0:
        raise MT5ValidationError(
            f"INVALID_BROKER_POSITION_IDENTIFIER: ticket={broker_pos.position_ticket}, "
            f"identifier={broker_pos.position_identifier}"
        )
    if not shadow_pos.position_identifier or shadow_pos.position_identifier <= 0:
        raise MT5ValidationError(
            f"INVALID_SHADOW_POSITION_IDENTIFIER: ticket={shadow_pos.position_ticket}, "
            f"identifier={shadow_pos.position_identifier}"
        )

    if margin_mode in (
        MT5AccountMarginMode.ACCOUNT_MARGIN_MODE_RETAIL_NETTING,
        MT5AccountMarginMode.ACCOUNT_MARGIN_MODE_EXCHANGE,
    ):
        # Netting: primary authority is immutable position_identifier AND symbol must match
        return (
            shadow_pos.position_identifier == broker_pos.position_identifier
            and shadow_pos.symbol == broker_pos.symbol
        )
    elif margin_mode == MT5AccountMarginMode.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING:
        # Hedging: primary authority is (position_ticket, position_identifier) AND symbol must match
        return (
            shadow_pos.position_ticket == broker_pos.position_ticket
            and shadow_pos.position_identifier == broker_pos.position_identifier
            and shadow_pos.symbol == broker_pos.symbol
        )
    else:
        raise MT5DomainError(f"UNKNOWN_MARGIN_MODE: {margin_mode}")


def verify_order_deal_execution(
    order_ticket: int,
    historical_order: MT5OrderReality,
    matching_deals: Sequence[MT5DealReality],
) -> Tuple[OrderLifecycleState, Decimal, Decimal, str, Tuple[str, ...]]:
    """Authoritative lifecycle proof of execution volume and terminal state.

    Enforces canonical multi-deal ordering (deal_time_msc, deal_ticket).
    Excludes canceled deal types (BUY_CANCELED, SELL_CANCELED) from fresh execution volume.
    Returns (resolved_state, total_executed_volume, vwap, broker_event_id, evidence_refs).
    """
    # Deterministic canonical ordering
    sorted_deals = sorted(
        matching_deals,
        key=lambda d: (int(d.deal_time_utc.timestamp() * 1000), d.deal_ticket),
    )

    # Exclude canceled deal types from fresh execution volume
    execution_deals = [
        d for d in sorted_deals if categorize_deal(d.deal_type) == MT5DealCategory.TRADE_EXECUTION_DEAL
    ]

    total_volume = sum((d.volume for d in execution_deals), Decimal("0.0"))
    if total_volume > Decimal("0.0"):
        total_cost = sum((d.volume * d.price for d in execution_deals), Decimal("0.0"))
        vwap = total_cost / total_volume
    else:
        vwap = Decimal("0.0")

    # Relational Validation: Direction (DEAL_TYPE) and Lifecycle (DEAL_ENTRY)
    buy_order_types = {
        MT5OrderType.BUY, MT5OrderType.BUY_LIMIT, MT5OrderType.BUY_STOP, MT5OrderType.BUY_STOP_LIMIT
    }
    sell_order_types = {
        MT5OrderType.SELL, MT5OrderType.SELL_LIMIT, MT5OrderType.SELL_STOP, MT5OrderType.SELL_STOP_LIMIT
    }

    for d in execution_deals:
        # 1. Directional validation
        if historical_order.order_type in buy_order_types and d.deal_type != MT5DealType.DEAL_TYPE_BUY:
            raise MT5ReconciliationError(
                f"DEAL_DIRECTION_MISMATCH: order {historical_order.order_ticket} is {historical_order.order_type.value} "
                f"but execution deal {d.deal_ticket} is {d.deal_type.value}"
            )
        if historical_order.order_type in sell_order_types and d.deal_type != MT5DealType.DEAL_TYPE_SELL:
            raise MT5ReconciliationError(
                f"DEAL_DIRECTION_MISMATCH: order {historical_order.order_ticket} is {historical_order.order_type.value} "
                f"but execution deal {d.deal_ticket} is {d.deal_type.value}"
            )

        # 2. Entry lifecycle validation
        if d.entry == MT5DealEntry.DEAL_ENTRY_OUT_BY:
            raise MT5DomainError(
                "CLOSE_BY_UNSUPPORTED: DEAL_ENTRY_OUT_BY is not authorized under current contract"
            )
        if d.entry is not None:
            if d.entry not in (
                MT5DealEntry.DEAL_ENTRY_IN,
                MT5DealEntry.DEAL_ENTRY_OUT,
                MT5DealEntry.DEAL_ENTRY_INOUT,
            ):
                raise MT5DomainError(f"UNSUPPORTED_DEAL_ENTRY: {d.entry.value}")

            # Position opening orders (position_ticket is None or 0) cannot produce DEAL_ENTRY_OUT
            is_opening_order = (
                historical_order.position_ticket is None or historical_order.position_ticket == 0
            )
            if is_opening_order and d.entry == MT5DealEntry.DEAL_ENTRY_OUT:
                raise MT5ReconciliationError(
                    f"RELATIONAL_ENTRY_MISMATCH: opening order {historical_order.order_ticket} produced DEAL_ENTRY_OUT"
                )
            # Position closing orders (position_ticket > 0) cannot produce DEAL_ENTRY_IN
            if not is_opening_order and d.entry == MT5DealEntry.DEAL_ENTRY_IN:
                raise MT5ReconciliationError(
                    f"RELATIONAL_ENTRY_MISMATCH: closing order {historical_order.order_ticket} produced DEAL_ENTRY_IN"
                )

    order_state = historical_order.state
    if not isinstance(order_state, MT5OrderState):
        raise MT5DomainError(f"INVALID_ORDER_STATE_TYPE: expected MT5OrderState, got {type(order_state)}")

    # 1. Authoritative FILLED proof
    if order_state == MT5OrderState.ORDER_STATE_FILLED:
        if total_volume != historical_order.volume_initial:
            raise MT5ReconciliationError(
                f"FILLED_VOLUME_MISMATCH: deal_volume={total_volume} != initial={historical_order.volume_initial}"
            )
        if not execution_deals:
            raise MT5ReconciliationError("FILLED_ORDER_WITHOUT_EXECUTION_DEALS")
        final_deal = execution_deals[-1]
        broker_event_id = str(final_deal.deal_ticket)
        evidence_refs = tuple(str(d.deal_ticket) for d in execution_deals)
        return OrderLifecycleState.FILLED, total_volume, vwap, broker_event_id, evidence_refs

    # 2. Authoritative CANCELLED proof
    if order_state == MT5OrderState.ORDER_STATE_CANCELED:
        broker_event_id = str(historical_order.order_ticket)
        evidence_refs = tuple(str(d.deal_ticket) for d in execution_deals)
        return OrderLifecycleState.CANCELLED, total_volume, vwap, broker_event_id, evidence_refs

    # 3. Authoritative REJECTED proof
    if order_state == MT5OrderState.ORDER_STATE_REJECTED:
        broker_event_id = str(historical_order.order_ticket)
        return OrderLifecycleState.REJECTED, Decimal("0.0"), Decimal("0.0"), broker_event_id, ()

    # 4. Authoritative EXPIRED proof
    if order_state == MT5OrderState.ORDER_STATE_EXPIRED:
        broker_event_id = str(historical_order.order_ticket)
        return OrderLifecycleState.EXPIRED, Decimal("0.0"), Decimal("0.0"), broker_event_id, ()

    raise MT5ReconciliationError(f"UNSUPPORTED_TERMINAL_ORDER_STATE: {order_state.value}")


# ============================================================================
# 8. AUTHORITATIVE 6-DIMENSIONAL RECONCILIATION ENGINE
# ============================================================================


class MT5ReconciliationEngine:
    """Authoritative 6-Dimensional Reconciliation Engine (RECON-6D)."""

    def __init__(self, tolerances: Optional[ReconciliationToleranceConfig] = None) -> None:
        self.tolerances = tolerances or ReconciliationToleranceConfig()

    def reconcile_6d(
        self,
        shadow: ACASHShadowLedgerSnapshot,
        broker: MT5BrokerRealitySnapshot,
        tolerances: Optional[ReconciliationToleranceConfig] = None,
        coordinator_map: Optional[Mapping[str, ExecutionCoordinator]] = None,
    ) -> MT56DReconciliationReport:
        """Perform authoritative 6-dimensional reconciliation audit."""
        cfg = tolerances or self.tolerances
        reconciliation_id = f"RECON_{shadow.broker_id}_{shadow.account_id}_{int(time.time() * 1000)}"
        reconciled_at = datetime.now(timezone.utc)
        discrepancies: List[MT5Discrepancy] = []
        resolved_orders: List[ReconciliationEvidence] = []

        dim_verification: Dict[str, bool] = {
            "balance": False,
            "equity": False,
            "margin": False,
            "positions": False,
            "orders": False,
            "deals": False,
        }

        # 0. Provenance & Identity Invariant Checks
        if shadow.broker_id != broker.broker_id:
            discrepancies.append(
                MT5Discrepancy(
                    kind=MT5DiscrepancyKind.IDENTITY_MISMATCH,
                    severity=MT5DiscrepancySeverity.CRITICAL,
                    dimension="identity",
                    identifier="broker_id",
                    expected_value=shadow.broker_id,
                    observed_value=broker.broker_id,
                    detail="Mismatched broker_id across shadow and broker snapshots.",
                )
            )
        if shadow.account_id != broker.account_id:
            discrepancies.append(
                MT5Discrepancy(
                    kind=MT5DiscrepancyKind.IDENTITY_MISMATCH,
                    severity=MT5DiscrepancySeverity.CRITICAL,
                    dimension="identity",
                    identifier="account_id",
                    expected_value=shadow.account_id,
                    observed_value=broker.account_id,
                    detail="Mismatched account_id across shadow and broker snapshots.",
                )
            )
        if shadow.terminal_instance_id != broker.terminal_instance_id:
            discrepancies.append(
                MT5Discrepancy(
                    kind=MT5DiscrepancyKind.IDENTITY_MISMATCH,
                    severity=MT5DiscrepancySeverity.CRITICAL,
                    dimension="identity",
                    identifier="terminal_instance_id",
                    expected_value=shadow.terminal_instance_id,
                    observed_value=broker.terminal_instance_id,
                    detail="Mismatched terminal_instance_id across shadow and broker snapshots.",
                )
            )

        currency_mismatch = shadow.currency != broker.account.currency
        if currency_mismatch:
            discrepancies.append(
                MT5Discrepancy(
                    kind=MT5DiscrepancyKind.CURRENCY_MISMATCH,
                    severity=MT5DiscrepancySeverity.CRITICAL,
                    dimension="currency",
                    identifier="account_currency",
                    expected_value=shadow.currency,
                    observed_value=broker.account.currency,
                    detail="Account base currency mismatch. Financial dimensions unverifiable.",
                )
            )
            dim_verification["balance"] = False
            dim_verification["equity"] = False
            dim_verification["margin"] = False

        # 0.1 Cryptographic Lineage Verification
        expected_shadow_digest = compute_payload_digest(
            {
                "schema_version": shadow.schema_version,
                "broker_id": shadow.broker_id,
                "account_id": shadow.account_id,
                "terminal_instance_id": shadow.terminal_instance_id,
                "currency": shadow.currency,
                "snapshot_at": shadow.snapshot_at,
                "balance": shadow.balance,
                "equity": shadow.equity,
                "margin": shadow.margin,
                "positions": shadow.positions,
                "resting_orders": shadow.resting_orders,
                "deals": shadow.deals,
            }
        )
        if shadow.ledger_digest != expected_shadow_digest:
            raise ReconciliationIntegrityError(
                f"SHADOW_LEDGER_DIGEST_MISMATCH: expected {expected_shadow_digest}, got {shadow.ledger_digest}"
            )

        expected_broker_digest = compute_payload_digest(
            {
                "schema_version": broker.schema_version,
                "broker_id": broker.broker_id,
                "account_id": broker.account_id,
                "terminal_instance_id": broker.terminal_instance_id,
                "observed_at": broker.observed_at,
                "account": broker.account,
                "positions": broker.positions,
                "orders": broker.orders,
                "history_orders": broker.history_orders,
                "deals": broker.deals,
                "deal_coverage": broker.deal_coverage,
                "capture_context": broker.capture_context,
            }
        )
        if broker.broker_snapshot_digest != expected_broker_digest:
            raise ReconciliationIntegrityError(
                f"BROKER_SNAPSHOT_DIGEST_MISMATCH: expected {expected_broker_digest}, got {broker.broker_snapshot_digest}"
            )

        # 0.2 Freshness & Scope Verification
        snapshot_age = (reconciled_at - broker.observed_at).total_seconds()
        if snapshot_age > cfg.max_snapshot_age_seconds:
            discrepancies.append(
                MT5Discrepancy(
                    kind=MT5DiscrepancyKind.STALE_SNAPSHOT,
                    severity=MT5DiscrepancySeverity.CRITICAL,
                    dimension="freshness",
                    identifier="observed_at",
                    expected_value=f"<={cfg.max_snapshot_age_seconds}s",
                    observed_value=f"{snapshot_age:.1f}s",
                    detail=f"Observation timestamp older than {cfg.max_snapshot_age_seconds}s SLA.",
                )
            )

        if not broker.deal_coverage.is_complete:
            discrepancies.append(
                MT5Discrepancy(
                    kind=MT5DiscrepancyKind.INCOMPLETE_HISTORY_SCOPE,
                    severity=MT5DiscrepancySeverity.CRITICAL,
                    dimension="deals",
                    identifier="deal_coverage",
                    expected_value="is_complete=True",
                    observed_value=f"is_complete={broker.deal_coverage.is_complete}",
                    detail="Historical deal coverage scope incomplete or unverified.",
                )
            )

        if not broker.capture_context.is_coherent:
            discrepancies.append(
                MT5Discrepancy(
                    kind=MT5DiscrepancyKind.INCOHERENT_SNAPSHOT,
                    severity=MT5DiscrepancySeverity.CRITICAL,
                    dimension="coherence",
                    identifier="capture_duration_ms",
                    expected_value=f"<={broker.capture_context.max_capture_window_ms}ms and coherent",
                    observed_value=f"{broker.capture_context.capture_duration_ms:.1f}ms, status={broker.capture_context.completeness_status.value}",
                    detail="Observation capture duration exceeded maximum window or failed coherence.",
                )
            )

        # Check duplicate deal tickets in broker snapshot
        deal_tickets_seen: Set[int] = set()
        for d in broker.deals:
            if d.deal_ticket in deal_tickets_seen:
                raise MT5ValidationError(f"DUPLICATE_DEAL_TICKET: {d.deal_ticket}")
            deal_tickets_seen.add(d.deal_ticket)

        # Check duplicate position tickets in broker snapshot
        pos_tickets_seen: Set[int] = set()
        for p in broker.positions:
            if p.position_ticket in pos_tickets_seen:
                raise MT5ValidationError(f"DUPLICATE_POSITION_TICKET: {p.position_ticket}")
            pos_tickets_seen.add(p.position_ticket)

        # --- FINANCIAL DIMENSIONS (Only verified if currency matches) ---
        if not currency_mismatch:
            # --- DIMENSION 1: BALANCE ---
            delta_balance = abs(broker.account.balance - shadow.balance)
            if delta_balance > cfg.balance_tolerance:
                discrepancies.append(
                    MT5Discrepancy(
                        kind=MT5DiscrepancyKind.BALANCE_MISMATCH,
                        severity=MT5DiscrepancySeverity.CRITICAL,
                        dimension="balance",
                        identifier="balance",
                        expected_value=f"{shadow.balance} {shadow.currency}",
                        observed_value=f"{broker.account.balance} {broker.account.currency}",
                        delta=delta_balance,
                        detail=f"Balance discrepancy {delta_balance} exceeds tolerance {cfg.balance_tolerance}.",
                    )
                )
            else:
                dim_verification["balance"] = True

            # --- DIMENSION 2: EQUITY ---
            delta_equity = abs(broker.account.equity - shadow.equity)
            if delta_equity > cfg.equity_tolerance:
                discrepancies.append(
                    MT5Discrepancy(
                        kind=MT5DiscrepancyKind.EQUITY_MISMATCH,
                        severity=MT5DiscrepancySeverity.CRITICAL,
                        dimension="equity",
                        identifier="equity",
                        expected_value=f"{shadow.equity} {shadow.currency}",
                        observed_value=f"{broker.account.equity} {broker.account.currency}",
                        delta=delta_equity,
                        detail=f"Equity discrepancy {delta_equity} exceeds tolerance {cfg.equity_tolerance}.",
                    )
                )
            else:
                dim_verification["equity"] = True

            # --- DIMENSION 3: MARGIN ---
            delta_margin = abs(broker.account.margin - shadow.margin)
            if delta_margin > cfg.margin_tolerance:
                discrepancies.append(
                    MT5Discrepancy(
                        kind=MT5DiscrepancyKind.MARGIN_MISMATCH,
                        severity=MT5DiscrepancySeverity.CRITICAL,
                        dimension="margin",
                        identifier="margin",
                        expected_value=f"{shadow.margin} {shadow.currency}",
                        observed_value=f"{broker.account.margin} {broker.account.currency}",
                        delta=delta_margin,
                        detail=f"Margin discrepancy {delta_margin} exceeds tolerance {cfg.margin_tolerance}.",
                    )
                )
            else:
                dim_verification["margin"] = True

        # --- DIMENSION 4: POSITIONS ---
        margin_mode = broker.account.margin_mode
        if not isinstance(margin_mode, MT5AccountMarginMode):
            raise MT5DomainError(f"INVALID_MARGIN_MODE_TYPE: expected MT5AccountMarginMode, got {type(margin_mode)}")

        # Check for Phantom Positions (broker has position not in shadow)
        for b_pos in broker.positions:
            matched = False
            for s_pos in shadow.positions:
                if match_position_identity(s_pos, b_pos, margin_mode):
                    matched = True
                    # Check volume equality
                    if s_pos.volume != b_pos.volume:
                        discrepancies.append(
                            MT5Discrepancy(
                                kind=MT5DiscrepancyKind.POSITION_VOLUME_MISMATCH,
                                severity=MT5DiscrepancySeverity.CRITICAL,
                                dimension="positions",
                                identifier=str(b_pos.position_ticket),
                                expected_value=f"{s_pos.volume} lots",
                                observed_value=f"{b_pos.volume} lots",
                                delta=abs(b_pos.volume - s_pos.volume),
                                detail=f"Position volume mismatch on {b_pos.symbol}.",
                            )
                        )
                    # Check side
                    expected_side = s_pos.side.upper()
                    observed_side = b_pos.position_type.value.replace("POSITION_TYPE_", "")
                    if expected_side != observed_side:
                        discrepancies.append(
                            MT5Discrepancy(
                                kind=MT5DiscrepancyKind.POSITION_SIDE_MISMATCH,
                                severity=MT5DiscrepancySeverity.CRITICAL,
                                dimension="positions",
                                identifier=str(b_pos.position_ticket),
                                expected_value=expected_side,
                                observed_value=observed_side,
                                detail=f"Position direction mismatch on {b_pos.symbol}.",
                            )
                        )
                    break

            if not matched:
                discrepancies.append(
                    MT5Discrepancy(
                        kind=MT5DiscrepancyKind.PHANTOM_POSITION,
                        severity=MT5DiscrepancySeverity.CRITICAL,
                        dimension="positions",
                        identifier=str(b_pos.position_ticket),
                        expected_value="None",
                        observed_value=f"{b_pos.symbol} {b_pos.volume} lots",
                        detail=f"Untracked broker position ticket {b_pos.position_ticket} on {b_pos.symbol}.",
                    )
                )

        # Check for Missing Positions (shadow expects position not in broker)
        for s_pos in shadow.positions:
            matched = False
            for b_pos in broker.positions:
                if match_position_identity(s_pos, b_pos, margin_mode):
                    matched = True
                    break
            if not matched:
                discrepancies.append(
                    MT5Discrepancy(
                        kind=MT5DiscrepancyKind.MISSING_POSITION,
                        severity=MT5DiscrepancySeverity.CRITICAL,
                        dimension="positions",
                        identifier=str(s_pos.position_ticket),
                        expected_value=f"{s_pos.symbol} {s_pos.volume} lots",
                        observed_value="None",
                        detail=f"Tracked shadow position ticket {s_pos.position_ticket} missing from broker.",
                    )
                )

        if not any(d.dimension == "positions" for d in discrepancies):
            dim_verification["positions"] = True

        # --- DIMENSION 5: RESTING ORDERS ---
        broker_orders_by_ticket = {o.order_ticket: o for o in broker.orders}
        shadow_orders_by_ticket = {o.order_ticket: o for o in shadow.resting_orders}
        broker_history_orders_by_ticket = {o.order_ticket: o for o in broker.history_orders}

        # Check for Orphan Orders (broker has resting order not in shadow)
        for b_ord in broker.orders:
            if b_ord.order_ticket not in shadow_orders_by_ticket:
                discrepancies.append(
                    MT5Discrepancy(
                        kind=MT5DiscrepancyKind.ORPHAN_RESTING_ORDER,
                        severity=MT5DiscrepancySeverity.CRITICAL,
                        dimension="orders",
                        identifier=str(b_ord.order_ticket),
                        expected_value="None",
                        observed_value=f"{b_ord.symbol} {b_ord.volume_initial} lots",
                        detail=f"Untracked resting order ticket {b_ord.order_ticket} on broker.",
                    )
                )
            else:
                s_ord = shadow_orders_by_ticket[b_ord.order_ticket]
                if s_ord.volume != b_ord.volume_current:
                    discrepancies.append(
                        MT5Discrepancy(
                            kind=MT5DiscrepancyKind.ORDER_PARAMETER_MISMATCH,
                            severity=MT5DiscrepancySeverity.CRITICAL,
                            dimension="orders",
                            identifier=str(b_ord.order_ticket),
                            expected_value=f"volume={s_ord.volume}",
                            observed_value=f"volume={b_ord.volume_current}",
                            detail=f"Resting order volume mismatch on ticket {b_ord.order_ticket}.",
                        )
                    )

        # Check for Missing Orders and resolve transitions
        for s_ord in shadow.resting_orders:
            if s_ord.order_ticket not in broker_orders_by_ticket:
                # Order transitioned: check broker history orders
                if s_ord.order_ticket in broker_history_orders_by_ticket:
                    b_h_ord = broker_history_orders_by_ticket[s_ord.order_ticket]
                    matching_deals = [d for d in broker.deals if d.order_ticket == s_ord.order_ticket]
                    resolved_state, total_vol, vwap, broker_event_id, evidence_refs = verify_order_deal_execution(
                        order_ticket=s_ord.order_ticket,
                        historical_order=b_h_ord,
                        matching_deals=matching_deals,
                    )
                    if resolved_state == OrderLifecycleState.FILLED:
                        b_kind = BrokerEventKind.FILLED
                    elif resolved_state == OrderLifecycleState.CANCELLED:
                        b_kind = BrokerEventKind.ORDER_CANCELLED
                    elif resolved_state == OrderLifecycleState.REJECTED:
                        b_kind = BrokerEventKind.REJECT
                    elif resolved_state == OrderLifecycleState.EXPIRED:
                        b_kind = BrokerEventKind.EXPIRED
                    else:
                        raise MT5DomainError(f"UNSUPPORTED_ORDER_STATE: {resolved_state}")

                    _, evidence = normalize_broker_event(
                        broker_order_id=str(s_ord.order_ticket),
                        event_kind=b_kind,
                        observed_at=broker.observed_at,
                        source=f"mt5:{broker.broker_id}",
                        broker_sequence=broker_event_id,
                        cancel_was_requested=True,
                        evidence_refs=evidence_refs,
                    )
                    if evidence is not None:
                        resolved_orders.append(evidence)
                else:
                    discrepancies.append(
                        MT5Discrepancy(
                            kind=MT5DiscrepancyKind.MISSING_RESTING_ORDER,
                            severity=MT5DiscrepancySeverity.CRITICAL,
                            dimension="orders",
                            identifier=str(s_ord.order_ticket),
                            expected_value=f"{s_ord.symbol} {s_ord.volume} lots",
                            observed_value="None",
                            detail=f"Tracked resting order ticket {s_ord.order_ticket} missing from broker order book.",
                        )
                    )

        if not any(d.dimension == "orders" for d in discrepancies):
            dim_verification["orders"] = True

        # --- DIMENSION 6: HISTORICAL DEALS & RELATIONAL LINEAGE ---
        shadow_deals_by_ticket = {d.deal_ticket: d for d in shadow.deals}
        broker_positions_by_identifier = {p.position_identifier: p for p in broker.positions}

        for b_deal in broker.deals:
            deal_category = categorize_deal(b_deal.deal_type)
            if deal_category == MT5DealCategory.TRADE_EXECUTION_DEAL:
                # 1. Close-by fail closed check
                if b_deal.entry == MT5DealEntry.DEAL_ENTRY_OUT_BY:
                    raise MT5DomainError(
                        "CLOSE_BY_UNSUPPORTED: DEAL_ENTRY_OUT_BY is not authorized under current execution contract"
                    )

                # 2. Lineage Correlation Check (Zero comment bypass, ACASH-owned only)
                is_known_deal = b_deal.deal_ticket in shadow_deals_by_ticket
                is_tracked_resting = b_deal.order_ticket in shadow_orders_by_ticket
                is_coord_tracked = False
                if coordinator_map:
                    is_coord_tracked = any(
                        str(b_deal.order_ticket) == c.execution_id
                        or str(b_deal.order_ticket) == getattr(c, "order_id", None)
                        for c in coordinator_map.values()
                    )

                if not (is_known_deal or is_tracked_resting or is_coord_tracked):
                    discrepancies.append(
                        MT5Discrepancy(
                            kind=MT5DiscrepancyKind.UNTRACKED_TRADE_DEAL,
                            severity=MT5DiscrepancySeverity.CRITICAL,
                            dimension="deals",
                            identifier=str(b_deal.deal_ticket),
                            expected_value="ACASH Tracked Intent Lineage",
                            observed_value=f"deal_ticket={b_deal.deal_ticket}, order={b_deal.order_ticket}",
                            detail=f"Trade execution deal {b_deal.deal_ticket} without valid ACASH intent lineage.",
                        )
                    )
                else:
                    # 3. Relational Position Lifecycle Integrity
                    # DEAL_POSITION_ID represents the position lifecycle identifier
                    if b_deal.entry == MT5DealEntry.DEAL_ENTRY_IN:
                        # Opening or increasing a position: resulting broker position identifier must match
                        # or have been subsequently closed in historical deals
                        if b_deal.position_ticket not in broker_positions_by_identifier:
                            b_deal_time_msc = int(b_deal.deal_time_utc.timestamp() * 1000)
                            has_subsequent_close = False
                            for other in broker.deals:
                                other_time_msc = int(other.deal_time_utc.timestamp() * 1000)
                                is_subsequent = (
                                    other_time_msc > b_deal_time_msc
                                    or (other_time_msc == b_deal_time_msc and other.deal_ticket > b_deal.deal_ticket)
                                )
                                if (
                                    other.position_ticket == b_deal.position_ticket
                                    and is_subsequent
                                    and other.entry in (MT5DealEntry.DEAL_ENTRY_OUT, MT5DealEntry.DEAL_ENTRY_INOUT)
                                    and categorize_deal(other.deal_type) == MT5DealCategory.TRADE_EXECUTION_DEAL
                                ):
                                    has_subsequent_close = True
                                    break
                            if not has_subsequent_close:
                                discrepancies.append(
                                    MT5Discrepancy(
                                        kind=MT5DiscrepancyKind.PHANTOM_POSITION,
                                        severity=MT5DiscrepancySeverity.CRITICAL,
                                        dimension="positions",
                                        identifier=str(b_deal.position_ticket),
                                        expected_value="Known Resulting Position or Subsequent Close",
                                        observed_value=f"deal_position_id={b_deal.position_ticket}",
                                        detail=f"DEAL_ENTRY_IN for deal {b_deal.deal_ticket} lacks corresponding resulting position or subsequent close.",
                                    )
                                )

        if not any(d.dimension == "deals" for d in discrepancies):
            dim_verification["deals"] = True

        # --- EVALUATION & CONFIRMATION EMISSION ---
        critical_discrepancies = [d for d in discrepancies if d.severity == MT5DiscrepancySeverity.CRITICAL]
        all_6d_verified = all(dim_verification.values())

        if not critical_discrepancies and all_6d_verified:
            status = ReconciliationStatus.CLEAN
            confirmation = MT5ReconciliationConfirmation(
                reconciliation_id=reconciliation_id,
                broker_id=shadow.broker_id,
                account_id=shadow.account_id,
                verified_at=reconciled_at,
                orders_verified=True,
                deals_verified=True,
                positions_verified=True,
                account_verified=True,
                is_complete=True,
                discrepancies_count=0,
            )
        else:
            status = (
                ReconciliationStatus.DISCREPANCIES_DETECTED
                if critical_discrepancies
                else ReconciliationStatus.RECONCILIATION_FAILED
            )
            confirmation = None

        # Cryptographic SHA-256 evidence digests
        resolved_evidence_digests = tuple(
            e.evidence_digest for e in resolved_orders
        )
        report_digest_payload = {
            "reconciliation_id": reconciliation_id,
            "schema_version": "1.0.0",
            "broker_id": shadow.broker_id,
            "account_id": shadow.account_id,
            "terminal_instance_id": shadow.terminal_instance_id,
            "ledger_digest": shadow.ledger_digest,
            "broker_snapshot_digest": broker.broker_snapshot_digest,
            "historical_coverage_digest": broker.deal_coverage.coverage_digest,
            "capture_context_digest": compute_payload_digest(broker.capture_context),
            "resolved_evidence_digests": resolved_evidence_digests,
            "discrepancies": [d.model_dump() for d in discrepancies],
            "reconciled_at": reconciled_at,
        }
        report_digest = compute_payload_digest(report_digest_payload)

        failure_reason = critical_discrepancies[0].kind if critical_discrepancies else None

        return MT56DReconciliationReport(
            schema_version="1.0.0",
            reconciliation_id=reconciliation_id,
            broker_id=shadow.broker_id,
            account_id=shadow.account_id,
            terminal_instance_id=shadow.terminal_instance_id,
            reconciled_at=reconciled_at,
            status=status,
            tolerances=cfg,
            dimension_verification=dim_verification,
            failure_reason=failure_reason,
            discrepancies=tuple(discrepancies),
            confirmation=confirmation,
            resolved_orders=tuple(resolved_orders),
            ledger_digest=shadow.ledger_digest,
            broker_snapshot_digest=broker.broker_snapshot_digest,
            report_digest=report_digest,
        )

    def capture_bounded_broker_observation(
        self,
        transport: MT5TransportProtocol,
        broker_id: str,
        account_id: str,
        terminal_instance_id: str,
        scope: HistoricalDealScopeKind = HistoricalDealScopeKind.FULL_CYCLE,
        watermark_ticket: int = 0,
        watermark_time_msc: int = 0,
        date_from: Optional[datetime] = None,
        max_capture_window_ms: float = 2000.0,
        recapture_attempt: int = 0,
        prior_capture_context: Optional[ReconciliationCaptureContext] = None,
    ) -> MT5BrokerRealitySnapshot:
        """Capture coherent-enough bounded broker observation across 4-D queries.

        Enforces frozen capture cutoff and raw-query count oracle completeness.
        """
        start_time = datetime.now(timezone.utc)
        start_msc = int(start_time.timestamp() * 1000)
        query_latencies: Dict[str, float] = {}

        # 1. Account, Positions, Orders queries
        t0 = time.perf_counter()
        acc = transport.account_info()
        query_latencies["account_info"] = (time.perf_counter() - t0) * 1000
        if acc is None:
            raise MT5TransportError("account_info() returned None")

        t0 = time.perf_counter()
        positions = transport.positions_get()
        query_latencies["positions_get"] = (time.perf_counter() - t0) * 1000
        if positions is None:
            raise MT5TransportError("positions_get() returned None")

        t0 = time.perf_counter()
        orders = transport.orders_get()
        query_latencies["orders_get"] = (time.perf_counter() - t0) * 1000
        if orders is None:
            raise MT5TransportError("orders_get() returned None")

        # 2. Frozen observation cutoff timestamp for both count oracle and get queries
        capture_to = datetime.now(timezone.utc)
        completed_msc = int(capture_to.timestamp() * 1000)

        t0 = time.perf_counter()
        expected_orders_count = transport.history_orders_total(date_from=date_from, date_to=capture_to)
        query_latencies["history_orders_total"] = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        history_orders = transport.history_orders_get(date_from=date_from, date_to=capture_to)
        query_latencies["history_orders_get"] = (time.perf_counter() - t0) * 1000
        if history_orders is None:
            raise MT5TransportError("history_orders_get() returned None")
        if len(history_orders) != expected_orders_count:
            raise MT5ReconciliationError(
                f"INCOMPLETE_HISTORY_ORDERS_SCOPE: history_orders_total={expected_orders_count} "
                f"!= history_orders_get={len(history_orders)}"
            )

        # 3. Dual-Scope Historical Deal Queries with Count Oracle
        t0 = time.perf_counter()
        if scope == HistoricalDealScopeKind.FULL_CYCLE:
            query_from = date_from or datetime.fromtimestamp(0, tz=timezone.utc)
            expected_raw_count = transport.history_deals_total(date_from=query_from, date_to=capture_to)
            raw_deals = transport.history_deals_get(date_from=query_from, date_to=capture_to)

            if (
                raw_deals is not None
                and len(raw_deals) == expected_raw_count
                and all(query_from <= d.deal_time_utc <= capture_to for d in raw_deals)
            ):
                is_complete = True
                deals = raw_deals
            else:
                is_complete = False
                deals = raw_deals if raw_deals is not None else ()
        elif scope == HistoricalDealScopeKind.WATERMARK_INCREMENTAL:
            coarse_sec = max(0.0, math.floor(watermark_time_msc / 1000.0) - 1.0)
            query_from = datetime.fromtimestamp(coarse_sec, tz=timezone.utc)
            expected_raw_count = transport.history_deals_total(date_from=query_from, date_to=capture_to)
            raw_deals = transport.history_deals_get(date_from=query_from, date_to=capture_to)

            if raw_deals is None or len(raw_deals) != expected_raw_count:
                is_complete = False
                deals = ()
            else:
                # Apply exact 2-tuple millisecond + ticket post-filter on proven complete raw set
                filtered_deals = [
                    d
                    for d in raw_deals
                    if (int(d.deal_time_utc.timestamp() * 1000) > watermark_time_msc)
                    or (
                        int(d.deal_time_utc.timestamp() * 1000) == watermark_time_msc
                        and d.deal_ticket > watermark_ticket
                    )
                ]
                deals = tuple(filtered_deals)
                is_complete = True
        else:
            query_from = date_from or start_time
            raw_deals = transport.history_deals_get(date_from=query_from, date_to=capture_to)
            deals = raw_deals if raw_deals is not None else ()
            is_complete = raw_deals is not None

        query_latencies["history_deals_get"] = (time.perf_counter() - t0) * 1000
        completed_time = datetime.now(timezone.utc)
        duration_ms = (completed_time - start_time).total_seconds() * 1000

        post_watermark_ticket = max((d.deal_ticket for d in deals), default=watermark_ticket)

        # 4. Straddle / Boundary Activity Check
        resting_order_tickets = {o.order_ticket for o in orders}
        boundary_activity_detected = False
        for d in deals:
            d_time_msc = int(d.deal_time_utc.timestamp() * 1000)
            if (
                d.order_ticket in resting_order_tickets
                and start_msc <= d_time_msc <= completed_msc
                and watermark_ticket < d.deal_ticket <= post_watermark_ticket
            ):
                boundary_activity_detected = True
                break

        if boundary_activity_detected:
            completeness_status = CaptureCompletenessStatus.BOUNDARY_ACTIVITY_DETECTED
        elif duration_ms > max_capture_window_ms:
            completeness_status = CaptureCompletenessStatus.CAPTURE_TIMEOUT
        elif not is_complete:
            completeness_status = CaptureCompletenessStatus.PARTIAL_QUERY_FAILED
        else:
            completeness_status = CaptureCompletenessStatus.COMPLETE

        capture_ctx = ReconciliationCaptureContext(
            reconciliation_id=f"CAP_{int(start_msc)}",
            capture_started_at=start_time,
            capture_completed_at=completed_time,
            capture_started_at_msc=start_msc,
            capture_completed_at_msc=completed_msc,
            pre_watermark_deal_ticket=watermark_ticket,
            post_watermark_deal_ticket=post_watermark_ticket,
            query_latencies_ms=query_latencies,
            capture_duration_ms=duration_ms,
            max_capture_window_ms=max_capture_window_ms,
            completeness_status=completeness_status,
            boundary_activity_detected=boundary_activity_detected,
            recapture_attempt=recapture_attempt,
            prior_capture_context=prior_capture_context,
        )

        coverage_digest = compute_payload_digest(
            {
                "scope_kind": scope.value,
                "from_timestamp": query_from,
                "to_timestamp": capture_to,
                "watermark_time_msc": watermark_time_msc,
                "watermark_ticket": watermark_ticket,
                "last_deal_ticket": post_watermark_ticket,
                "deal_tickets": sorted(d.deal_ticket for d in deals),
                "total_deals": len(deals),
                "is_complete": is_complete,
            }
        )

        coverage = HistoricalDealCoverage(
            scope_kind=scope,
            from_timestamp=query_from,
            to_timestamp=capture_to,
            watermark_ticket=watermark_ticket,
            watermark_time_msc=watermark_time_msc,
            last_deal_ticket=post_watermark_ticket,
            total_deals_retrieved=len(deals),
            is_complete=is_complete,
            coverage_digest=coverage_digest,
        )

        broker_payload = {
            "schema_version": "1.0.0",
            "broker_id": broker_id,
            "account_id": account_id,
            "terminal_instance_id": terminal_instance_id,
            "observed_at": completed_time,
            "account": acc,
            "positions": positions,
            "orders": orders,
            "history_orders": history_orders,
            "deals": deals,
            "deal_coverage": coverage,
            "capture_context": capture_ctx,
        }
        digest = compute_payload_digest(broker_payload)

        return MT5BrokerRealitySnapshot(
            schema_version="1.0.0",
            broker_id=broker_id,
            account_id=account_id,
            terminal_instance_id=terminal_instance_id,
            observed_at=completed_time,
            account=acc,
            positions=positions,
            orders=orders,
            history_orders=history_orders,
            deals=deals,
            deal_coverage=coverage,
            capture_context=capture_ctx,
            broker_snapshot_digest=digest,
        )

    def execute_reconciliation_cycle(
        self,
        adapter: MT5BrokerAdapter,
        shadow_ledger: ACASHShadowLedger,
        coordinator_map: Mapping[str, ExecutionCoordinator],
        tolerances: Optional[ReconciliationToleranceConfig] = None,
        watermark_ticket: int = 0,
        watermark_time_msc: int = 0,
        date_from: Optional[datetime] = None,
    ) -> MT56DReconciliationReport:
        """Execute end-to-end reconciliation cycle with real 2-pass recapture."""
        cfg = tolerances or self.tolerances
        shadow = shadow_ledger.snapshot_reconciliation_state()

        # Pass 1: Initial observation
        broker = self.capture_bounded_broker_observation(
            transport=adapter.transport,
            broker_id=adapter.broker_id,
            account_id=adapter.account_id,
            terminal_instance_id=adapter.terminal_instance_id,
            watermark_ticket=watermark_ticket,
            watermark_time_msc=watermark_time_msc,
            date_from=date_from,
            max_capture_window_ms=cfg.max_capture_window_ms,
            recapture_attempt=0,
        )

        # Pass 2: Synchronized re-capture if boundary activity detected
        if broker.capture_context.boundary_activity_detected:
            broker = self.capture_bounded_broker_observation(
                transport=adapter.transport,
                broker_id=adapter.broker_id,
                account_id=adapter.account_id,
                terminal_instance_id=adapter.terminal_instance_id,
                watermark_ticket=broker.capture_context.post_watermark_deal_ticket,
                watermark_time_msc=broker.capture_context.capture_completed_at_msc,
                date_from=date_from,
                max_capture_window_ms=cfg.max_capture_window_ms,
                recapture_attempt=1,
                prior_capture_context=broker.capture_context,
            )

        report = self.reconcile_6d(shadow, broker, cfg, coordinator_map=coordinator_map)

        if report.is_clean and report.confirmation is not None:
            # Deliver evidence to coordinators via public seam
            ticket_to_intent = {str(o.order_ticket): o.intent_id for o in shadow.resting_orders}
            for evidence in report.resolved_orders:
                target_intent = ticket_to_intent.get(evidence.broker_order_id)
                for execution_id, coordinator in coordinator_map.items():
                    if (
                        coordinator.execution_id in (evidence.broker_order_id, target_intent)
                        or getattr(coordinator, "order_id", None) in (evidence.broker_order_id, target_intent)
                        or execution_id in (evidence.broker_order_id, target_intent)
                    ):
                        coordinator.apply_reconciliation(
                            broker_event_id=evidence.broker_sequence,
                            broker_sequence=evidence.broker_sequence,
                            evidence_token=evidence.to_evidence_string(),
                            order_id=evidence.broker_order_id,
                            observed_at=evidence.observed_at,
                            evidence_refs=(*evidence.evidence_refs, report.report_digest),
                        )
            # Unlock adapter
            adapter.confirm_reconciliation(report.confirmation)
        else:
            if report.discrepancies:
                raise MT5ReconciliationError(
                    f"RECONCILIATION_CRITICAL_DISCREPANCY: {report.discrepancies[0].kind.value} on {report.discrepancies[0].identifier}"
                )

        return report
