"""Phase 12 Slice 3: MetaTrader 5 Transport Layer and DTO Envelopes."""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import importlib
from typing import Any, Dict, List, Optional, Protocol, Tuple

from pydantic import BaseModel, ConfigDict, Field

from acash.execution.mt5.enums import (
    MT5AccountMarginMode,
    MT5DealEntry,
    MT5DealType,
    MT5FillingMode,
    MT5OrderState,
    MT5OrderTime,
    MT5OrderType,
    MT5PositionType,
    MT5Retcode,
    MT5TradeAction,
    MT5TradeExecutionMode,
    MT5ApiErrorCode,
)
from acash.execution.mt5.exceptions import (
    MT5DomainError,
    MT5RetcodeError,
    MT5SymbolSpecError,
    MT5TransportError,
    MT5ValidationError,
)
from acash.execution.mt5.mapping import (
    decode_mt5_deal_entry,
    decode_mt5_deal_type,
    decode_mt5_margin_mode,
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


class TransportFailureCause(str, Enum):
    """Categorized technical cause for transport failure or degradation."""

    TERMINAL_IPC_UNAVAILABLE = "TERMINAL_IPC_UNAVAILABLE"
    TERMINAL_UNHEALTHY = "TERMINAL_UNHEALTHY"
    TRADE_SERVER_DISCONNECTED = "TRADE_SERVER_DISCONNECTED"  # Retcode 10031
    TRADING_PERMISSION_DISABLED = "TRADING_PERMISSION_DISABLED"  # trade_allowed / trade_expert False
    ORDER_SEND_TIMEOUT_UNCERTAIN = "ORDER_SEND_TIMEOUT_UNCERTAIN"
    CLIENT_API_ERROR = "CLIENT_API_ERROR"


class MT5TransportSafetyState(str, Enum):
    """Transport dispatch safety state machine."""

    READY = "READY"
    DEGRADED = "DEGRADED"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    BLOCKED = "BLOCKED"


class MT5HealthReport(BaseModel):
    """Authoritative health assessment distinguishing transport connectivity from trading permissions and policy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    is_connected: bool
    is_healthy: bool
    is_trade_allowed: bool
    safety_state: MT5TransportSafetyState
    failure_cause: Optional[TransportFailureCause] = None
    detail: str = ""


class MT5TransportCommand(BaseModel):
    """Outbound transport envelope carrying canonical trade request and deterministic lineage correlation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request: MT5TradeRequest
    lineage: MT5ExecutionLineage


class MT5TransportObservation(BaseModel):
    """Inbound transport envelope pairing the observation result with its originating command lineage."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    result: MT5TradeResult
    lineage: MT5ExecutionLineage
    observed_at: datetime


class MT5ReconciliationConfirmation(BaseModel):
    """Typed, authoritative evidence required to confirm reconciliation and unblock dispatch."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reconciliation_id: str = Field(min_length=1)
    broker_id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)
    verified_at: datetime
    orders_verified: bool
    deals_verified: bool
    positions_verified: bool
    account_verified: bool
    is_complete: bool
    discrepancies_count: int = 0


