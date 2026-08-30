# Phase 7: Validation Certificate Ingestion & Revocation Specification

## 1. Overview & Trust Root
The `ValidationCertificate` is a read-only imported artifact in Phase 7 representing a cryptographically signed and verified certification from Phase 6.

### Content Integrity vs. Issuer Authenticity
$$\boxed{\text{Content Integrity (SHA-256 Hashes)} \neq \text{Issuer Authenticity (Cryptographic Signature)}}$$
* **Content Integrity**: Proves that the decision and evidence payloads have not been tampered with.
* **Issuer Authenticity**: Proves that the certificate was authorized and signed by a trusted system authority key (e.g. `ACASH_RESEARCH_AUTHORITY_V1`).

Phase 7 **NEVER** mutates, weakens, or recreates Phase 6 `ValidationReport` instances.

All signature verification in Phase 7 uses **real Ed25519** (RFC 8032) via a mandatory `Ed25519TrustStore`. There is no optional bypass path and no SHA256(message + secret) emulation.

---

## 2. Validation Certificate Schema

```python
class ValidationCertificate(BaseModel):
    """Immutable certificate ingested from Phase 6 Statistical Validation Gate."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    certificate_id: str
    validation_id: str
    strategy_id: str
    hypothesis_id: str
    verdict: ValidationGateVerdict  # Must be PASS_TRADEABLE_ALPHA

    decision_digest: str            # SHA-256
    evidence_digest: str            # SHA-256
    source_report_hash: str         # SHA-256

    issuer_id: str
    issuer_public_key_id: str       # Must resolve in Ed25519TrustStore
    signature_algorithm: Literal["Ed25519"] = "Ed25519"
    certificate_signature: str      # Base64 Ed25519 over canonical payload

    methodology_version: str
    created_at: datetime
    expires_at: Optional[datetime] = None  # None = no expiry
```

Canonical signing bytes are produced by `ValidationCertificate.compute_canonical_payload_bytes()`.

---

## 3. Ed25519TrustStore Key Validity

```python
class Ed25519TrustStoreEntry(BaseModel):
    key_id: str
    issuer_id: str
    public_key_b64: str             # Raw 32-byte Ed25519 public key, base64
    valid_from: datetime
    valid_until: Optional[datetime] = None  # None = key does not expire
    status: TrustStoreEntryStatus   # ACTIVE | ROTATED | REVOKED
```

Policy:
- `valid_until=None` means the key does not expire.
- Verification evaluates key validity at the relevant signing/verification time (`at_time`), not only current status.
- `REVOKED` keys fail closed for all verification attempts.
- `ROTATED` keys remain verifiable for historical signatures when `at_time` falls within `valid_from..valid_until`.

---

## 4. Append-Only Certificate Revocation Model

Certificates are **immutable** and are never modified in place. Revocations are emitted as append-only, signed `CertificateRevocationEvent` records:

```python
class CertificateRevocationEvent(BaseModel):
    revocation_id: str
    certificate_id: str
    strategy_id: str                # Must match target certificate.strategy_id
    revoked_at: datetime
    reason: str
    actor: str
    actor_public_key_id: str        # Must resolve in Ed25519TrustStore
    revocation_signature: str       # Base64 Ed25519 over canonical payload
    revocation_digest: str          # SHA-256 of canonical payload
```

Revocation verification is **not** reduced to `certificate_id` matching alone. The admission service verifies:
1. `revocation.certificate_id == certificate.certificate_id`
2. `revocation.strategy_id == certificate.strategy_id`
3. `revocation_digest` matches canonical payload
4. Ed25519 signature via TrustStore at `revoked_at`
5. `revoked_at` is not in the future relative to verification time

---

## 5. Ingestion Validation Invariants

To be admitted into Phase 7, a certificate must satisfy all criteria:
1. `verdict == PASS_TRADEABLE_ALPHA`.
2. Certificate not expired at verification time.
3. No valid, fully verified matching revocation event in the append-only ledger.
4. `signature_algorithm == "Ed25519"`.
5. `issuer_public_key_id` resolves in `Ed25519TrustStore` at `certificate.created_at`.
6. `certificate.issuer_id` matches TrustStore entry `issuer_id`.
7. `certificate_signature` verifies via `trust_store.verify(...)`.

There is no fallback verification path when TrustStore verification fails.
