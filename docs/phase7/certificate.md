# Phase 7: Validation Certificate Ingestion Specification

## 1. Overview & Core Contract
The `ValidationCertificate` is a read-only imported artifact in Phase 7 representing a cryptographically sealed certification from Phase 6.

Phase 7 **NEVER** mutates, weakens, or recreates Phase 6 `ValidationReport` instances.

---

## 2. Certificate Schema

```python
class ValidationCertificate(BaseModel):
    """Immutable certificate ingested from Phase 6 Statistical Validation Gate."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    certificate_id: str = Field(description="Unique deterministic certificate identifier.")
    validation_id: str = Field(description="Phase 6 validation report identifier.")
    strategy_id: str = Field(description="Target strategy identifier.")
    hypothesis_id: str = Field(description="Registered hypothesis specification identifier.")
    verdict: ValidationVerdict = Field(description="Must be PASS_TRADEABLE_ALPHA.")
    decision_digest: str = Field(pattern=r"^[a-f0-9]{64}$", description="Phase 6 decision digest.")
    evidence_digest: str = Field(pattern=r"^[a-f0-9]{64}$", description="Phase 6 evidence digest.")
    methodology_version: str = Field(description="Phase 6 governance methodology version (e.g. 'v1.0.0').")
    created_at: datetime = Field(description="UTC timestamp when certificate was issued.")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration timestamp for certificate validity.")
    is_revoked: bool = Field(default=False, description="Manual or automated revocation flag.")
    source_report_hash: str = Field(pattern=r"^[a-f0-9]{64}$", description="SHA-256 hash of the complete Phase 6 JSON report.")
```

---

## 3. Ingestion Validation Invariants
To be accepted by Phase 7, a `ValidationCertificate` must satisfy all 5 admission conditions:
1. `verdict == ValidationVerdict.PASS_TRADEABLE_ALPHA`
2. `decision_digest` matches the SHA-256 hash of the sealed decision payload.
3. `evidence_digest` matches the SHA-256 hash of the sealed evidence payload.
4. `methodology_version` is actively supported by the execution environment.
5. `is_revoked == False` and (if specified) `utc_now() <= expires_at`.
