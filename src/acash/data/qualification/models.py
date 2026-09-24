"""Models, enumerations, DTOs, and manifest schemas for historical SIP data qualification."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

# Import for type checking only – runtime import handled via forward references
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from acash.data.qualification.client import SipContractViolationError, SipRetrievalResult

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from acash.core.domain.enums import BarTimeframe
from acash.core.domain.exceptions import DataContractError, DomainValidationError
from acash.core.domain.market_data import Bar
from acash.core.domain.types import ensure_finite_decimal
from acash.data.schema import validate_decimal128_bounds


class QualificationCheckStatus(str, Enum):
    """Sub-verification result statuses."""
    PASS = "PASS"
    FAIL = "FAIL"
    UNVERIFIED = "UNVERIFIED"
    BLOCKED = "BLOCKED"


class ProvenanceBasis(str, Enum):
    """Epistemic basis for asserting provider data source provenance."""
    RESPONSE_EXPLICIT = "RESPONSE_EXPLICIT"
    DOCUMENTED_API_CONTRACT = "DOCUMENTED_API_CONTRACT"
    UNVERIFIED = "UNVERIFIED"


OFFICIAL_CONTRACT_PROVIDER: str = "Alpaca"
OFFICIAL_CONTRACT_FEED: str = "sip"
OFFICIAL_CONTRACT_REFERENCES: List[str] = [
    "https://docs.alpaca.markets/us/reference/stockbars",
    "https://docs.alpaca.markets/us/docs/market-data-faq",
]
OFFICIAL_CONTRACT_SEMANTICS: str = (
    "feed=sip => all US exchanges / SIP consolidated feed; "
    "historical SIP requires end >= 15 minutes old for unsubscribed access"
)
OFFICIAL_CONTRACT_RECORDED_AT_UTC: str = "2026-09-18T00:00:00Z"


class SourceQualificationStatus(str, Enum):
    """Overall state of the historical market data source qualification."""
    UNVERIFIED = "UNVERIFIED"
    ACCESS_VERIFIED = "ACCESS_VERIFIED"
    CONTRACT_VERIFIED = "CONTRACT_VERIFIED"
    DATA_SOURCE_TECHNICALLY_QUALIFIED = "DATA_SOURCE_TECHNICALLY_QUALIFIED"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"


class VwapAuthorityStatus(str, Enum):
    """Authority standing of provider-supplied VWAP values."""
    UNVERIFIED = "UNVERIFIED"
    QUALIFIED = "QUALIFIED"
    REJECTED = "REJECTED"


class MarketDataFeed(str, Enum):
    """Declared feed parameter."""
    SIP = "sip"
    IEX = "iex"
    OTHER = "other"


class PriceAdjustment(str, Enum):
    """Declared price adjustment parameter."""
    RAW = "raw"
    SPLIT = "split"
    DIVIDEND = "dividend"
    ALL = "all"


class QualityRuleCode(str, Enum):
    """Data quality and integrity rule identifiers."""
    OUTSIDE_REGULAR_HOURS = "OUTSIDE_REGULAR_HOURS"
    NON_MONOTONIC_TIMESTAMP = "NON_MONOTONIC_TIMESTAMP"
    DUPLICATE_TIMESTAMP = "DUPLICATE_TIMESTAMP"
    INVALID_PRICE = "INVALID_PRICE"
    INVALID_OHLC_BOUNDS = "INVALID_OHLC_BOUNDS"
    NEGATIVE_VOLUME = "NEGATIVE_VOLUME"
    NON_FINITE_VALUE = "NON_FINITE_VALUE"
    CALENDAR_AUTHORITY_UNVERIFIED = "CALENDAR_AUTHORITY_UNVERIFIED"
    MISSING_BAR = "MISSING_BAR"


class QualitySeverity(str, Enum):
    """Severity classification for quality findings."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class QualityFinding(BaseModel):
    """Finding emitted by qualification validation."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    rule: QualityRuleCode
    severity: QualitySeverity
    message: str
    timestamp_utc: Optional[datetime] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class HistoricalSipBar(BaseModel):
    """Source-specific immutable DTO for historical intraday equity bars.

    Preserves provider-supplied trade count and VWAP without mutating the
    canonical core Bar model.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    trade_count: Optional[int] = None
    provider_vwap: Optional[Decimal] = None

    @field_validator("timestamp_utc")
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise DataContractError("Bar timestamp must be timezone-aware UTC.")
        return v.astimezone(timezone.utc)

    @field_validator("open", "high", "low", "close")
    @classmethod
    def validate_prices(cls, v: Decimal, info: Any) -> Decimal:
        field_name = getattr(info, "field_name", "price") or "price"
        ensure_finite_decimal(v, field_name=field_name)
        validate_decimal128_bounds(v, field_name=field_name)
        if v <= Decimal("0"):
            raise DomainValidationError(f"{field_name} must be strictly positive (> 0), got: {v}")
        return v

    @field_validator("volume")
    @classmethod
    def validate_volume(cls, v: Decimal) -> Decimal:
        ensure_finite_decimal(v, field_name="volume")
        validate_decimal128_bounds(v, field_name="volume")
        if v < Decimal("0"):
            raise DomainValidationError(f"volume must be non-negative (>= 0), got: {v}")
        return v

    @field_validator("trade_count")
    @classmethod
    def validate_trade_count(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise DomainValidationError(f"trade_count must be non-negative (>= 0), got: {v}")
        return v

    @field_validator("provider_vwap")
    @classmethod
    def validate_provider_vwap(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            ensure_finite_decimal(v, field_name="provider_vwap")
            validate_decimal128_bounds(v, field_name="provider_vwap")
            if v <= Decimal("0"):
                raise DomainValidationError(f"provider_vwap must be strictly positive (> 0), got: {v}")
        return v

    @model_validator(mode="after")
    def validate_geometry(self) -> "HistoricalSipBar":
        max_body = max(self.open, self.close)
        min_body = min(self.open, self.close)
        if self.high < max_body:
            raise DomainValidationError(
                f"high ({self.high}) cannot be less than max(open, close) ({max_body})"
            )
        if self.low > min_body:
            raise DomainValidationError(
                f"low ({self.low}) cannot be greater than min(open, close) ({min_body})"
            )
        return self

    def to_canonical_bar(
        self,
        symbol: str,
        timeframe: BarTimeframe = BarTimeframe.M1,
        knowledge_time_utc: Optional[datetime] = None,
        duration_seconds: int = 60,
    ) -> Bar:
        """Convert to existing canonical ACASH Bar without mutating core Bar."""
        from datetime import timedelta
        start = self.timestamp_utc
        end = start + timedelta(seconds=duration_seconds)
        k_time = knowledge_time_utc or end
        return Bar(
            symbol=symbol,
            timeframe=timeframe,
            event_start_utc=start,
            event_end_utc=end,
            knowledge_time_utc=k_time,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
        )


class SipPageMetadata(BaseModel):
    """Metadata for a single paginated HTTP response payload."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    page_index: int
    bar_count: int
    raw_sha256: str
    byte_length: int
    relative_artifact_path: str
    page_token: Optional[str] = None
    next_page_token: Optional[str] = None


class SipProvenanceManifest(BaseModel):
    """Reproducibility manifest for an Alpaca historical SIP retrieval."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_id: str
    provider: str = "alpaca"
    endpoint: str = "https://data.alpaca.markets/v2/stocks/{symbol}/bars"
    symbol: str
    feed_requested: str = "sip"
    feed_response_provenance: str = "UNVERIFIED"
    provenance_basis: ProvenanceBasis = ProvenanceBasis.UNVERIFIED
    timeframe: str = "1Min"
    adjustment: str = "raw"
    asof: Optional[str] = None
    requested_start_utc: str
    requested_end_utc: str
    retrieval_timestamp_utc: str
    page_count: int
    pages: List[SipPageMetadata]
    composite_raw_payload_sha256: str
    canonical_bars_sha256: str
    record_count: int
    first_bar_timestamp_utc: Optional[str] = None
    last_bar_timestamp_utc: Optional[str] = None
    git_commit_sha: str
    git_dirty: bool
    schema_version: str = "1.0.0"
    source_qualification_status: SourceQualificationStatus
    vwap_authority_status: VwapAuthorityStatus
    source_contract_provider: str = OFFICIAL_CONTRACT_PROVIDER
    source_contract_feed: str = OFFICIAL_CONTRACT_FEED
    source_contract_references: List[str] = Field(
        default_factory=lambda: list(OFFICIAL_CONTRACT_REFERENCES)
    )
    source_contract_recorded_at_utc: str = OFFICIAL_CONTRACT_RECORDED_AT_UTC
    source_contract_semantics: str = OFFICIAL_CONTRACT_SEMANTICS
    warnings: List[str] = Field(default_factory=list)
    failure_reason: Optional[str] = None
    governance_disclaimer: str = (
        "DATA_SOURCE_TECHNICALLY_QUALIFIED is an infrastructural data qualification only. "
        "It confers ZERO strategy admission, ZERO candidate promotion, ZERO backtesting authorization, "
        "NO HYP_003 creation, and ZERO trading/capital authority."
    )


class SourceQualificationReport(BaseModel):
    """Complete qualification report emitted by the qualification engine."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    request_contract_status: QualificationCheckStatus
    network_access_status: QualificationCheckStatus
    data_integrity_status: QualificationCheckStatus
    provider_provenance_status: QualificationCheckStatus
    overall_status: SourceQualificationStatus
    vwap_authority_status: VwapAuthorityStatus
    manifest: SipProvenanceManifest
    findings: List[QualityFinding]
    bars_count: int
