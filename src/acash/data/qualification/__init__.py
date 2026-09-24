"""Historical SIP market data qualification package."""

from acash.data.qualification.client import (
    AlpacaAccessDeniedError,
    AlpacaAuthenticationError,
    AlpacaHistoricalSipClient,
    AlpacaRateLimitExceededError,
    SipContractViolationError,
    SipRetrievalResult,
)
from acash.data.qualification.hyp_009_daily_client import (
    HYP009AlpacaClient,
    Hyp009PreNetworkGuard,
    Hyp009RetrievalResult,
    assert_split_raw_alignment,
)

from acash.data.qualification.engine import HistoricalSipQualificationEngine
from acash.data.qualification.guard import (
    FifteenMinuteAccessGuard,
    ProtectedWindowViolationError,
)
from acash.data.qualification.manifest import (
    build_sip_provenance_manifest,
    compute_canonical_bars_sha256,
    compute_framed_composite_sha256,
    compute_page_sha256,
    save_evidence_package,
    serialize_manifest_to_json,
    verify_persisted_evidence_package,
)
from acash.data.qualification.models import (
    HistoricalSipBar,
    MarketDataFeed,
    PriceAdjustment,
    ProvenanceBasis,
    QualificationCheckStatus,
    QualityFinding,
    QualityRuleCode,
    QualitySeverity,
    SipPageMetadata,
    SipProvenanceManifest,
    SourceQualificationReport,
    SourceQualificationStatus,
    VwapAuthorityStatus,
)
from acash.data.qualification.session import (
    RthSessionBounds,
    VerifiedSessionSchedule,
)
from acash.data.qualification.validator import HistoricalBarValidator

__all__ = [
    "AlpacaAccessDeniedError",
    "AlpacaAuthenticationError",
    "AlpacaHistoricalSipClient",
    "HYP009AlpacaClient",
    "Hyp009PreNetworkGuard",
    "Hyp009RetrievalResult",
    "AlpacaRateLimitExceededError",
    "FifteenMinuteAccessGuard",
    "HistoricalBarValidator",
    "HistoricalSipBar",
    "HistoricalSipQualificationEngine",
    "MarketDataFeed",
    "PriceAdjustment",
    "ProtectedWindowViolationError",
    "ProvenanceBasis",
    "QualificationCheckStatus",
    "QualityFinding",
    "QualityRuleCode",
    "QualitySeverity",
    "RthSessionBounds",
    "SipContractViolationError",
    "SipPageMetadata",
    "SipProvenanceManifest",
    "SipRetrievalResult",
    "SourceQualificationReport",
    "SourceQualificationStatus",
    "VerifiedSessionSchedule",
    "VwapAuthorityStatus",
    "build_sip_provenance_manifest",
    "compute_canonical_bars_sha256",
    "compute_framed_composite_sha256",
    "compute_page_sha256",
    "save_evidence_package",
    "serialize_manifest_to_json",
    "verify_persisted_evidence_package",
    "assert_split_raw_alignment",
]
