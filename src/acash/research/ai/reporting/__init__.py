"""ACASH Section 33 Automated Research Report Generator (Phase 14, Slice 4).

Deterministic, offline, post-validation summarizer that renders audit-compliant
Section 33 research reports strictly from sealed ACASH evidence, and grounds
every numeric claim through the EvidenceGroundingVerifier.

INVARIANTS:
- EvidenceGroundingVerifier is the SINGLE AUTHORITY over report numeric claims.
- Reports are REPORTED summaries with zero evidential, qualification, trading,
  or capital authority.
- No backtest execution, no statistical recomputation, no market data, no
  broker/execution imports, no network, and no LLM inference.
"""

from acash.research.ai.reporting.citation_verifier import (
    EvidenceChainStatus,
    EvidenceGroundingVerifier,
    GroundingVerificationResult,
    VerifiedClaim,
    validate_evidence_chain,
)
from acash.research.ai.reporting.generator import (
    OMITTED_MARKER,
    Section33Report,
    Section33ReportGenerator,
)

__all__ = [
    # Verifier (single authority over report numeric claims)
    "EvidenceGroundingVerifier",
    "GroundingVerificationResult",
    "VerifiedClaim",
    "EvidenceChainStatus",
    "validate_evidence_chain",
    # Generator
    "Section33ReportGenerator",
    "Section33Report",
    "OMITTED_MARKER",
]