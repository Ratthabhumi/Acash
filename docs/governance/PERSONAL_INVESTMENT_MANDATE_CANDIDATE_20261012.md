# ACASH — Personal Investment Mandate Candidate (Draft / Not Ratified)

**Document ID:** `DOC-ACASH-MANDATE-CANDIDATE-20261012`  
**Classification:** Investment Mandate Specification & Parameter Reconciliation  
**Status:** `DRAFT_NOT_RATIFIED` (Operator Working Hypothesis — Zero Live Authority)  
**Governing Authority:** `AGENTS.md` (Strict Fail-Closed, Single Canonical Authority, Zero Unverified Claims)  
**Effective As-Of:** 2026-10-12  
**Supersedes:** Parameter defaults in `DOC-ACASH-PERSONAL-QUANT-ARCHITECTURE-20261012` §4  

---

## 1. Context & Reconciliation of Operator Planning Inputs

The system owner has provided specific planning parameters for the Personal Systematic Investment System. This document reconciles those factual operator statements against the unapproved defaults previously drafted in PR #22.

### Parameter Reconciliation Matrix
| Parameter Field | PR #22 Draft Default | Actual Operator Statement | Reconciled Canonical Status | Governance Meaning |
| :--- | :--- | :--- | :--- | :--- |
| **Capital Planning (USD)** | `0.00` | `$1,000` | `proposed_investable_capital_usd = 1000.00` | Planning & simulation scale; NOT live funding. |
| **Real Capital Authority (USD)** | `0.00` | `$0.00` | `real_capital_authority_usd = 0.00` | **STRICT BOUNDARY**: Zero live capital accessible. |
| **Simulated Research NAV (USD)** | N/A | `$1,000` | `simulated_research_nav_usd = 1000.00` | Denomination base for offline backtests and friction models. |
| **Max Tolerable Drawdown** | `20.0%` | `50.0%` | `max_tolerable_drawdown_pct = 50.0` | Peak-to-trough tolerance; NOT an automated stop order. |
| **Executable Drawdown Policy** | Hard cash floor @ 15% | Not specified | `executable_drawdown_policy = UNDECIDED` | Defensive circuit breaker rules are unratified. |
| **Annual Volatility Target** | `10.0%` | Not specified | `volatility_target_annual_pct = UNDECIDED` | Not approved by operator; cannot be assumed. |
| **Investment Horizon** | `10 years` | Not specified | `investment_horizon = UNKNOWN` | Unapproved assumption; pending operator confirmation. |
| **Reporting Currency** | `THB` | Not specified | `reporting_currency = UNDECIDED` | Primary working currency USD; THB secondary view. |
| **Emergency Cash Reserve** | `0.00` | Not specified | `emergency_cash_reserve = UNKNOWN` | Affordability cannot be inferred without cash buffer audit. |
| **Broker Selection** | Dime, InnovestX, IBKR | Interactive Brokers (IBKR) | `preferred_broker_candidate = IBKR`<br>`broker_account_verified = false`<br>`broker_execution_authority = false` | Target execution venue registered; live account unverified and execution disabled. |
| **Research Sleeve Allocation** | `10% - 30%` | Not specified | `active_strategy_real_allocation = 0.0` | 0% real capital to research sleeve until separate admission. |

---

## 2. Hard Governance Safeguards & Boundaries

1. **Risk Tolerance $\neq$ Capital Affordability**:
   - The operator's declared willingness to endure a 50% drawdown reflects psychological risk appetite, not an actuarial certification that a $500 loss will not cause personal financial distress.
   - Emergency liquid reserves outside ACASH remain `UNKNOWN`. ACASH will not authorize live execution without verified reserve isolation.

2. **Drawdown Tolerance $\neq$ Automated Stop-Loss**:
   - The 50% peak-to-trough drawdown threshold is an evaluation benchmark constraint, **NOT** an automated broker market/stop order trigger.
   - Stop orders do not guarantee execution at the specified level in gapping, illiquid, or halt conditions (e.g., overnight gaps, circuit breakers).

