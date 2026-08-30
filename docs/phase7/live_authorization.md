# Phase 7: Live Authorization Specification

## 1. Overview & Separation of Concerns
While a `ValidationCertificate` certifies statistical quality, a `LiveAuthorization` grants permission to allocate capital under explicit, dynamic operational constraints.

```text
ValidationCertificate = "This strategy meets research standards."
LiveAuthorization     = "This strategy may trade up to $50,000 notional on Venue X with 2.5% max daily loss."
```

---

## 2. Live Authorization Schema

```python
class LiveAuthorization(BaseModel):
    """Authoritative token granting capital allocation and operational boundaries."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    authorization_id: str = Field(description="Unique deterministic authorization identifier.")
    certificate_id: str = Field(description="Linked ValidationCertificate identifier.")
    strategy_id: str = Field(description="Target strategy identifier.")
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
    
    authorization_digest: str = Field(pattern=r"^[a-f0-9]{64}$", description="SHA-256 hash of canonical authorization parameters.")
```

---

## 3. Pre-Live Risk Admission Checks
Before generating a `LiveAuthorization`, the Pre-Live Risk Engine evaluates:
1. **Total Firm Sizing Capacity**: Adding `max_notional` does not breach global firm risk limits.
2. **Correlation & Overlap**: Strategy is not collinear with an already active live strategy sharing liquidity.
3. **Connectivity & Latency**: Target venue latency and heartbeat health are nominal.
