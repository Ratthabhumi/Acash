"""ACASH Paper Trading — Provider-Agnostic Real Market Data Feed (E3.5).

Defines the canonical ``IMarketDataFeed`` adapter contract plus concrete,
credential-free, $0 providers:

- ``BinancePublicKlinesFeed``  — Binance public REST klines (no auth required)
- ``StooqCsvFeed``            — Stooq daily CSV (no auth required)

Design contracts (E3.5):
- Explicit provider identification (provider_id, provider_version).
- Explicit symbol, timeframe, and UTC timezone normalization.
- ``received_at_utc`` wall-clock ingestion time recorded on every bar.
- Data freshness computed as received_at - market event time.
- Sequence tracking and idempotent polling (no duplicate bars emitted).
- Fail-closed on disconnection or malformed responses (DataContractError).
- Never fabricate bid/ask/volume/trade-count/latency. Fields the provider
  does NOT supply are recorded as ``None`` and listed in ``unavailable``.

GOVERNANCE (E3.5):
=============
- This feed is EXECUTION/PAPER INFRASTRUCTURE ONLY.
- It is NOT the D17 data authority.
- It is NOT admissible as MACRO-001 research evidence.
- It is NOT used to backtest MACRO-001.
- No provider credentials are ever required or invented.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from acash.core.domain.enums import BarTimeframe
from acash.core.domain.exceptions import DataContractError

if TYPE_CHECKING:
    from acash.paper.runner import SyntheticBar


# ---------------------------------------------------------------------------
# Feed Diagnostics & Sanitization
# ---------------------------------------------------------------------------


def sanitize_diagnostic_text(text: str) -> str:
    """Sanitize strings for logs/journal, redacting credentials, secrets, and auth tokens."""
    if not text:
        return ""
    res = str(text)
    res = re.sub(r"://([^:@\s]+):([^@\s]+)@", r"://\1:***@", res)
    res = re.sub(
        r"((?:api[_-]?key|secret|token|password|auth|authorization)=)(?:[^\s&]+)",
        r"\1***",
        res,
        flags=re.IGNORECASE,
    )
    res = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", r"\1***", res, flags=re.IGNORECASE)
    return res


# ---------------------------------------------------------------------------
# Feed error hierarchy — strict fail-closed
# ---------------------------------------------------------------------------


class FeedContractError(DataContractError):
    """Base error for market-data feed contract violations."""


class FeedConnectionError(FeedContractError):
    """Raised when the feed cannot connect or the connection is lost.

    Carries optional structured diagnostic metadata to preserve observability
    without compromising fail-closed contract enforcement.
    """

    def __init__(
        self,
        message: str,
        *,
        error_class: Optional[str] = None,
        category: Optional[str] = None,
        operation: Optional[str] = None,
        endpoint: Optional[str] = None,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        status_code: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
        last_poll_utc: Optional[str] = None,
        last_bar_utc: Optional[str] = None,
        reconnect_count: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.error_class = error_class
        self.category = category
        self.operation = operation
        self.endpoint = endpoint
        self.symbol = symbol
        self.timeframe = timeframe
        self.status_code = status_code
        self.timeout_seconds = timeout_seconds
        self.last_poll_utc = last_poll_utc
        self.last_bar_utc = last_bar_utc
        self.reconnect_count = reconnect_count


class FeedMalformedResponseError(FeedContractError):
    """Raised when a provider returns data that cannot be parsed."""


class FeedDataValidationError(FeedContractError):
    """Raised when a parsed bar violates the canonical bar contract."""


# ---------------------------------------------------------------------------
# FeedBar — canonical normalized real market bar
# ---------------------------------------------------------------------------


class FeedBar(BaseModel):
    """Canonical normalized real market data bar for paper-trading ingestion.

    Invariants:
    - timestamp_utc is timezone-aware and normalized to UTC (event close time).
    - received_at_utc is the monotonic wall-clock ingestion timestamp (UTC).
    - OHLC prices are strictly positive finite Decimals; high >= max(o,c),
      low <= min(o,c).
    - Volume is non-negative when supplied; None means the provider does not
      supply volume (recorded as unavailable, never fabricated).
    - bid/ask are the provider top-of-book quote; None when unavailable.
    - trade_count is the number of trades when the provider supplies it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str = Field(description="Provider identifier (e.g. 'binance.public').")
    provider_version: str = Field(description="Provider transport version.")
    source_id: str = Field(description="Provider-native source event identifier.")
    symbol: str = Field(description="Provider-native symbol string.")
    timeframe: BarTimeframe = Field(description="Canonical ACASH bar timeframe.")
    timestamp_utc: datetime = Field(description="Bar close/market event time (UTC).")
    received_at_utc: datetime = Field(description="Wall clock ingestion time (UTC).")
    open: Decimal = Field(description="Open price.")
    high: Decimal = Field(description="High price.")
    low: Decimal = Field(description="Low price.")
    close: Decimal = Field(description="Close price.")
    volume: Optional[Decimal] = Field(
        default=None, description="Volume when the provider supplies it; None = unavailable."
    )
    bid: Optional[Decimal] = Field(
        default=None, description="Top-of-book bid when supplied; None = unavailable."
    )
    ask: Optional[Decimal] = Field(
        default=None, description="Top-of-book ask when supplied; None = unavailable."
    )
    trade_count: Optional[int] = Field(
        default=None, description="Trade count when supplied; None = unavailable."
    )
    sequence: Optional[int] = Field(
        default=None, description="Provider monotonic sequence when available."
    )
    unavailable: List[str] = Field(
        default_factory=list,
        description="Explicit list of fields the provider did NOT supply.",
    )

    @field_validator("symbol")
    @classmethod
    def _validate_symbol(cls, v: str) -> str:
        if not v or not v.strip():
            raise FeedDataValidationError("FeedBar.symbol must be non-empty.")
        return v.strip()

    @field_validator("source_id")
    @classmethod
    def _validate_source_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise FeedDataValidationError("FeedBar.source_id must be non-empty.")
        return v.strip()

    @field_validator("timestamp_utc", "received_at_utc", mode="after")
    @classmethod
    def _validate_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise FeedDataValidationError("FeedBar datetimes must be timezone-aware UTC.")
        return v.astimezone(timezone.utc)

    @field_validator("open", "high", "low", "close")
    @classmethod
    def _validate_price(cls, v: Decimal, info: Any) -> Decimal:
        field_name = getattr(info, "field_name", None) or "price"
        if not isinstance(v, Decimal) or not v.is_finite():
            raise FeedDataValidationError(f"FeedBar.{field_name} must be a finite Decimal.")
        if v <= Decimal("0"):
            raise FeedDataValidationError(f"FeedBar.{field_name} must be strictly positive.")
        return v

    @field_validator("volume", "bid", "ask")
    @classmethod
    def _validate_finite_optional(cls, v: Optional[Decimal], info: Any) -> Optional[Decimal]:
        if v is None:
            return None
        field_name = getattr(info, "field_name", None) or "value"
        if not isinstance(v, Decimal) or not v.is_finite():
            raise FeedDataValidationError(f"FeedBar.{field_name} must be a finite Decimal.")
        if v < Decimal("0"):
            raise FeedDataValidationError(f"FeedBar.{field_name} must be non-negative.")
        return v

    @field_validator("trade_count")
    @classmethod
    def _validate_trade_count(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return None
        if v < 0:
            raise FeedDataValidationError("FeedBar.trade_count must be non-negative.")
        return v

    @classmethod
    def build(cls, **kwargs: Any) -> "FeedBar":
        """Construct a FeedBar with uniform fail-closed error semantics.

        Pydantic's ValidationError is normalized into FeedDataValidationError so
        every validation violation surfaces through the canonical DataContractError
        hierarchy (never a raw framework exception).
        """
        try:
            return cls(**kwargs)
        except ValidationError as exc:
            raise FeedDataValidationError(
                f"FeedBar validation failed: {exc}"
            ) from exc

    @model_validator(mode="after")
    def _validate_geometry(self) -> "FeedBar":
        """OHLC geometry invariants: high >= max(o,c), low <= min(o,c)."""
        if self.high < max(self.open, self.close):
            raise FeedDataValidationError(
                "FeedBar.high must be >= max(open, close); "
                f"got open={self.open} high={self.high} close={self.close}."
            )
        if self.low > min(self.open, self.close):
            raise FeedDataValidationError(
                "FeedBar.low must be <= min(open, close); "
                f"got open={self.open} low={self.low} close={self.close}."
            )
        return self

    def data_age_ms(self) -> int:
        """Freshness: wall-clock ingestion minus market event time (ms)."""
        delta = (self.received_at_utc - self.timestamp_utc).total_seconds()
        return max(0, int(delta * 1000))

    def to_journal_payload(self) -> Dict[str, Any]:
        """Canonical journal payload for the MARKET_DATA layer (E3.5)."""
        payload: Dict[str, Any] = {
            "provider": self.provider,
            "provider_version": self.provider_version,
            "source_id": self.source_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe.value,
            "timestamp_utc": self.timestamp_utc.isoformat(),
            "received_at_utc": self.received_at_utc.isoformat(),
            "open": str(self.open),
            "high": str(self.high),
            "low": str(self.low),
            "close": str(self.close),
            "data_age_ms": self.data_age_ms(),
            "source": self.provider,
            "GOVERNANCE_LABEL": "REAL_MARKET_DATA_EXECUTION_INFRA_ONLY",
        }
        if self.volume is not None:
            payload["volume"] = str(self.volume)
        if self.bid is not None:
            payload["bid"] = str(self.bid)
        if self.ask is not None:
            payload["ask"] = str(self.ask)
        if self.trade_count is not None:
            payload["trade_count"] = self.trade_count
        if self.sequence is not None:
            payload["sequence"] = self.sequence
        payload["unavailable"] = sorted(self.unavailable)
        return payload


# ---------------------------------------------------------------------------
# FeedStatus — observability for the feed connection
# ---------------------------------------------------------------------------


@dataclass
class FeedStatus:
    """Connection status and freshness telemetry for one feed."""

    provider: str
    is_connected: bool
    last_bar_utc: Optional[datetime] = None
    last_poll_utc: Optional[datetime] = None
    data_age_ms: int = 0
    reconnect_count: int = 0
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "is_connected": self.is_connected,
            "last_bar_utc": self.last_bar_utc.isoformat() if self.last_bar_utc else None,
            "last_poll_utc": self.last_poll_utc.isoformat() if self.last_poll_utc else None,
            "data_age_ms": self.data_age_ms,
            "reconnect_count": self.reconnect_count,
            "last_error": self.last_error,
        }


