"""Canonical domain schemas, DTOs, and lineage models for MetaTrader 5 execution."""

from datetime import datetime
from decimal import Decimal
import hashlib
import re
from typing import Any, Dict, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from acash.core.domain.exceptions import DomainValidationError
from acash.core.domain.types import ensure_finite_decimal
from acash.core.serialization import CanonicalConfigSerializer
from acash.execution.mt5.enums import (
    MT5AccountMarginMode,
    MT5DealEntry,
    MT5DealType,
    MT5ExecutionPolicy,
    MT5FillingMode,
    MT5OrderState,
    MT5OrderTime,
    MT5OrderType,
    MT5PositionType,
    MT5TradeAction,
    MT5TradeExecutionMode,
)
from acash.execution.mt5.exceptions import MT5SymbolSpecError, MT5ValidationError

SHA256_HEX_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def _validate_sha256(v: str, field_name: str) -> str:
    if not isinstance(v, str) or not SHA256_HEX_PATTERN.match(v):
        raise MT5ValidationError(
            f"{field_name} must be a valid 64-character lowercase hex SHA-256 string, got: {v!r}"
        )
    return v


class BrokerSymbolSpec(BaseModel):
    """Immutable, versioned specification of broker-side instrument mechanics."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    canonical_symbol: str = Field(min_length=1, description="ACASH canonical symbol (e.g. 'EURUSD').")
    broker_symbol: str = Field(min_length=1, description="Broker vendor symbol (e.g. 'EURUSD.pro').")
    contract_size: Decimal = Field(description="Contract size (e.g. 100,000 for standard FX lot).")
    volume_min: Decimal = Field(description="Minimum order lot size.")
    volume_max: Decimal = Field(description="Maximum order lot size.")
    volume_step: Decimal = Field(description="Lot size step / increment.")
    digits: int = Field(ge=0, description="Price decimal places.")
    point_size: Decimal = Field(description="Point size (e.g. 0.00001).")
    tick_size: Decimal = Field(description="Minimum price movement (e.g. 0.00001).")
    trade_execution_mode: MT5TradeExecutionMode = Field(description="Broker execution mode.")
    allowed_filling_flags: Tuple[str, ...] = Field(
        default=(), description="Tuple of allowed filling mode flags (e.g. 'SYMBOL_FILLING_FOK')."
    )
    allowed_order_modes: Tuple[str, ...] = Field(
        default=(), description="Tuple of allowed order mode flags (e.g. 'SYMBOL_ORDER_LIMIT')."
    )
    stops_level_points: int = Field(default=0, ge=0, description="Minimum distance for SL/TP in points.")
    margin_currency: str = Field(min_length=1, description="Margin currency (e.g. 'EUR').")
    profit_currency: str = Field(min_length=1, description="Profit currency (e.g. 'USD').")
    spec_digest: str = Field(description="Canonical SHA-256 digest of symbol specification.")

    @field_validator("contract_size", "volume_min", "volume_max", "volume_step", "point_size", "tick_size")
    @classmethod
    def validate_positive_decimals(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        field_name = info.field_name or "field"
        ensure_finite_decimal(v, field_name=field_name)
        if v <= Decimal("0"):
            raise MT5SymbolSpecError(f"{field_name} must be strictly positive (> 0), got: {v}")
        return v

    @field_validator("volume_max")
    @classmethod
    def validate_volume_bounds(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        data = info.data
        if "volume_min" in data and v < data["volume_min"]:
            raise MT5SymbolSpecError(
                f"volume_max ({v}) cannot be less than volume_min ({data['volume_min']})"
            )
        return v

    @field_validator("spec_digest")
    @classmethod
    def validate_digest(cls, v: str, info: ValidationInfo) -> str:
        return _validate_sha256(v, info.field_name or "spec_digest")

    @classmethod
    def compute_spec_digest(
        cls,
        canonical_symbol: str,
        broker_symbol: str,
        contract_size: Decimal,
        volume_min: Decimal,
        volume_max: Decimal,
        volume_step: Decimal,
        digits: int,
        point_size: Decimal,
        tick_size: Decimal,
        trade_execution_mode: MT5TradeExecutionMode,
        allowed_filling_flags: Tuple[str, ...],
        allowed_order_modes: Tuple[str, ...],
        stops_level_points: int,
        margin_currency: str,
        profit_currency: str,
    ) -> str:
        """Compute the canonical SHA-256 spec_digest for a symbol specification."""
        canonical_payload: Dict[str, Any] = {
            "canonical_symbol": canonical_symbol.strip(),
            "broker_symbol": broker_symbol.strip(),
            "contract_size": str(contract_size),
            "volume_min": str(volume_min),
            "volume_max": str(volume_max),
            "volume_step": str(volume_step),
            "digits": digits,
            "point_size": str(point_size),
            "tick_size": str(tick_size),
            "trade_execution_mode": trade_execution_mode.value,
            "allowed_filling_flags": sorted(allowed_filling_flags),
            "allowed_order_modes": sorted(allowed_order_modes),
            "stops_level_points": stops_level_points,
            "margin_currency": margin_currency.strip(),
            "profit_currency": profit_currency.strip(),
        }
        return hashlib.sha256(
            CanonicalConfigSerializer.to_canonical_json(canonical_payload).encode("utf-8")
        ).hexdigest()


class MT5TradeRequest(BaseModel):
    """Canonical MqlTradeRequest data transfer object for MT5 trade operations."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    action: MT5TradeAction = Field(description="Trade operation action type.")
    magic: int = Field(default=0, ge=0, description="Expert Advisor / Strategy identifier (ulong semantic).")
    order: Optional[int] = Field(default=None, gt=0, description="Order ticket for modify/cancel (ulong semantic).")
    symbol: str = Field(min_length=1, description="Trade symbol name.")
    volume: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), description="Requested volume in lots.")
    price: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), description="Order execution price.")
    stoplimit: Optional[Decimal] = Field(default=None, gt=Decimal("0.0"), description="StopLimit price level.")
    sl: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), description="Stop Loss price level.")
    tp: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), description="Take Profit price level.")
    deviation: int = Field(default=0, ge=0, description="Maximal price deviation in points (ulong semantic).")
    type: MT5OrderType = Field(description="Order type.")
    type_filling: MT5FillingMode = Field(description="Order filling mode.")
    type_time: MT5OrderTime = Field(default=MT5OrderTime.ORDER_TIME_GTC, description="Order expiration type.")
    expiration: Optional[datetime] = Field(default=None, description="Expiration time in UTC.")
    comment: str = Field(default="", max_length=31, description="Order comment (max 31 chars per MQL5 spec).")
    position: Optional[int] = Field(default=None, gt=0, description="Position ticket for modify/close (ulong semantic).")
    position_by: Optional[int] = Field(default=None, gt=0, description="Opposite position ticket for Close-By (ulong semantic).")

    @field_validator("volume", "price", "sl", "tp")
    @classmethod
    def validate_finite_decimals(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        field_name = info.field_name or "field"
        ensure_finite_decimal(v, field_name=field_name)
        return v

    @field_validator("stoplimit")
    @classmethod
    def validate_optional_stoplimit(cls, v: Optional[Decimal], info: ValidationInfo) -> Optional[Decimal]:
        if v is not None:
            ensure_finite_decimal(v, field_name=info.field_name or "stoplimit")
        return v

    @model_validator(mode="after")
    def validate_action_specific_requirements(self) -> "MT5TradeRequest":
        if self.action in (MT5TradeAction.TRADE_ACTION_DEAL, MT5TradeAction.TRADE_ACTION_PENDING):
            if self.volume <= Decimal("0.0"):
                raise MT5ValidationError(
                    f"volume must be strictly positive (> 0) for action {self.action.value}, got: {self.volume}"
                )
        elif self.action == MT5TradeAction.TRADE_ACTION_REMOVE:
            if self.order is None or self.order <= 0:
                raise MT5ValidationError("order ticket must be specified (> 0) for TRADE_ACTION_REMOVE")
        return self



class MT5TradeResult(BaseModel):
    """Canonical MqlTradeResult data transfer object capturing IPC transport observations."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    retcode: int = Field(description="MQL5 trade server return code.")
    deal: int = Field(default=0, ge=0, description="Deal ticket if executed (ulong semantic).")
    order: int = Field(default=0, ge=0, description="Order ticket if placed (ulong semantic).")
    volume: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), description="Deal volume confirmed by broker.")
    price: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), description="Deal price confirmed by broker.")
    bid: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), description="Current market Bid price.")
    ask: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), description="Current market Ask price.")
    comment: str = Field(default="", max_length=128, description="Trade server comment.")
    request_id: int = Field(default=0, ge=0, description="Terminal request ID (uint semantic).")
    retcode_external: int = Field(default=0, description="External gateway return code.")

    @field_validator("volume", "price", "bid", "ask")
    @classmethod
    def validate_finite_decimals(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        field_name = info.field_name or "field"
        ensure_finite_decimal(v, field_name=field_name)
        return v


class MT5DealReality(BaseModel):
    """Authoritative fill observation corresponding to an MT5 deal ticket."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    deal_ticket: int = Field(gt=0, description="Unique MT5 deal ticket.")
    order_ticket: int = Field(gt=0, description="Linked MT5 order ticket.")
    position_ticket: int = Field(
        ge=0,
        description=(
            "Linked MT5 position ticket (corresponds to MQL5 DEAL_POSITION_ID, which is the lifecycle "
            "identifier of the position this deal affected; distinct from individual ticket numbers in hedging mode)."
        ),
    )
    symbol: str = Field(min_length=1, description="Symbol name.")
    deal_type: MT5DealType = Field(description="Deal operation type.")
    volume: Decimal = Field(gt=Decimal("0.0"), description="Executed volume.")
    price: Decimal = Field(gt=Decimal("0.0"), description="Executed price.")
    commission: Decimal = Field(default=Decimal("0.0"), description="Broker commission.")
    fee: Decimal = Field(default=Decimal("0.0"), description="Exchange/gateway fee.")
    swap: Decimal = Field(default=Decimal("0.0"), description="Cumulative swap.")
    profit: Decimal = Field(default=Decimal("0.0"), description="Realized deal profit.")
    deal_time_utc: datetime = Field(description="UTC execution timestamp.")
    comment: str = Field(default="", description="Deal comment.")
    magic: int = Field(default=0, ge=0, description="Expert Advisor / Strategy ID.")
    entry: Optional[MT5DealEntry] = Field(default=None, description="MQL5 deal entry mode (DEAL_ENTRY).")

    @field_validator("volume", "price", "commission", "fee", "swap", "profit")
    @classmethod
    def validate_finite_decimals(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        field_name = info.field_name or "field"
        ensure_finite_decimal(v, field_name=field_name)
        return v


class MT5OrderReality(BaseModel):
    """Authoritative resting/historical order observation from MT5."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    order_ticket: int = Field(gt=0, description="Unique MT5 order ticket.")
    position_ticket: Optional[int] = Field(default=None, ge=0, description="Linked MT5 position ticket.")
    symbol: str = Field(min_length=1, description="Symbol name.")
    order_type: MT5OrderType = Field(description="Order type.")
    state: MT5OrderState = Field(description="Order state.")
    volume_initial: Decimal = Field(gt=Decimal("0.0"), description="Initial requested volume.")
    volume_current: Decimal = Field(ge=Decimal("0.0"), description="Remaining unexecuted volume.")
    price_open: Decimal = Field(ge=Decimal("0.0"), description="Specified open price.")
    price_stoplimit: Optional[Decimal] = Field(default=None, gt=Decimal("0.0"), description="StopLimit price level.")
    sl: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), description="Stop Loss level.")
    tp: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), description="Take Profit level.")
    time_setup_utc: datetime = Field(description="Order setup time in UTC.")
    time_done_utc: Optional[datetime] = Field(default=None, description="Order completion/cancellation time in UTC.")
    magic: int = Field(default=0, ge=0, description="Expert Advisor / Strategy ID.")
    comment: str = Field(default="", description="Order comment.")

    @field_validator("volume_initial", "volume_current", "price_open", "sl", "tp")
    @classmethod
    def validate_finite_decimals(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        field_name = info.field_name or "field"
        ensure_finite_decimal(v, field_name=field_name)
        return v

    @field_validator("price_stoplimit")
    @classmethod
    def validate_optional_stoplimit(cls, v: Optional[Decimal], info: ValidationInfo) -> Optional[Decimal]:
        if v is not None:
            ensure_finite_decimal(v, field_name=info.field_name or "price_stoplimit")
        return v


class MT5PositionReality(BaseModel):
    """Authoritative broker-side position snapshot from MT5."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    position_ticket: int = Field(gt=0, description="Unique MT5 position ticket.")
    position_identifier: int = Field(gt=0, description="Immutable originating position identifier (POSITION_IDENTIFIER).")
    symbol: str = Field(min_length=1, description="Position symbol.")
    position_type: MT5PositionType = Field(description="Position direction (BUY or SELL).")
    volume: Decimal = Field(gt=Decimal("0.0"), description="Position volume in lots.")
    price_open: Decimal = Field(gt=Decimal("0.0"), description="Weighted average open price.")
    price_current: Decimal = Field(gt=Decimal("0.0"), description="Current market price.")
    sl: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), description="Stop Loss level.")
    tp: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), description="Take Profit level.")
    swap: Decimal = Field(default=Decimal("0.0"), description="Cumulative position swap.")
    profit: Decimal = Field(default=Decimal("0.0"), description="Unrealized floating profit.")
    magic: int = Field(default=0, ge=0, description="Expert Advisor / Strategy ID.")
    comment: str = Field(default="", description="Position comment.")
    time_open_utc: datetime = Field(description="Position open time in UTC.")

    @field_validator("volume", "price_open", "price_current", "sl", "tp", "swap", "profit")
    @classmethod
    def validate_finite_decimals(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        field_name = info.field_name or "field"
        ensure_finite_decimal(v, field_name=field_name)
        return v


class MT5AccountReality(BaseModel):
    """Authoritative account balance, margin, and equity snapshot from MT5."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    login: int = Field(gt=0, description="Account login number.")
    trade_mode: int = Field(ge=0, description="Account trade mode (0=Demo, 1=Contest, 2=Real).")
    margin_mode: MT5AccountMarginMode = Field(description="Account margin calculation mode (strictly required, no silent fallback).")
    leverage: int = Field(gt=0, description="Account leverage ratio (e.g. 100 for 1:100).")
    limit_orders: int = Field(ge=0, description="Maximum allowed active pending orders.")
    margin_so_mode: int = Field(ge=0, description="Margin stop-out mode.")
    trade_allowed: bool = Field(description="Whether trading is allowed for the account.")
    trade_expert: bool = Field(description="Whether automated EA trading is enabled.")
    balance: Decimal = Field(description="Account balance.")
    credit: Decimal = Field(default=Decimal("0.0"), description="Account credit.")
    profit: Decimal = Field(default=Decimal("0.0"), description="Floating profit across positions.")
    equity: Decimal = Field(description="Account equity (balance + credit + profit).")
    margin: Decimal = Field(ge=Decimal("0.0"), description="Locked margin.")
    margin_free: Decimal = Field(description="Free margin available for trading.")
    margin_level: Decimal = Field(ge=Decimal("0.0"), description="Margin level percentage.")
    margin_so_call: Decimal = Field(ge=Decimal("0.0"), description="Margin call level.")
    margin_so_so: Decimal = Field(ge=Decimal("0.0"), description="Margin stop-out level.")
    margin_initial: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), description="Initial margin requirement.")
    margin_maintenance: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), description="Maintenance margin requirement.")
    currency: str = Field(min_length=1, description="Account deposit currency (e.g. 'USD').")

    @field_validator(
        "balance", "credit", "profit", "equity", "margin", "margin_free",
        "margin_level", "margin_so_call", "margin_so_so", "margin_initial", "margin_maintenance"
    )
    @classmethod
    def validate_finite_decimals(cls, v: Decimal, info: ValidationInfo) -> Decimal:
        field_name = info.field_name or "field"
        ensure_finite_decimal(v, field_name=field_name)
        return v


class MT5ExecutionLineage(BaseModel):
    """Immutable 9-tuple container guaranteeing multi-entity execution lineage."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    broker_id: str = Field(min_length=1, description="Broker identifier (e.g. 'IC_MARKETS').")
    account_id: str = Field(min_length=1, description="Account identifier (e.g. 'MT5_DEMO_12345').")
    terminal_instance_id: str = Field(min_length=1, description="Local MT5 terminal instance identifier.")
    strategy_id: str = Field(min_length=1, description="ACASH originating strategy identifier.")
    cycle_id: str = Field(min_length=1, description="RuntimeSupervisor cycle identifier.")
    intent_id: str = Field(min_length=1, description="OrderIntent identifier.")
    mt5_order_ticket: Optional[int] = Field(default=None, gt=0, description="MT5 order ticket (> 0).")
    mt5_deal_ticket: Optional[Union[int, Tuple[int, ...]]] = Field(
        default=None, description="Single MT5 deal ticket or tuple of deal tickets for multi-fill."
    )
    position_id: Optional[int] = Field(default=None, gt=0, description="MT5 position ticket.")

    @field_validator("broker_id", "account_id", "terminal_instance_id", "strategy_id", "cycle_id", "intent_id")
    @classmethod
    def validate_non_empty_strings(cls, v: str, info: ValidationInfo) -> str:
        field_name = info.field_name or "field"
        if not v or not v.strip():
            raise MT5ValidationError(f"{field_name} must be a non-empty string.")
        return v.strip()

    @field_validator("mt5_deal_ticket")
    @classmethod
    def validate_deal_tickets(cls, v: Optional[Union[int, Tuple[int, ...]]]) -> Optional[Union[int, Tuple[int, ...]]]:
        if v is None:
            return None
        if isinstance(v, int):
            if v <= 0:
                raise MT5ValidationError(f"mt5_deal_ticket integer must be strictly positive (> 0), got: {v}")
            return v
        if isinstance(v, (tuple, list)):
            if not v:
                raise MT5ValidationError("mt5_deal_ticket tuple cannot be empty.")
            for t in v:
                if not isinstance(t, int) or t <= 0:
                    raise MT5ValidationError(f"All deal tickets in tuple must be positive integers, got: {t}")
            return tuple(v)
        raise MT5ValidationError(f"mt5_deal_ticket must be an int or tuple of ints, got: {type(v)}")