3. **Active Strategy Real Allocation = 0%**:
   - The architectural two-tier split (Core vs. Research Sleeve) described in `personal_quant_investment_architecture.md` is an illustrative framework.
   - Until an active strategy clears formal hypothesis preregistration, out-of-sample statistical gates, and explicit human authorization, `active_strategy_real_allocation` remains strictly **0.0%**.

4. **Currency Dual-View Policy**:
   - Global ETFs (VOO, BND, GLD, BIL) trade and clear in USD.
   - For an individual based in Thailand, portfolio wealth is subject to USD/THB exchange rate fluctuation.
   - The canonical simulation engine operates in **USD** (asset native currency) to avoid confounding strategy returns with currency drift. An informational **THB** view is computed using authoritative Bank of Thailand (BOT) daily fixing rates.

5. **Broker Reality Check (IBKR Fee Drag on $1,000 Capital)**:
   - Preferred Broker Candidate: **Interactive Brokers LLC (IBKR)**.
   - Pro Tiered Tariff: $0.0035/share, minimum $0.35/order, capped at 1.0% of order value.
   - Pro Fixed Tariff: $0.005/share, minimum $1.00/order, capped at 1.0% of order value.
   - On a $1,000 account rebalancing 4 ETFs with $50 order adjustments, 4 tickets at $0.35 = $1.40 per rebalance event (0.14% of NAV). If performed monthly, annual friction is ~1.68% before spreads, FX conversion, and wire fees.
   - A single $0.35 assumption does not account for exchange fees, clearing fees, FX conversion spreads (typically $2.00 minimum on IBKR), or Thai bank international transfer fees.

---

## 3. Candidate Mandate YAML Specification

```yaml
personal_investment_mandate_candidate:
  mandate_id: "MANDATE_CANDIDATE_20261012_USD1000"
  status: "DRAFT_NOT_RATIFIED"
  created_at_utc: "2026-10-12T00:00:00Z"
  
  capital_structure:
    simulated_research_nav_usd: 1000.00
    proposed_investable_capital_usd: 1000.00
    real_capital_authority_usd: 0.00
    emergency_cash_reserve_usd: "UNKNOWN"
    active_strategy_real_allocation_pct: 0.0
    
  risk_profile:
    max_tolerable_drawdown_pct: 50.0
    volatility_target_annual_pct: "UNDECIDED"
    executable_drawdown_policy: "UNDECIDED"
    hard_risk_off_threshold_pct: "UNDECIDED"
    
  temporal_and_currency:
    investment_horizon_years: "UNKNOWN"
    rebalance_frequency: "MONTHLY"
    research_primary_currency: "USD"
    reporting_currency: "UNDECIDED"
    secondary_reporting_currency: "THB"
    
  universe_scope:
    allowed_asset_classes:
      - "GLOBAL_EQUITY_ETFS"     # VOO
      - "FIXED_INCOME_ETFS"      # BND / AGG
      - "COMMODITIES_GOLD_ETFS"  # GLD / IAU
      - "CASH_EQUIVALENTS"       # BIL / US T-Bills
    direction_policy: "LONG_ONLY"
    leverage_ceiling: 1.00
    
  broker_configuration:
    preferred_broker_candidate: "IBKR"
    broker_account_verified: false
    broker_execution_authority: false
    fee_structure_candidate: "PRO_TIERED"
    minimum_commission_usd: 0.35
    maximum_commission_pct: 0.01

  governance:
    execution_authority: "ZERO_ORDER_READ_ONLY"
    operator_decision_channel: "DISCRETIONARY_HUMAN_CONFIRMATION"
```

---

## 4. Verification Checkpoint
- Implementation Status: **COMPLETE**
- Contract Enforcement: **STRICT FAIL-CLOSED**
- Authority Status: **DRAFT_NOT_RATIFIED**
- Real Capital: **$0.00**
- Preferred Broker: **IBKR (Candidate Only — Zero Order Authority)**