class MT5TransportProtocol(Protocol):
    """Technical contract for MT5 IPC transport operations."""

    def initialize(
        self,
        path: Optional[str] = None,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        timeout_ms: int = 60000,
    ) -> bool: ...

    def shutdown(self) -> None: ...

    def is_connected(self) -> bool: ...

    def terminal_info(self) -> Optional[Dict[str, Any]]: ...

    def account_info(self) -> Optional[MT5AccountReality]: ...

    def symbol_info(self, symbol: str) -> Optional[BrokerSymbolSpec]: ...

    def order_send(self, command: MT5TransportCommand) -> MT5TransportObservation: ...

    def orders_get(
        self,
        symbol: Optional[str] = None,
        ticket: Optional[int] = None,
    ) -> Tuple[MT5OrderReality, ...]: ...

    def history_orders_get(
        self,
        ticket: Optional[int] = None,
        position: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[MT5OrderReality, ...]: ...

    def history_orders_total(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> int: ...

    def positions_get(
        self,
        symbol: Optional[str] = None,
        ticket: Optional[int] = None,
    ) -> Tuple[MT5PositionReality, ...]: ...

    def history_deals_get(
        self,
        ticket: Optional[int] = None,
        position: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[MT5DealReality, ...]: ...

    def history_deals_total(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> int: ...


class MockMT5Transport:
    """Deterministic, high-fidelity in-memory simulator for MT5 IPC transport."""

    def __init__(
        self,
        broker_id: str = "MOCK_BROKER",
        account_id: str = "MOCK_ACCOUNT",
    ) -> None:
        self.broker_id = broker_id
        self.account_id = account_id
        self._connected: bool = True
        self._terminal_healthy: bool = True
        self._trade_allowed: bool = True
        self._trade_expert: bool = True
        self._timeout_on_order_send: bool = False
        self._injected_retcode: Optional[int] = None
        self._next_ticket: int = 100000

        # In-memory storage for 4-dimensional reconciliation
        self.active_orders: Dict[int, MT5OrderReality] = {}
        self.history_orders: Dict[int, MT5OrderReality] = {}
        self.active_positions: Dict[int, MT5PositionReality] = {}
        self.history_deals: Dict[int, MT5DealReality] = {}
        self.symbol_specs: Dict[str, BrokerSymbolSpec] = {}

    def set_connected(self, connected: bool) -> None:
        self._connected = connected

    def set_terminal_healthy(self, healthy: bool) -> None:
        self._terminal_healthy = healthy

    def set_trading_permissions(self, trade_allowed: bool, trade_expert: bool) -> None:
        self._trade_allowed = trade_allowed
        self._trade_expert = trade_expert

    def set_timeout_on_order_send(self, timeout: bool) -> None:
        self._timeout_on_order_send = timeout

    def set_injected_retcode(self, retcode: Optional[int]) -> None:
        self._injected_retcode = retcode

    def register_symbol_spec(self, spec: BrokerSymbolSpec) -> None:
        self.symbol_specs[spec.broker_symbol] = spec

    def initialize(
        self,
        path: Optional[str] = None,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        timeout_ms: int = 60000,
    ) -> bool:
        return self._connected

    def shutdown(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def terminal_info(self) -> Optional[Dict[str, Any]]:
        if not self._terminal_healthy:
            return None
        return {
            "connected": self._connected,
            "trade_allowed": self._trade_allowed,
            "trade_expert": self._trade_expert,
            "community_account": False,
            "community_connection": False,
        }

    def account_info(self) -> Optional[MT5AccountReality]:
        if not self._terminal_healthy:
            return None
        return MT5AccountReality(
            login=123456,
            trade_mode=0,
            margin_mode=MT5AccountMarginMode.ACCOUNT_MARGIN_MODE_RETAIL_NETTING,
            leverage=100,
            limit_orders=200,
            margin_so_mode=0,
            trade_allowed=self._trade_allowed,
            trade_expert=self._trade_expert,
            balance=Decimal("100000.00"),
            credit=Decimal("0.00"),
            profit=Decimal("0.00"),
            equity=Decimal("100000.00"),
            margin=Decimal("0.00"),
            margin_free=Decimal("100000.00"),
            margin_level=Decimal("0.00"),
            margin_so_call=Decimal("50.00"),
            margin_so_so=Decimal("30.00"),
            margin_initial=Decimal("0.00"),
            margin_maintenance=Decimal("0.00"),
            currency="USD",
        )

    def symbol_info(self, symbol: str) -> Optional[BrokerSymbolSpec]:
        return self.symbol_specs.get(symbol)

    def order_send(self, command: MT5TransportCommand) -> MT5TransportObservation:
        now = datetime.now(timezone.utc)
        if self._timeout_on_order_send:
            raise TimeoutError("Simulated MT5 IPC order_send timeout")

        if not self._connected:
            result = MT5TradeResult(
                retcode=MT5Retcode.TRADE_RETCODE_CONNECTION.value,
                comment="No connection to trade server",
            )
            return MT5TransportObservation(
                result=result,
                lineage=command.lineage,
                observed_at=now,
            )

        if self._injected_retcode is not None:
            result = MT5TradeResult(
                retcode=self._injected_retcode,
                comment=f"Injected retcode {self._injected_retcode}",
            )
            return MT5TransportObservation(
                result=result,
                lineage=command.lineage,
                observed_at=now,
            )

        req = command.request
        self._next_ticket += 1
        ticket = self._next_ticket

        if req.action == MT5TradeAction.TRADE_ACTION_DEAL:
            deal_ticket = ticket + 500000
            deal = MT5DealReality(
                deal_ticket=deal_ticket,
                order_ticket=ticket,
                position_ticket=ticket,
                symbol=req.symbol,
                deal_type=MT5DealType.DEAL_TYPE_BUY if req.type == MT5OrderType.BUY else MT5DealType.DEAL_TYPE_SELL,
                volume=req.volume,
                price=Decimal("1.08500") if req.price == Decimal("0.0") else req.price,
                commission=Decimal("0.00"),
                fee=Decimal("0.00"),
                swap=Decimal("0.00"),
                profit=Decimal("0.00"),
                deal_time_utc=now,
                comment=req.comment,
                magic=req.magic,
            )
            self.history_deals[deal_ticket] = deal

            pos = MT5PositionReality(
                position_ticket=ticket,
                position_identifier=ticket,
                symbol=req.symbol,
                position_type=MT5PositionType.POSITION_TYPE_BUY if req.type == MT5OrderType.BUY else MT5PositionType.POSITION_TYPE_SELL,
                volume=req.volume,
                price_open=deal.price,
                price_current=deal.price,
                sl=req.sl,
                tp=req.tp,
                swap=Decimal("0.00"),
                profit=Decimal("0.00"),
                magic=req.magic,
                comment=req.comment,
                time_open_utc=now,
            )
            self.active_positions[ticket] = pos

            filled_order = MT5OrderReality(
                order_ticket=ticket,
                position_ticket=ticket,
                symbol=req.symbol,
                order_type=req.type,
                state=MT5OrderState.ORDER_STATE_FILLED,
                volume_initial=req.volume,
                volume_current=Decimal("0.0"),
                price_open=deal.price,
                price_stoplimit=None,
                sl=req.sl,
                tp=req.tp,
                time_setup_utc=now,
                time_done_utc=now,
                magic=req.magic,
                comment=req.comment,
            )
            self.history_orders[ticket] = filled_order

            result = MT5TradeResult(
                retcode=MT5Retcode.TRADE_RETCODE_DONE.value,
                deal=deal_ticket,
                order=ticket,
                volume=req.volume,
                price=deal.price,
                comment="Request executed",
            )

        elif req.action == MT5TradeAction.TRADE_ACTION_PENDING:
            order = MT5OrderReality(
                order_ticket=ticket,
                position_ticket=None,
                symbol=req.symbol,
                order_type=req.type,
                state=MT5OrderState.ORDER_STATE_PLACED,
                volume_initial=req.volume,
                volume_current=req.volume,
                price_open=req.price,
                price_stoplimit=req.stoplimit,
                sl=req.sl,
                tp=req.tp,
                time_setup_utc=now,
                time_done_utc=None,
                magic=req.magic,
                comment=req.comment,
            )
            self.active_orders[ticket] = order

            result = MT5TradeResult(
                retcode=MT5Retcode.TRADE_RETCODE_PLACED.value,
                order=ticket,
                volume=req.volume,
                price=req.price,
                comment="Order placed",
            )

        elif req.action == MT5TradeAction.TRADE_ACTION_REMOVE:
            if req.order is not None and req.order in self.active_orders:
                removed_order = self.active_orders.pop(req.order)
                canceled_order = removed_order.model_copy(
                    update={"state": MT5OrderState.ORDER_STATE_CANCELED, "time_done_utc": now}
                )
                self.history_orders[req.order] = canceled_order

                result = MT5TradeResult(
                    retcode=MT5Retcode.TRADE_RETCODE_CANCEL.value,
                    order=req.order,
                    comment="Order removed",
                )
            else:
                result = MT5TradeResult(
                    retcode=MT5Retcode.TRADE_RETCODE_INVALID_ORDER.value,
                    order=req.order if req.order is not None else ticket,
                    comment="Invalid order ticket or order not found",
                )

        else:
            result = MT5TradeResult(
                retcode=MT5Retcode.TRADE_RETCODE_DONE.value,
                order=ticket,
                comment="Action executed",
            )

        return MT5TransportObservation(
            result=result,
            lineage=command.lineage,
            observed_at=now,
        )

    def orders_get(
        self,
        symbol: Optional[str] = None,
        ticket: Optional[int] = None,
    ) -> Tuple[MT5OrderReality, ...]:
        orders = list(self.active_orders.values())
        if symbol is not None:
            orders = [o for o in orders if o.symbol == symbol]
        if ticket is not None:
            orders = [o for o in orders if o.order_ticket == ticket]
        return tuple(orders)

    def history_orders_get(
        self,
        ticket: Optional[int] = None,
        position: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[MT5OrderReality, ...]:
        orders = list(self.history_orders.values())
        if ticket is not None:
            orders = [o for o in orders if o.order_ticket == ticket]
        if position is not None:
            orders = [o for o in orders if o.position_ticket == position]
        if date_from is not None:
            orders = [o for o in orders if o.time_setup_utc >= date_from]
        if date_to is not None:
            orders = [o for o in orders if o.time_setup_utc <= date_to]
        return tuple(orders)

    def history_orders_total(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> int:
        orders = self.history_orders_get(date_from=date_from, date_to=date_to)
        return len(orders)

    def positions_get(
        self,
        symbol: Optional[str] = None,
        ticket: Optional[int] = None,
    ) -> Tuple[MT5PositionReality, ...]:
        positions = list(self.active_positions.values())
        if symbol is not None:
            positions = [p for p in positions if p.symbol == symbol]
        if ticket is not None:
            positions = [p for p in positions if p.position_ticket == ticket]
        return tuple(positions)

    def history_deals_get(
        self,
        ticket: Optional[int] = None,
        position: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[MT5DealReality, ...]:
        deals = list(self.history_deals.values())
        if ticket is not None:
            deals = [d for d in deals if d.deal_ticket == ticket]
        if position is not None:
            deals = [d for d in deals if d.position_ticket == position]
        if date_from is not None:
            deals = [d for d in deals if d.deal_time_utc >= date_from]
        if date_to is not None:
            deals = [d for d in deals if d.deal_time_utc <= date_to]
        return tuple(deals)

    def history_deals_total(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> int:
        deals = self.history_deals_get(date_from=date_from, date_to=date_to)
        return len(deals)


class NativeMT5Transport:
    """Production Windows C-extension wrapper for MetaTrader 5 Python IPC.

    INVARIANT:
    Dynamic imports prevent import crashes on Linux / CI environments.
    Translates native C-struct namedtuples faithfully into frozen DTOs.
    """

    def __init__(self) -> None:
        self._mt5: Optional[Any] = None

    def _get_mt5(self) -> Any:
        if self._mt5 is None:
            try:
                self._mt5 = importlib.import_module("MetaTrader5")
            except ImportError as e:
                raise MT5DomainError(
                    f"MetaTrader5 package is not available on this platform/runtime: {e}"
                ) from e
        return self._mt5

    def initialize(
        self,
        path: Optional[str] = None,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        timeout_ms: int = 60000,
    ) -> bool:
        mt5 = self._get_mt5()
        kwargs: Dict[str, Any] = {"timeout": timeout_ms}
        if path is not None:
            kwargs["path"] = path
        if login is not None:
            kwargs["login"] = login
        if password is not None:
            kwargs["password"] = password
        if server is not None:
            kwargs["server"] = server
        res: bool = mt5.initialize(**kwargs)
        return bool(res)

    def shutdown(self) -> None:
        mt5 = self._get_mt5()
        mt5.shutdown()

    def is_connected(self) -> bool:
        mt5 = self._get_mt5()
        info = mt5.terminal_info()
        if info is None:
            return False
        return bool(getattr(info, "connected", False))

    def terminal_info(self) -> Optional[Dict[str, Any]]:
        mt5 = self._get_mt5()
        info = mt5.terminal_info()
        if info is None:
            return None
        return {
            "connected": bool(getattr(info, "connected", False)),
            "trade_allowed": bool(getattr(info, "trade_allowed", False)),
            "trade_expert": bool(getattr(info, "trade_expert", False)),
            "community_account": bool(getattr(info, "community_account", False)),
            "community_connection": bool(getattr(info, "community_connection", False)),
        }

    def account_info(self) -> Optional[MT5AccountReality]:
        mt5 = self._get_mt5()
        acc = mt5.account_info()
        if acc is None:
            return None
        raw_margin_mode = getattr(acc, "margin_mode", None)
        if raw_margin_mode is None:
            raise MT5DomainError("MISSING_ACCOUNT_MARGIN_MODE: account object missing required margin_mode property")
        margin_mode = decode_mt5_margin_mode(int(raw_margin_mode))
        return MT5AccountReality(
            login=int(acc.login),
            trade_mode=int(acc.trade_mode),
            margin_mode=margin_mode,
            leverage=int(acc.leverage),
            limit_orders=int(acc.limit_orders),
            margin_so_mode=int(acc.margin_so_mode),
            trade_allowed=bool(acc.trade_allowed),
            trade_expert=bool(acc.trade_expert),
            balance=Decimal(str(acc.balance)),
            credit=Decimal(str(acc.credit)),
            profit=Decimal(str(acc.profit)),
            equity=Decimal(str(acc.equity)),
            margin=Decimal(str(acc.margin)),
            margin_free=Decimal(str(acc.margin_free)),
            margin_level=Decimal(str(acc.margin_level)),
            margin_so_call=Decimal(str(acc.margin_so_call)),
            margin_so_so=Decimal(str(acc.margin_so_so)),
            margin_initial=Decimal(str(getattr(acc, "margin_initial", "0.0"))),
            margin_maintenance=Decimal(str(getattr(acc, "margin_maintenance", "0.0"))),
            currency=str(acc.currency),
        )

    def symbol_info(self, symbol: str) -> Optional[BrokerSymbolSpec]:
        mt5 = self._get_mt5()
        info = mt5.symbol_info(symbol)
        if info is None:
            return None

        exec_mode_map = {
            0: MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_REQUEST,
            1: MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_INSTANT,
            2: MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_MARKET,
            3: MT5TradeExecutionMode.SYMBOL_TRADE_EXECUTION_EXCHANGE,
        }
        if hasattr(info, "trade_exemode"):
            raw_exec_mode = int(info.trade_exemode)
        elif hasattr(info, "trade_execution_mode"):
            raw_exec_mode = int(info.trade_execution_mode)
        else:
            raise MT5TransportError(
                f"MT5 SymbolInfo does not expose a supported execution-mode attribute for {symbol}"
            )
        if raw_exec_mode not in exec_mode_map:
            raise MT5SymbolSpecError(
                f"UNKNOWN_TRADE_EXECUTION_MODE: unmapped trade_execution_mode {raw_exec_mode} for symbol {symbol}"
            )
        exec_mode = exec_mode_map[raw_exec_mode]

        filling_flags: List[str] = []
        filling_mode_mask = int(getattr(info, "filling_mode", 0))
        if filling_mode_mask & 1:
            filling_flags.append("SYMBOL_FILLING_FOK")
        if filling_mode_mask & 2:
            filling_flags.append("SYMBOL_FILLING_IOC")
        if filling_mode_mask & 4:
            filling_flags.append("SYMBOL_FILLING_BOC")

        order_mode_mask = int(getattr(info, "order_mode", 0))
        order_modes: List[str] = []
        if order_mode_mask & 1 or order_mode_mask == 0:
            order_modes.append("SYMBOL_ORDER_MARKET")
        if order_mode_mask & 2:
            order_modes.append("SYMBOL_ORDER_LIMIT")
        if order_mode_mask & 4:
            order_modes.append("SYMBOL_ORDER_STOP")
        if order_mode_mask & 8:
            order_modes.append("SYMBOL_ORDER_STOP_LIMIT")
        if order_mode_mask & 16:
            order_modes.append("SYMBOL_ORDER_SL")
        if order_mode_mask & 32:
            order_modes.append("SYMBOL_ORDER_TP")
        if order_mode_mask & 64:
            order_modes.append("SYMBOL_ORDER_CLOSEBY")
        if not order_modes:
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

    def order_send(self, command: MT5TransportCommand) -> MT5TransportObservation:
        mt5 = self._get_mt5()
        req = command.request

        action_map = {
            MT5TradeAction.TRADE_ACTION_DEAL: 1,
            MT5TradeAction.TRADE_ACTION_PENDING: 5,
            MT5TradeAction.TRADE_ACTION_SLTP: 6,
            MT5TradeAction.TRADE_ACTION_MODIFY: 7,
            MT5TradeAction.TRADE_ACTION_REMOVE: 8,
            MT5TradeAction.TRADE_ACTION_CLOSE_BY: 10,
        }
        order_type_map = {
            MT5OrderType.BUY: 0,
            MT5OrderType.SELL: 1,
            MT5OrderType.BUY_LIMIT: 2,
            MT5OrderType.SELL_LIMIT: 3,
            MT5OrderType.BUY_STOP: 4,
            MT5OrderType.SELL_STOP: 5,
            MT5OrderType.BUY_STOP_LIMIT: 6,
            MT5OrderType.SELL_STOP_LIMIT: 7,
            MT5OrderType.CLOSE_BY: 8,
        }
        filling_map = {
            MT5FillingMode.ORDER_FILLING_FOK: 0,
            MT5FillingMode.ORDER_FILLING_IOC: 1,
            MT5FillingMode.ORDER_FILLING_RETURN: 2,
            MT5FillingMode.ORDER_FILLING_BOC: 3,
        }
        time_map = {
            MT5OrderTime.ORDER_TIME_GTC: 0,
            MT5OrderTime.ORDER_TIME_DAY: 1,
            MT5OrderTime.ORDER_TIME_SPECIFIED: 2,
            MT5OrderTime.ORDER_TIME_SPECIFIED_DAY: 3,
        }

        req_dict: Dict[str, Any] = {
            "action": action_map[req.action],
            "magic": req.magic,
            "symbol": req.symbol,
            "volume": float(req.volume),
            "price": float(req.price),
            "sl": float(req.sl),
            "tp": float(req.tp),
            "deviation": req.deviation,
            "type": order_type_map[req.type],
            "type_filling": filling_map[req.type_filling],
            "type_time": time_map[req.type_time],
            "comment": req.comment,
        }
        if req.order != 0:
            req_dict["order"] = req.order
        if req.position is not None and req.position != 0:
            req_dict["position"] = req.position
        if req.position_by is not None and req.position_by != 0:
            req_dict["position_by"] = req.position_by
        if req.stoplimit is not None and req.stoplimit > Decimal("0.0"):
            req_dict["stoplimit"] = float(req.stoplimit)
        if req.expiration is not None:
            req_dict["expiration"] = int(req.expiration.timestamp())

        native_res = mt5.order_send(req_dict)
        now = datetime.now(timezone.utc)

        if native_res is None:
            last_err = mt5.last_error()
            err_code = int(last_err[0]) if last_err else -1
            err_desc = str(last_err[1]) if last_err else "order_send returned None"
            is_timeout = err_code == MT5ApiErrorCode.RES_E_INTERNAL_FAIL_TIMEOUT.value
            raise MT5TransportError(
                f"NATIVE_ORDER_SEND_FAILED: {err_desc} (API error code {err_code})",
                api_code=err_code,
                is_timeout=is_timeout,
            )
        else:
            result = MT5TradeResult(
                retcode=int(native_res.retcode),
                deal=int(native_res.deal),
                order=int(native_res.order),
                volume=Decimal(str(native_res.volume)),
                price=Decimal(str(native_res.price)),
                bid=Decimal(str(native_res.bid)),
                ask=Decimal(str(native_res.ask)),
                comment=str(native_res.comment),
                request_id=int(native_res.request_id),
                retcode_external=int(native_res.retcode_external),
            )

        return MT5TransportObservation(
            result=result,
            lineage=command.lineage,
            observed_at=now,
        )

    def orders_get(
        self,
        symbol: Optional[str] = None,
        ticket: Optional[int] = None,
    ) -> Tuple[MT5OrderReality, ...]:
        mt5 = self._get_mt5()
        kwargs: Dict[str, Any] = {}
        if symbol is not None:
            kwargs["symbol"] = symbol
        if ticket is not None:
            kwargs["ticket"] = ticket

        raw_orders = mt5.orders_get(**kwargs)
        if raw_orders is None:
            last_err = mt5.last_error()
            err_code = int(last_err[0]) if last_err else -1
            err_desc = str(last_err[1]) if last_err else "orders_get returned None"
            raise MT5TransportError(f"NATIVE_ORDERS_GET_FAILED: {err_desc} (API error code {err_code})")

        parsed: List[MT5OrderReality] = []
        for o in raw_orders:
            parsed.append(self._parse_order_tuple(o))
        return tuple(parsed)

    def history_orders_get(
        self,
        ticket: Optional[int] = None,
        position: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[MT5OrderReality, ...]:
        mt5 = self._get_mt5()
        kwargs: Dict[str, Any] = {}
        if ticket is not None:
            kwargs["ticket"] = ticket
        if position is not None:
            kwargs["position"] = position
        effective_from = date_from
        if date_to is not None and effective_from is None:
            effective_from = datetime.fromtimestamp(0, timezone.utc)
        if effective_from is not None and date_to is not None:
            kwargs["date_from"] = effective_from
            kwargs["date_to"] = date_to
        elif effective_from is not None:
            kwargs["date_from"] = effective_from
        elif date_to is not None:
            kwargs["date_to"] = date_to

        raw_orders = mt5.history_orders_get(**kwargs)
        if raw_orders is None:
            last_err = mt5.last_error()
            err_code = int(last_err[0]) if last_err else -1
            err_desc = str(last_err[1]) if last_err else "history_orders_get returned None"
            raise MT5TransportError(f"NATIVE_HISTORY_ORDERS_GET_FAILED: {err_desc} (API error code {err_code})")

        parsed: List[MT5OrderReality] = []
        for o in raw_orders:
            parsed.append(self._parse_order_tuple(o))
        return tuple(parsed)

    def history_orders_total(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> int:
        if not self.is_connected():
            raise MT5TransportError("Cannot query history_orders_total: transport is disconnected.")
        mt5 = self._get_mt5()
        try:
            effective_from = date_from
            if date_to is not None and effective_from is None:
                effective_from = datetime.fromtimestamp(0, timezone.utc)
            if effective_from is not None and date_to is not None:
                total = mt5.history_orders_total(effective_from, date_to)
            elif effective_from is not None:
                total = mt5.history_orders_total(effective_from)
            else:
                total = mt5.history_orders_total()
            if total is None:
                last_err = mt5.last_error()
                err_code = int(last_err[0]) if last_err else -1
                err_desc = str(last_err[1]) if last_err else "history_orders_total returned None"
                raise MT5TransportError(
                    f"history_orders_total query failed: {err_desc} (code={err_code})",
                    api_code=err_code,
                )
            return int(total)
        except Exception as e:
            if isinstance(e, MT5TransportError):
                raise
            raise MT5TransportError(f"history_orders_total failed with unexpected error: {e}") from e

    def positions_get(
        self,
        symbol: Optional[str] = None,
        ticket: Optional[int] = None,
    ) -> Tuple[MT5PositionReality, ...]:
        mt5 = self._get_mt5()
        kwargs: Dict[str, Any] = {}
        if symbol is not None:
            kwargs["symbol"] = symbol
        if ticket is not None:
            kwargs["ticket"] = ticket

        raw_positions = mt5.positions_get(**kwargs)
        if raw_positions is None:
            last_err = mt5.last_error()
            err_code = int(last_err[0]) if last_err else -1
            err_desc = str(last_err[1]) if last_err else "positions_get returned None"
            raise MT5TransportError(f"NATIVE_POSITIONS_GET_FAILED: {err_desc} (API error code {err_code})")

        parsed: List[MT5PositionReality] = []
        for p in raw_positions:
            raw_pos_type = int(p.type)
            if raw_pos_type == 0:
                pos_type = MT5PositionType.POSITION_TYPE_BUY
            elif raw_pos_type == 1:
                pos_type = MT5PositionType.POSITION_TYPE_SELL
            else:
                raise MT5ValidationError(
                    f"UNKNOWN_POSITION_TYPE: received unmapped position type {raw_pos_type} for position {p.ticket}"
                )

            raw_identifier = getattr(p, "identifier", None)
            if raw_identifier is None:
                raise MT5ValidationError(
                    f"MISSING_POSITION_IDENTIFIER: position object {p.ticket} missing required identifier property"
                )
            position_identifier = int(raw_identifier)
            if position_identifier <= 0:
                raise MT5ValidationError(
                    f"INVALID_POSITION_IDENTIFIER: position identifier must be positive int, got {position_identifier} for position {p.ticket}"
                )

            parsed.append(
                MT5PositionReality(
                    position_ticket=int(p.ticket),
                    position_identifier=position_identifier,
                    symbol=str(p.symbol),
                    position_type=pos_type,
                    volume=Decimal(str(p.volume)),
                    price_open=Decimal(str(p.price_open)),
                    price_current=Decimal(str(p.price_current)),
                    sl=Decimal(str(p.sl)),
                    tp=Decimal(str(p.tp)),
                    swap=Decimal(str(p.swap)),
                    profit=Decimal(str(p.profit)),
                    magic=int(p.magic),
                    comment=str(p.comment),
                    time_open_utc=datetime.fromtimestamp(p.time, timezone.utc),
                )
            )
        return tuple(parsed)

    def history_deals_get(
        self,
        ticket: Optional[int] = None,
        position: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Tuple[MT5DealReality, ...]:
        mt5 = self._get_mt5()
        kwargs: Dict[str, Any] = {}
        if ticket is not None:
            kwargs["ticket"] = ticket
        if position is not None:
            kwargs["position"] = position
        effective_from = date_from
        if date_to is not None and effective_from is None:
            effective_from = datetime.fromtimestamp(0, timezone.utc)
        if effective_from is not None and date_to is not None:
            kwargs["date_from"] = effective_from
            kwargs["date_to"] = date_to
        elif effective_from is not None:
            kwargs["date_from"] = effective_from
        elif date_to is not None:
            kwargs["date_to"] = date_to

        raw_deals = mt5.history_deals_get(**kwargs)
        if raw_deals is None:
            last_err = mt5.last_error()
            err_code = int(last_err[0]) if last_err else -1
            err_desc = str(last_err[1]) if last_err else "history_deals_get returned None"
            raise MT5TransportError(f"NATIVE_HISTORY_DEALS_GET_FAILED: {err_desc} (API error code {err_code})")

        parsed: List[MT5DealReality] = []
        for d in raw_deals:
            raw_deal_type = int(d.type)
            deal_type = decode_mt5_deal_type(raw_deal_type)

            raw_entry = getattr(d, "entry", None)
            if raw_entry is None:
                raise MT5ValidationError(
                    f"MISSING_DEAL_ENTRY: deal {d.ticket} missing required entry property"
                )
            deal_entry = decode_mt5_deal_entry(int(raw_entry))

            parsed.append(
                MT5DealReality(
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
            )
        return tuple(parsed)

    def history_deals_total(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> int:
        if not self.is_connected():
            raise MT5TransportError("Cannot query history_deals_total: transport is disconnected.")
        mt5 = self._get_mt5()
        try:
            effective_from = date_from
            if date_to is not None and effective_from is None:
                effective_from = datetime.fromtimestamp(0, timezone.utc)
            if effective_from is not None and date_to is not None:
                total = mt5.history_deals_total(effective_from, date_to)
            elif effective_from is not None:
                total = mt5.history_deals_total(effective_from)
            else:
                total = mt5.history_deals_total()
            if total is None:
                last_err = mt5.last_error()
                err_code = int(last_err[0]) if last_err else -1
                err_desc = str(last_err[1]) if last_err else "history_deals_total returned None"
                raise MT5TransportError(
                    f"history_deals_total query failed: {err_desc} (code={err_code})",
                    api_code=err_code,
                )
            return int(total)
        except Exception as e:
            if isinstance(e, MT5TransportError):
                raise
            raise MT5TransportError(f"history_deals_total failed with unexpected error: {e}") from e

    def _parse_order_tuple(self, o: Any) -> MT5OrderReality:
        order_type_map = {
            0: MT5OrderType.BUY,
            1: MT5OrderType.SELL,
            2: MT5OrderType.BUY_LIMIT,
            3: MT5OrderType.SELL_LIMIT,
            4: MT5OrderType.BUY_STOP,
            5: MT5OrderType.SELL_STOP,
            6: MT5OrderType.BUY_STOP_LIMIT,
            7: MT5OrderType.SELL_STOP_LIMIT,
            8: MT5OrderType.CLOSE_BY,
        }
        order_state_map = {
            0: MT5OrderState.ORDER_STATE_STARTED,
            1: MT5OrderState.ORDER_STATE_PLACED,
            2: MT5OrderState.ORDER_STATE_CANCELED,
            3: MT5OrderState.ORDER_STATE_PARTIAL,
            4: MT5OrderState.ORDER_STATE_FILLED,
            5: MT5OrderState.ORDER_STATE_REJECTED,
            6: MT5OrderState.ORDER_STATE_EXPIRED,
            7: MT5OrderState.ORDER_STATE_REQUEST_ADD,
            8: MT5OrderState.ORDER_STATE_REQUEST_MODIFY,
            9: MT5OrderState.ORDER_STATE_REQUEST_CANCEL,
        }

        raw_order_type = int(o.type)
        if raw_order_type not in order_type_map:
            raise MT5ValidationError(
                f"UNKNOWN_ORDER_TYPE: received unmapped order type {raw_order_type} for order {o.ticket}"
            )

        raw_order_state = int(o.state)
        if raw_order_state not in order_state_map:
            raise MT5ValidationError(
                f"UNKNOWN_ORDER_STATE: received unmapped order state {raw_order_state} for order {o.ticket}"
            )

        time_done = (
            datetime.fromtimestamp(o.time_done, timezone.utc)
            if getattr(o, "time_done", 0) > 0
            else None
        )
        stoplimit_val = Decimal(str(getattr(o, "price_stoplimit", 0.0)))
        stoplimit_opt = stoplimit_val if stoplimit_val > Decimal("0.0") else None
        pos_id = int(getattr(o, "position_id", 0))
        pos_ticket = pos_id if pos_id > 0 else None

        return MT5OrderReality(
            order_ticket=int(o.ticket),
            position_ticket=pos_ticket,
            symbol=str(o.symbol),
            order_type=order_type_map[raw_order_type],
            state=order_state_map[raw_order_state],
            volume_initial=Decimal(str(o.volume_initial)),
            volume_current=Decimal(str(o.volume_current)),
            price_open=Decimal(str(o.price_open)),
            price_stoplimit=stoplimit_opt,
            sl=Decimal(str(o.sl)),
            tp=Decimal(str(o.tp)),
            time_setup_utc=datetime.fromtimestamp(o.time_setup, timezone.utc),
            time_done_utc=time_done,
            magic=int(o.magic),
            comment=str(o.comment),
        )