# ---------------------------------------------------------------------------
# IMarketDataFeed — provider-agnostic adapter contract (E3.5)
# ---------------------------------------------------------------------------


class IMarketDataFeed(ABC):
    """Provider-agnostic real market data feed adapter.

    Implementations MUST:
    - Identify themselves via provider_id / provider_version.
    - Normalize all timestamps to timezone-aware UTC.
    - Record received_at_utc for every emitted bar.
    - Track a monotonic sequence and deduplicate on repeated polling.
    - Raise DataContractError-derived errors on failure (never silently return
      fabricated or stale data as fresh).
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Stable provider identifier (e.g. 'binance.public.klines')."""

    @property
    @abstractmethod
    def provider_version(self) -> str:
        """Provider transport implementation version."""

    @property
    @abstractmethod
    def symbol(self) -> str:
        """Provider-native symbol being polled."""

    @property
    @abstractmethod
    def timeframe(self) -> BarTimeframe:
        """Canonical bar timeframe being polled."""

    @abstractmethod
    def connect(self) -> None:
        """Open the connection. Fail-closed on error."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close the connection. Idempotent."""

    @abstractmethod
    def poll_next_bar(self) -> Optional[FeedBar]:
        """Poll the next new bar, or None if no new bar is available yet.

        Must be idempotent: a bar already emitted is not returned twice.
        Raises FeedConnectionError on disconnection and
        FeedMalformedResponseError on malformed provider data.
        """

    @abstractmethod
    def status(self) -> FeedStatus:
        """Return current connection/freshness telemetry."""


