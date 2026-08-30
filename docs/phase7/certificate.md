# Phase 7: Validation Certificate Ingestion & Revocation Specification

## 1. Overview & Trust Root
The `ValidationCertificate` is a read-only imported artifact in Phase 7 representing a cryptographically signed and verified certification from Phase 6.

### Content Integrity vs. Issuer Authenticity
$$\boxed{\text{Content Integrity (SHA-256 Hashes)} \neq \text{Issuer Authenticity (Cryptographic Signature)}}$$
* **Content Integrity**: Proves that the decision and evidence payloads have not been tampered with.
* **Issuer Authenticity**: Proves that the certificate was authorized and signed by a trusted system authority key (e.g. `ACASH_RESEARCH_AUTHORITY_V1`).

Phase 7 **NEVER** mutates, weakens, or recreates Phase 6 `ValidationReport` instances.

---

## 2. Validation Certificate Schema

```python
class ValidationCertificate(BaseModel):
    """Immutable certificate ingested from Phase 6 Statistical Validation Gate."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    certificate_id: str = Field(description="Unique deterministic certificate identifier.")
    validation_id: str = Field(description="Phase 6 validation report identifier.")
    strategy_id: str = Field(description="Target strategy identifier.")
    hypothesis_id: str = Field(description="Registered hypothesis specification identifier.")
    verdict: ValidationVerdict = Field(description="Must be PASS_TRADEABLE_ALPHA.")
    
    # Cryptographic Lineage Digests
    decision_digest: str = Field(pattern=r"^[a-f0-9]{64}$", description="Phase 6 decision digest.")
    evidence_digest: str = Field(pattern=r"^[a-f0-9]{64}$", description="Phase 6 evidence digest.")
    source_report_hash: str = Field(pattern=r"^[a-f0-9]{64}$", description="SHA-256 hash of the complete Phase 6 JSON report.")
    
    # Issuer Trust Root & Digital Signature
    issuer_id: str = Field(description="Authorized issuing authority identifier (e.g. 'ACASH_GOVERNANCE_GATE_6').")
    issuer_public_key_id: str = Field(description="Key ID of the issuing authority.")
    signature_algorithm: str = Field(default="ED25519_SHA512", description="Cryptographic signature algorithm.")
    certificate_signature: str = Field(description="Digital signature over (certificate_id + decision_digest + evidence_digest).")
    
    methodology_version: str = Field(description="Phase 6 governance methodology version (e.g. 'v1.0.0').")
    created_at: datetime = Field(description="UTC timestamp when certificate was issued.")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration timestamp for certificate validity.")
```

---

## 3. Append-Only Certificate Revocation Model

Certificates are **immutable** and are never modified in place. Revocations are emitted as append-only, signed `CertificateRevocationEvent` records:

```python
class CertificateRevocationEvent(BaseModel):
    """Immutable forensic event declaring a ValidationCertificate revoked."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    revocation_id: str = Field(description="Unique deterministic revocation event ID.")
    certificate_id: str = Field(description="Target ValidationCertificate ID being revoked.")
    strategy_id: str = Field(description="Target strategy identifier.")
    revoked_at: datetime = Field(description="UTC timestamp of revocation.")
    
    reason: str = Field(description="Forensic reason for revocation (e.g. 'DATA_LEAK_DISCOVERED', 'REGIME_BREAK').")
    actor: str = Field(description="Entity issuing revocation (e.g. 'RISK_COMMITTEE_CHAIR', 'AUTO_HEALTH_AUDITOR').")
    actor_public_key_id: str = Field(description="Public key ID of the revoking authority.")
    revocation_signature: str = Field(description="Digital signature of the revoking actor.")
    
    revocation_digest: str = Field(pattern=r"^[a-f0-9]{64}$", description="SHA-256 hash of canonical revocation record.")
```

---

## 4. Ingestion Validation Invariants
To be admitted into Phase 7, a certificate must satisfy all 6 admission criteria:
1. `verdict == ValidationVerdict.PASS_TRADEABLE_ALPHA`.
2. `decision_digest` and `evidence_digest` match the computed hashes of the Phase 6 payload.
3. `certificate_signature` verifies successfully against the `issuer_public_key_id`.
4. `methodology_version` is actively supported by the execution runtime.
5. `expires_at` is either `None` or `utc_now() <= expires_at`.
6. No matching `CertificateRevocationEvent` exists in the append-only revocation ledger.
