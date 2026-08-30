# Phase 7: Live Authorization Specification & State Machine

## 1. Overview & Separation of Concerns
A `LiveAuthorization` is a dynamic, state-managed token granting permission to allocate capital under bounded operational constraints.

```text
ValidationCertificate = "This strategy meets historical research standards."
LiveAuthorization     = "This strategy may trade up to $50,000 notional on Venue X with 2.5% max daily loss."
```

---

## 2. Authorization Lifecycle State Machine

```text
       ┌──────────┐
       │  DRAFT   │ (Created with proposed parameters)
       └────┬─────┘
            │
            ▼
┌───────────────────────┐
│   PENDING_APPROVAL    │ (Awaiting multi-sig risk officer approval)
└───────────┬───────────┘
            │
            ▼ (Approved & Signed)
┌───────────────────────┐
│        ACTIVE         │ (Strategy authorized to submit live orders)
└─────┬───────────┬─────┘
      │           │
      │ (Kill)    │ (Revoked)
      ▼           ▼
┌───────────┐ ┌───────────┐
│ SUSPENDED │ │  REVOKED  │ (Terminal)
└─────┬─────┘ └───────────┘
      │
      ▼ (Timeout reached)
┌───────────┐
│  EXPIRED  │ (Terminal)
└───────────┘
```

### State Definitions & Transition Rules
1. `DRAFT`: Proposed operational limits created by portfolio manager. No orders permitted.
2. `PENDING_APPROVAL`: Submitted to risk committee / automated risk gateway. No orders permitted.
3. `ACTIVE`: Cryptographically signed authorization token active. Orders permitted strictly within bounds.
4. `SUSPENDED`: Temporarily halted by a `KillSwitchEvent` or risk officer. No new orders permitted.
5. `REVOKED`: Permanently invalidated due to policy breach or model retirement (Terminal).
6. `EXPIRED`: Timestamp `utc_now() > expires_at` (Terminal).

### The "No Auto-Reactivation on Reboot" Invariant
> **"Process restarts, container reboots, or server crashes must NEVER automatically transition a `SUSPENDED` authorization back to `ACTIVE`."**
> 
> Reactivating a suspended strategy requires an explicit `AuthorizationReactivationEvent` signed by an authorized risk officer after root cause remediation.

---

## 3. Live Authorization Schema

```python
class AuthorizationStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"

class LiveAuthorization(BaseModel):
    """Authoritative token granting capital allocation and operational boundaries."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    authorization_id: str = Field(description="Unique deterministic authorization identifier.")
    certificate_id: str = Field(description="Linked ValidationCertificate identifier.")
    strategy_id: str = Field(description="Target strategy identifier.")
    status: AuthorizationStatus = Field(default=AuthorizationStatus.DRAFT, description="Current lifecycle state.")
    
    authorized_at: datetime = Field(description="UTC timestamp when authorization was granted.")
    expires_at: datetime = Field(description="Mandatory expiration timestamp for authorization validity.")
    
    # Operational Capital & Sizing Limits
    max_notional: Decimal = Field(gt=0, description="Maximum total notional exposure allowed across all positions.")
    max_position_size: Decimal = Field(gt=0, description="Maximum units allowed for any single position.")
    max_order_rate_per_minute: int = Field(gt=0, description="Throttling limit: max order submissions per minute.")
    
    # Loss & Drawdown Halts
    max_daily_loss_notional: Decimal = Field(gt=0, description="Max cumulative daily loss before automatic halt.")
    max_drawdown_pct: Decimal = Field(gt=0, le=100, description="Max peak-to-trough drawdown percentage before halt.")
    
    # Environmental Access
    allowed_venues: Tuple[str, ...] = Field(min_length=1, description="Whitelisted broker / exchange venues.")
    allowed_symbols: Tuple[str, ...] = Field(min_length=1, description="Whitelisted tradeable instrument symbols.")
    risk_policy_version: str = Field(description="Active pre-live risk policy version.")
    
    # Approver & Authority Signatures
    approver_id: str = Field(description="Risk officer or automated gateway ID.")
    approver_public_key_id: str = Field(description="Public key ID of approver.")
    authorization_signature: str = Field(description="Digital signature of approver over canonical parameters.")
    authorization_digest: str = Field(pattern=r"^[a-f0-9]{64}$", description="SHA-256 hash of canonical authorization parameters.")
```