# ---------------------------------------------------------------------------
# Binance public klines — free, credential-free, real OHLCV
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _KlineCandidate:
    """Internal structured representation of a single candidate kline from Binance."""

    open_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    close_ms: int
    trade_count: int


class BinancePublicKlinesFeed(IMarketDataFeed):
    """Free public Binance REST klines feed. NO credentials required.

    Admits finalized/closed candles only. An in-progress (open) candle is never
    emitted. Finalization is determined explicitly by verifying that the candle's
    close time (close_ms) is less than or equal to the captured observation clock
    (close_ms <= observation_now_ms).

    Supplies real OHLCV + volume + trade_count. bid/ask are NOT supplied by
    the klines endpoint and are therefore recorded as unavailable (never
    fabricated from trades).

    Catch-Up Scope Boundary:
    Polls up to candidate_limit (default 5) recent klines to tolerate transient
    polling latency. If an extended disconnect exceeds the candidate window,
    only the newest finalized candle is emitted and continuity tracking journals
    the elapsed gap. ACASH does not fabricate missing historical bars.
    """

    PROVIDER_ID = "binance.public.klines"
    PROVIDER_VERSION = "1.0.0"
    DEFAULT_CANDIDATE_LIMIT = 5

    _TIMEFRAME_MAP: Dict[BarTimeframe, str] = {
        BarTimeframe.M1: "1m",
        BarTimeframe.M5: "5m",
        BarTimeframe.M15: "15m",
        BarTimeframe.H1: "1h",
        BarTimeframe.H4: "4h",
        BarTimeframe.D1: "1d",
    }

    def __init__(
        self,
        symbol: str,
        timeframe: BarTimeframe = BarTimeframe.M1,
        *,
        client: Optional[httpx.Client] = None,
        clock: Optional[Callable[[], datetime]] = None,
        candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
    ) -> None:
        if not symbol or not symbol.strip():
            raise FeedContractError("BinancePublicKlinesFeed: symbol must be non-empty.")
        if timeframe not in self._TIMEFRAME_MAP:
            raise FeedContractError(
                f"BinancePublicKlinesFeed: unsupported timeframe {timeframe!r}."
            )
        self._symbol = symbol.strip().upper()
        self._tf = timeframe
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(10.0, connect=5.0, read=10.0),
            limits=httpx.Limits(max_keepalive_connections=1, max_connections=2),
        )
        self._clock: Callable[[], datetime] = clock or (lambda: datetime.now(timezone.utc))
        self._candidate_limit = max(1, candidate_limit)
        self._is_connected = False
        self._last_source_id: Optional[str] = None
        self._last_bar_utc: Optional[datetime] = None
        self._last_poll_utc: Optional[datetime] = None
        self._reconnect_count = 0
        self._last_error: Optional[str] = None

    def _get_observation_now(self) -> datetime:
        """Capture the single observation instant normalized to UTC."""
        now = self._clock()
        if now.tzinfo is None:
            return now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc)

    # -- identity -----------------------------------------------------------

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    @property
    def provider_version(self) -> str:
        return self.PROVIDER_VERSION

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def timeframe(self) -> BarTimeframe:
        return self._tf

    # -- lifecycle -----------------------------------------------------------

    def connect(self) -> None:
        endpoint = "https://api.binance.com/api/v3/klines"
        try:
            resp = self._client.get(
                endpoint,
                params={
                    "symbol": self._symbol,
                    "interval": self._TIMEFRAME_MAP[self._tf],
                    "limit": self._candidate_limit,
                },
            )
            resp.raise_for_status()
        except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError) as exc:
            self._is_connected = False
            error_cls = exc.__class__.__name__
            self._last_error = f"CONNECT_ERROR: {error_cls}"

            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if isinstance(exc, httpx.TimeoutException):
                category = "TIMEOUT"
            elif isinstance(exc, httpx.HTTPStatusError):
                category = "HTTP_ERROR"
            else:
                category = "CONNECTION_ERROR"

            timeout_sec = None
            if hasattr(self._client, "timeout"):
                timeout_sec = getattr(self._client.timeout, "connect", None)

            msg = (
                f"BinancePublicKlinesFeed.connect failed: {error_cls}. "
                "FEED DISCONNECTED — no further market data decisions may be made."
            )
            raise FeedConnectionError(
                sanitize_diagnostic_text(msg),
                error_class=error_cls,
                category=category,
                operation="connect",
                endpoint=endpoint,
                symbol=self._symbol,
                timeframe=self._tf.value,
                status_code=status_code,
                timeout_seconds=timeout_sec,
                last_poll_utc=self._last_poll_utc.isoformat() if self._last_poll_utc else None,
                last_bar_utc=self._last_bar_utc.isoformat() if self._last_bar_utc else None,
                reconnect_count=self._reconnect_count,
            ) from exc
        self._is_connected = True
        self._last_poll_utc = self._get_observation_now()

    def disconnect(self) -> None:
        self._is_connected = False

    # -- polling -------------------------------------------------------------

    def poll_next_bar(self) -> Optional[FeedBar]:
        if not self._is_connected:
            raise FeedConnectionError(
                "BinancePublicKlinesFeed.poll_next_bar: feed is not connected. "
                "FEED DISCONNECTED — no market data decisions may be made.",
                error_class="FeedNotConnected",
                category="NOT_CONNECTED",
                operation="poll",
                symbol=self._symbol,
                timeframe=self._tf.value,
                last_poll_utc=self._last_poll_utc.isoformat() if self._last_poll_utc else None,
                last_bar_utc=self._last_bar_utc.isoformat() if self._last_bar_utc else None,
                reconnect_count=self._reconnect_count,
            )
        endpoint = "https://api.binance.com/api/v3/klines"
        try:
            resp = self._client.get(
                endpoint,
                params={
                    "symbol": self._symbol,
                    "interval": self._TIMEFRAME_MAP[self._tf],
                    "limit": self._candidate_limit,
                },
            )
            resp.raise_for_status()
            raw = resp.json()
        except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError) as exc:
            self._is_connected = False
            self._reconnect_count += 1
            error_cls = exc.__class__.__name__
            self._last_error = f"POLL_ERROR: {error_cls}"

            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if isinstance(exc, httpx.TimeoutException):
                category = "TIMEOUT"
            elif isinstance(exc, httpx.HTTPStatusError):
                category = "HTTP_ERROR"
            else:
                category = "CONNECTION_ERROR"

            timeout_sec = None
            if hasattr(self._client, "timeout"):
                timeout_sec = getattr(self._client.timeout, "read", None)

            msg = (
                f"BinancePublicKlinesFeed.poll_next_bar connection lost: {error_cls}. "
                "FEED DISCONNECTED — no market data decisions may be made."
            )
            raise FeedConnectionError(
                sanitize_diagnostic_text(msg),
                error_class=error_cls,
                category=category,
                operation="poll",
                endpoint=endpoint,
                symbol=self._symbol,
                timeframe=self._tf.value,
                status_code=status_code,
                timeout_seconds=timeout_sec,
                last_poll_utc=self._last_poll_utc.isoformat() if self._last_poll_utc else None,
                last_bar_utc=self._last_bar_utc.isoformat() if self._last_bar_utc else None,
                reconnect_count=self._reconnect_count,
            ) from exc
        except ValueError as exc:
            raise FeedMalformedResponseError(
                f"BinancePublicKlinesFeed: response was not valid JSON: {exc}"
            ) from exc

        # Single observation clock captured for this poll
        observation_now = self._get_observation_now()
        self._last_poll_utc = observation_now

        if not isinstance(raw, list) or len(raw) == 0:
            raise FeedMalformedResponseError(
                "BinancePublicKlinesFeed: expected a non-empty array of klines."
            )

        observation_now_ms = int(observation_now.timestamp() * 1000)

        # 1. Parse structural fields for all candidate rows
        candidates = [self._parse_candidate_row(r) for r in raw]

        # 2. Filter closed candidates: candle close_ms must be <= observation_now_ms
        closed_candidates = [c for c in candidates if c.close_ms <= observation_now_ms]
        if not closed_candidates:
            # All candidates are open/in-progress; do NOT mutate _last_source_id or _last_bar_utc
            return None

        # 3. Select newest valid closed candidate
        newest = max(closed_candidates, key=lambda c: c.close_ms)
        source_id = f"{newest.open_ms}:{newest.close_ms}"

        # 4. Deduplicate on finalized source_id
        if source_id == self._last_source_id:
            return None

        # 5. Build FeedBar with canonical event timestamp and single observation instant
        event_time = datetime.fromtimestamp(newest.close_ms / 1000.0, tz=timezone.utc)
        if event_time > observation_now:
            raise FeedContractError(
                f"BinancePublicKlinesFeed: impossible future event_time {event_time.isoformat()} "
                f"> received_at {observation_now.isoformat()} for finalized candidate {source_id}."
            )

        bar = FeedBar.build(
            provider=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            source_id=source_id,
            symbol=self._symbol,
            timeframe=self._tf,
            timestamp_utc=event_time,
            received_at_utc=observation_now,
            open=newest.open,
            high=newest.high,
            low=newest.low,
            close=newest.close,
            volume=newest.volume,
            trade_count=newest.trade_count,
            unavailable=["bid", "ask", "latency"],
        )

        # 6. Commit admitted state only after successful validation
        self._last_source_id = source_id
        self._last_bar_utc = event_time
        return bar

    def _parse_candidate_row(self, row: Any) -> _KlineCandidate:
        """Parse raw API row into _KlineCandidate, fail-closed on malformed structure."""
        if not isinstance(row, list) or len(row) < 9:
            raise FeedMalformedResponseError(
                "BinancePublicKlinesFeed: malformed kline row (expected >= 9 fields)."
            )
        try:
            open_ms = int(row[0])
            open_dec = Decimal(str(row[1]))
            high_dec = Decimal(str(row[2]))
            low_dec = Decimal(str(row[3]))
            close_dec = Decimal(str(row[4]))
            volume_dec = Decimal(str(row[5]))
            close_ms = int(row[6])
            trade_count = int(row[8])
        except (TypeError, ValueError, IndexError, InvalidOperation) as exc:
            raise FeedMalformedResponseError(
                f"BinancePublicKlinesFeed: cannot parse kline row: {exc}"
            ) from exc

        return _KlineCandidate(
            open_ms=open_ms,
            open=open_dec,
            high=high_dec,
            low=low_dec,
            close=close_dec,
            volume=volume_dec,
            close_ms=close_ms,
            trade_count=trade_count,
        )

    # -- status ---------------------------------------------------------------

    def status(self) -> FeedStatus:
        age = 0
        if self._last_bar_utc is not None:
            now = self._get_observation_now()
            delta_sec = (now - self._last_bar_utc).total_seconds()
            if delta_sec < -0.001:
                raise FeedContractError(
                    f"BinancePublicKlinesFeed: last_bar_utc {self._last_bar_utc.isoformat()} "
                    f"is in the future relative to observation clock {now.isoformat()}."
                )
            age = max(0, int(round(delta_sec * 1000)))
        return FeedStatus(
            provider=self.PROVIDER_ID,
            is_connected=self._is_connected,
            last_bar_utc=self._last_bar_utc,
            last_poll_utc=self._last_poll_utc,
            data_age_ms=age,
            reconnect_count=self._reconnect_count,
            last_error=self._last_error,
        )


