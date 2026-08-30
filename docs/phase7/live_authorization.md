# Phase 7: Live Authorization Specification & State Machine

## 1. Overview & Separation of Concerns
A `LiveAuthorization` is a dynamic, state-managed token granting permission to allocate capital under bounded operational constraints.

```text
ValidationCertificate = "This strategy meets historical research standards."
LiveAuthorization     = "This strategy may trade up to $50,000 notional on Venue X with 2.5% max daily loss."
```

### Schema vs. Service Authority
The Pydantic schema **may construct any `AuthorizationStatus`** for serialization and deserialization. The schema does **not** enforce lifecycle policy.

**INVARIANT:** `ACTIVE` LiveAuthorization MUST only be emitted by the issuance/transition service (`issue_live_authorization`, `apply_approval`, `reactivate_authorization`). Application code must not mint `ACTIVE` authorizations outside these paths.

There are no `__init__` or `model_post_init` constructor hacks blocking `ACTIVE` at schema level — the service layer is the sole authority.

---

## 2. Authorization Lifecycle State Machine

```text
       ┌──────────┐
       │  DRAFT   │
       └────┬─────┘
            │ submit_for_approval()
            ▼
┌───────────────────────┐
│   PENDING_APPROVAL    │
└───────────┬───────────┘
            │ apply_approval() until quorum
            ▼
┌───────────────────────┐
│        ACTIVE         │
└─────┬───────────┬─────┘
      │           │
      │ suspend   │ revoke / expire
      ▼           ▼
┌───────────┐ ┌───────────┐ ┌───────────┐
│ SUSPENDED │ │  REVOKED  │ │  EXPIRED  │
└─────┬─────┘ └───────────┘ └───────────┘
      │           Terminal      Terminal
      │ reactivate_authorization()
      │ (same N-of-M quorum as issuance)
      ▼
    ACTIVE
```

### State Definitions
1. `DRAFT`: Proposed operational limits. No orders permitted.
2. `PENDING_APPROVAL`: Awaiting multi-sig quorum. No orders permitted.
3. `ACTIVE`: Quorum satisfied. Orders permitted within bounds.
4. `SUSPENDED`: Halted by kill switch or operator. No new orders.
5. `REVOKED`: Permanently invalidated (Terminal).
6. `EXPIRED`: Past `expires_at` (Terminal).

### Transition Service Functions (Sole Authority)
| Function | Valid From | Valid To |
| :--- | :--- | :--- |
| `create_draft_authorization()` | — | `DRAFT` |
| `submit_for_approval()` | `DRAFT` | `PENDING_APPROVAL` |
| `apply_approval()` | `PENDING_APPROVAL` | `PENDING_APPROVAL` or `ACTIVE` |
| `issue_live_authorization()` | — | `PENDING_APPROVAL` or `ACTIVE` |
| `suspend_authorization()` | `ACTIVE` | `SUSPENDED` |
| `reactivate_authorization()` | `SUSPENDED` | `ACTIVE` |
| `revoke_authorization()` | non-terminal | `REVOKED` |
| `expire_authorization()` | `ACTIVE` (past expiry) | `EXPIRED` |

Invalid transitions raise `PreLiveRiskAdmissionError`. Each function returns a **new frozen** `LiveAuthorization`; objects are never mutated in place.

---

## 3. Multi-Sig Issuance Quorum

```python
class AuthorizationApproval(BaseModel):
    approver_id: str
    public_key_id: str              # Ed25519TrustStore key ID
    role: ApproverRole
    authorization_id: str           # Replay protection binding
    approved_at: datetime
    approval_signature: str         # Ed25519 over canonical payload
    approval_digest: str            # SHA-256 of canonical payload

class LiveAuthorization(BaseModel):
    required_approvals: int         # Minimum N for ACTIVE
    approvals: Tuple[AuthorizationApproval, ...]
    authorization_digest: str       # SHA-256 of params + sorted approval_digests
```

Issuance invariant:
$$|\text{verified approvals}| \ge N_{\text{required}} \implies \text{ACTIVE}$$

Each approval is verified via mandatory `Ed25519TrustStore`. Duplicate `approver_id` or `public_key_id` values are rejected.

---

## 4. Reactivation Quorum (Phase 7 v1)

Reactivation uses the **same N-of-M quorum as original issuance**:

$$ \boxed{\text{Reactivation Quorum} = \text{Issuance Quorum}} $$

There is no single Risk Officer signature bypass.

```python
class AuthorizationReactivationApproval(BaseModel):
    approver_id: str
    public_key_id: str
    role: ApproverRole
    reactivation_id: str            # Replay protection
    authorization_id: str
    approved_at: datetime
    approval_signature: str
    approval_digest: str

class AuthorizationReactivationEvent(BaseModel):
    reactivation_id: str
    authorization_id: str
    strategy_id: str
    reactivated_at: datetime
    root_cause_summary: str         # Required audited root cause
    required_approvals: int         # Must equal LiveAuthorization.required_approvals
    approvals: Tuple[AuthorizationReactivationApproval, ...]
    reactivation_digest: str
```

### No Auto-Reactivation on Reboot
> Process restarts, container reboots, or server crashes must **NEVER** automatically transition `SUSPENDED` → `ACTIVE`.

Reactivation requires a signed `AuthorizationReactivationEvent` with full quorum verification via TrustStore.

---

## 5. Service API Summary

```python
verify_validation_certificate(certificate, trust_store, revocation_events=(), current_utc=None)
create_draft_authorization(certificate, trust_store, ...)
issue_live_authorization(certificate, trust_store, approvals, required_approvals, ...)
submit_for_approval(auth)
apply_approval(auth, approval, trust_store)
suspend_authorization(auth, reason, actor_id)
reactivate_authorization(auth, event, trust_store)
revoke_authorization(auth, reason, actor_id)
expire_authorization(auth, current_utc)
```

All cryptographic verification requires `Ed25519TrustStore`. There is no `trusted_public_keys` compatibility path.
