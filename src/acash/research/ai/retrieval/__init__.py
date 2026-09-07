"""ACASH Phase 14 Slice 2 — Source / Retrieval Layer.

RESEARCH INFRASTRUCTURE ONLY
----------------------------
This layer is an evidence-collection abstraction. It is NOT an alpha engine,
NOT a hypothesis, NOT a qualification engine, and NOT a trading system.

GOVERNANCE FIREWALL
-------------------
Dependency direction is one-way:

    SOURCE RETRIEVAL -> EVIDENCE RECORD -> LATER RESEARCH ANALYSIS

NOT:

    SOURCE RETRIEVAL -> STRATEGY QUALIFICATION -> TRADING

Nothing in this package can register hypotheses, qualify strategies, authorize
trading, access curated/quarantined research data, or mutate governance state.

EPISTEMIC MANDATE
-----------------
Retrieval success is evidence collection, never verification. Every retrieval
result carries an explicit epistemic classification (REPORTED by default) and
can never be classified VERIFIED at retrieval time.

CONTENT IDENTITY
----------------
RAW content hash and NORMALIZED content hash are always kept distinct.
Timestamps are metadata only and never affect content identity hashes.
"""

from acash.research.ai.retrieval.enums import (
    NormalizationPolicy,
    RetrievalMode,
    RetrievalStatus,
)
from acash.research.ai.retrieval.exceptions import (
    EvidenceStoreError,
    InvalidResultStateError,
    ProviderMisconfigurationError,
    RetrievalError,
    UnknownProviderError,
)
from acash.research.ai.retrieval.normalization import (
    compute_normalized_content_sha256,
    compute_raw_content_sha256,
    content_type_accepted,
    is_normalizable_content_type,
    normalize_text_content,
)
from acash.research.ai.retrieval.providers import (
    BaseSourceRetriever,
    FixtureContent,
    FixtureSourceRetriever,
    HttpSourceRetriever,
    SourceProviderRegistry,
)
from acash.research.ai.retrieval.schema import (
    EvidenceRecord,
    RetrievalProvenance,
    RetrievalRequest,
    RetrievalResult,
    SourceDescriptor,
    SourceRetrievalPolicy,
    utc_now_iso,
)
from acash.research.ai.retrieval.storage import (
    BaseEvidenceStore,
    InMemoryEvidenceStore,
)

__all__ = [
    # Enums
    "RetrievalStatus",
    "RetrievalMode",
    "NormalizationPolicy",
    # Exceptions
    "RetrievalError",
    "UnknownProviderError",
    "ProviderMisconfigurationError",
    "EvidenceStoreError",
    "InvalidResultStateError",
    # Normalization & Hashing
    "compute_raw_content_sha256",
    "compute_normalized_content_sha256",
    "normalize_text_content",
    "is_normalizable_content_type",
    "content_type_accepted",
    # Schemas
    "SourceRetrievalPolicy",
    "SourceDescriptor",
    "RetrievalRequest",
    "RetrievalProvenance",
    "RetrievalResult",
    "EvidenceRecord",
    "utc_now_iso",
    # Providers
    "BaseSourceRetriever",
    "SourceProviderRegistry",
    "FixtureContent",
    "FixtureSourceRetriever",
    "HttpSourceRetriever",
    # Storage
    "BaseEvidenceStore",
    "InMemoryEvidenceStore",
]