# ---------------------------------------------------------------------------
# Stooq daily CSV — free, credential-free, daily OHLCV (FX/equity/indices)
# ---------------------------------------------------------------------------


class StooqCsvFeed(IMarketDataFeed):
    """Free Stooq daily CSV feed (GET /q/d/l/?s=<SYMBOL>&i=d). No auth.

    Supplies real daily OHLC. volume is supplied for most equities/indices but
    is blank for many FX streams; blanks are recorded as unavailable.
    """

    PROVIDER_ID = "stooq.csv.daily"
    PROVIDER_VERSION = "1.0.0"

    def __init__(
        self,
        symbol: str,
        timeframe: BarTimeframe = BarTimeframe.D1,
        *,
        client: Optional[httpx.Client] = None,
    ) -> None:
        if not symbol or not symbol.strip():
            raise FeedContractError("StooqCsvFeed: symbol must be non-empty.")
        if timeframe != BarTimeframe.D1:
            raise FeedContractError(
                f"StooqCsvFeed: only {BarTimeframe.D1.value} is supported, got {timeframe!r}."
            )
        self._symbol = symbol.strip().lower()
        self._tf = timeframe
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(10.0, connect=5.0, read=10.0),
            limits=httpx.Limits(max_keepalive_connections=1, max_connections=2),
        )
        self._is_connected = False
        self._last_date: Optional[str] = None
        self._last_bar_utc: Optional[datetime] = None
        self._last_poll_utc: Optional[datetime] = None
        self._reconnect_count = 0
        self._last_error: Optional[str] = None

    @property
    def provider_id(self) -> str:
        return self.PROVIDER_ID

    @property
    def provider_version(self) -> str:
        return self.PROVIDER_VERSION

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def timeframe(self) -> BarTimeframe:
        return self._tf

    def connect(self) -> None:
        try:
            resp = self._client.get(
                "https://stooq.com/q/d/l/",
                params={"s": self._symbol, "i": "d"},
            )
            resp.raise_for_status()
        except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError) as exc:
            self._is_connected = False
            self._last_error = f"CONNECT_ERROR: {exc.__class__.__name__}"
            raise FeedConnectionError(
                f"StooqCsvFeed.connect failed: {exc.__class__.__name__}. "
                "FEED DISCONNECTED — no further market data decisions may be made.",
                error_class=exc.__class__.__name__,
                category="TIMEOUT" if isinstance(exc, httpx.TimeoutException) else ("HTTP_ERROR" if isinstance(exc, httpx.HTTPStatusError) else "CONNECTION_ERROR"),
                operation="connect",
                endpoint="https://stooq.com/q/d/l/",
                symbol=self._symbol,
                timeframe=self._tf.value,
            ) from exc
        self._is_connected = True
        self._last_poll_utc = datetime.now(timezone.utc)

    def disconnect(self) -> None:
        self._is_connected = False

    def poll_next_bar(self) -> Optional[FeedBar]:
        if not self._is_connected:
            raise FeedConnectionError(
                "StooqCsvFeed.poll_next_bar: feed is not connected. "
                "FEED DISCONNECTED — no market data decisions may be made.",
                error_class="FeedNotConnected",
                category="NOT_CONNECTED",
                operation="poll",
                symbol=self._symbol,
                timeframe=self._tf.value,
            )
        try:
            resp = self._client.get(
                "https://stooq.com/q/d/l/",
                params={"s": self._symbol, "i": "d"},
            )
            resp.raise_for_status()
            text = resp.text
        except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError) as exc:
            self._is_connected = False
            self._reconnect_count += 1
            self._last_error = f"POLL_ERROR: {exc.__class__.__name__}"
            raise FeedConnectionError(
                f"StooqCsvFeed.poll_next_bar connection lost: {exc.__class__.__name__}. "
                "FEED DISCONNECTED — no market data decisions may be made.",
                error_class=exc.__class__.__name__,
                category="TIMEOUT" if isinstance(exc, httpx.TimeoutException) else ("HTTP_ERROR" if isinstance(exc, httpx.HTTPStatusError) else "CONNECTION_ERROR"),
                operation="poll",
                endpoint="https://stooq.com/q/d/l/",
                symbol=self._symbol,
                timeframe=self._tf.value,
                reconnect_count=self._reconnect_count,
            ) from exc

        self._last_poll_utc = datetime.now(timezone.utc)
        return self._parse_csv(text)

    def _parse_csv(self, text: str) -> Optional[FeedBar]:
        import csv
        import io

        try:
            reader = csv.DictReader(io.StringIO(text))
            rows = list(reader)
        except Exception as exc:
            raise FeedMalformedResponseError(f"StooqCsvFeed: cannot parse CSV: {exc}") from exc
        if not rows:
            raise FeedMalformedResponseError("StooqCsvFeed: empty CSV response.")

        last = rows[-1]
        date_str = str(last.get("Date", "")).strip()
        if not date_str:
            raise FeedMalformedResponseError("StooqCsvFeed: missing Date column.")

        # Idempotent polling: deduplicate on the daily date string.
        if date_str == self._last_date:
            return None
        self._last_date = date_str

        try:
            event_time = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
            open_dec = Decimal(last["Open"])
            high_dec = Decimal(last["High"])
            low_dec = Decimal(last["Low"])
            close_dec = Decimal(last["Close"])
        except (KeyError, ValueError, TypeError, InvalidOperation) as exc:
            raise FeedMalformedResponseError(f"StooqCsvFeed: missing or malformed OHLC column: {exc}") from exc

        volume_raw = str(last.get("Volume", "")).strip()
        volume_dec: Optional[Decimal] = None
        unavailable: List[str] = ["latency"]
        if volume_raw:
            try:
                volume_dec = Decimal(volume_raw)
            except (ValueError, TypeError, InvalidOperation):
                unavailable.append("volume")
        else:
            unavailable.append("volume")
        unavailable.extend(["bid", "ask", "trade_count"])
        unavailable = sorted(set(unavailable))

        received_at = datetime.now(timezone.utc)
        bar = FeedBar.build(
            provider=self.PROVIDER_ID,
            provider_version=self.PROVIDER_VERSION,
            source_id=date_str,
            symbol=self._symbol,
            timeframe=self._tf,
            timestamp_utc=event_time,
            received_at_utc=received_at,
            open=open_dec,
            high=high_dec,
            low=low_dec,
            close=close_dec,
            volume=volume_dec,
            unavailable=unavailable,
        )
        self._last_bar_utc = event_time
        return bar

    def status(self) -> FeedStatus:
        age = 0
        if self._last_bar_utc is not None:
            now = datetime.now(timezone.utc)
            age = max(0, int((now - self._last_bar_utc).total_seconds() * 1000))
        return FeedStatus(
            provider=self.PROVIDER_ID,
            is_connected=self._is_connected,
            last_bar_utc=self._last_bar_utc,
            last_poll_utc=self._last_poll_utc,
            data_age_ms=age,
            reconnect_count=self._reconnect_count,
            last_error=self._last_error,
        )


# ---------------------------------------------------------------------------
# Feed bar → runner bar adapter (SyntheticBar with provenance)
# ---------------------------------------------------------------------------


def feed_bar_to_synthetic_bar(bar: FeedBar, strategy_symbol: str) -> "SyntheticBar":
    """Convert a normalized FeedBar into the runner's input bar with provenance.

    The provenance carries feed provider, source id, received_at, sequence and
    the explicit unavailability list so the journal records what the strategy
    actually saw, including fields the provider did not supply.
    """
    from acash.paper.runner import SyntheticBar  # local import avoids cycle

    return SyntheticBar(
        timestamp_utc=bar.timestamp_utc,
        symbol=strategy_symbol,
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        volume=bar.volume if bar.volume is not None else Decimal("0"),
        feed_source=bar.provider,
        feed_source_version=bar.provider_version,
        feed_source_id=bar.source_id,
        received_at_utc=bar.received_at_utc,
        feed_sequence=bar.sequence,
        feed_bid=bar.bid,
        feed_ask=bar.ask,
        feed_trade_count=bar.trade_count,
        feed_unavailable=list(bar.unavailable),
        data_age_ms=bar.data_age_ms(),
    )