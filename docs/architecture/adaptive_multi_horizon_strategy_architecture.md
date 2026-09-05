# ACASH Phase 23: Adaptive Multi-Horizon Strategy & Market-Regime Architecture
## Autonomous Trading Infrastructure, Multi-Horizon Strategy Abstraction & Context-Aware Execution Governance

> **Document ID:** `ACASH-SPEC-PHASE23-ADAPTIVE-STRATEGY-v1.0`  
> **Related ADR:** `ADR-024` in [`docs/DECISIONS.md`](../DECISIONS.md)  
> **Status:** Approved Architectural Specification & Design Record (Phase 23 Baseline)  
> **Parent Governance:** `ADR-003` (Deterministic Hard Risk Engine), `ADR-022` (Market-Adaptive Governance), `ADR-023` (Strategy Admission Standard)  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed, Evidence > Belief)  
> **Date:** 2026-09-05  
> **Version:** 1.0.0  

---

> [!IMPORTANT]
> **STRICT GOVERNANCE BOUNDARY & CAPITAL RESTRICTIONS:**
> - **THIS SPECIFICATION DOES NOT GRANT LIVE TRADING AUTHORITY.**
> - **THIS SPECIFICATION DOES NOT CONNECT TO LIVE BROKERS OR TRANSMIT ORDERS.**
> - **CAPITAL ALLOCATION AUTHORITY REMAINS HARD-LOCKED AT $0.00.**
> - **GATE B GOVERNANCE AUTHORIZATION REMAINS PENDING REPAIR APPROVAL (REV 9).**
> - **ZERO RUNTIME MUTATION TO `src/acash/execution/` OR `src/acash/risk/`.**
> - **PHASE 23 IS AN ARCHITECTURAL DECISION & DOMAIN SPECIFICATION RECORD.**

---

## 1. Executive Summary & Core Decision (ADR-024)

### 1.1 What ACASH Is and Is Not
ACASH MUST NOT be defined by a singular trading style, holding period, or algorithmic trope:
- ACASH is **NOT** a "Scalping Bot".
- ACASH is **NOT** an "Intraday Bot".
- ACASH is **NOT** a "Swing Bot".
- ACASH is **NOT** a "Long-Term Trend Bot".
- ACASH is **NOT** a "Grid EA" or "Martingale System".

ACASH is:
$$\boxed{\mathbf{ACASH} = \mathbf{Risk\text{-}Controlled\ Autonomous\ Trading\ Infrastructure\ \&\ Decision\ Framework}}$$

Trading style, holding horizon, entry timing, and profit targets are **properties of individual Strategy modules at the Strategy Layer**, not the core identity of the ACASH platform.

### 1.2 The Verifier & Enforcer Invariant
$$\mathbf{Strategy\ Selection} \neq \mathbf{Trading\ Authorization} \quad \land \quad \mathbf{Signal} \neq \mathbf{Order} \quad \land \quad \mathbf{Target\ Position} \neq \mathbf{Immediate\ Execution}$$

The platform core provides common, immutable, sovereign capabilities:
1. **Risk Engine:** Strict deterministic gatekeeper; sole authority for risk admission, exposure bounds, and kill switches.
2. **Execution Engine:** Protocol-level order lifecycle state machine (`transition_order()` sole authority), venue routing, and fill processing.
3. **Reconciliation Engine:** Continuous 6-dimensional shadow ledger parity checking against external broker reality.
4. **Governance Layer:** Multi-sig cryptographic authorization, provenance verification, and operational gating.

No strategy—regardless of historical Sharpe, backtest profitability, or artificial intelligence complexity—possesses the authority to bypass these common layers.

---

## 2. Five-Layer Architectural Separation

The platform enforces strict separation between domain responsibilities:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       1. ACASH CORE INFRASTRUCTURE                      │
│   • Broker Protocols & Venue Normalization (MT5, Fix, REST)             │
│   • Bi-Temporal Point-in-Time Alpha Lake & Event Bus                    │
│   • 6-D Reconciliation & Shadow Accounting Ledger                       │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         2. STRATEGY LAYER (PLUGINS)                     │
│   • Strategy Families: Scalping, Intraday, Swing, Trend, Mean Rev       │
│   • Signal Generation & Price Structure Feature Consumption             │
│   • Proposes: Target Position + Risk Budget + Entry Schedule            │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      3. RISK LAYER (SOVEREIGN GATEKEEPER)               │
│   • Evaluates: Proposed Exposure, Stop Distance, Instrument Margin      │
│   • Evaluates: Cross-Asset Correlation, Portfolio Limits, Liquidity     │
│   • Emits: ALLOW (100%), REDUCE (Monotonic Scale-Down), or REJECT (0%)  │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     4. EXECUTION LAYER (AUTHORIZED MECHANISM)           │
│   • Ingests: Admitted OrderIntents only                                 │
│   • Enforces: Throttles, Venue Limits, Slippage Bounds                  │
│   • Transitions: INTENT → SUBMITTED → ACKNOWLEDGED → FILLED/CANCELLED   │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     5. GOVERNANCE LAYER (AUTHORITY BOUNDARY)            │
│   • Multi-Sig Quorum & Hardware PIV Ceremonies                          │
│   • Immutable Trust Store & Genesis Head Cryptographic Lineage          │
│   • Live Capital Authority & Maximum Drawdown Limits                    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Market-Situation Dependency & Contextual Pipeline

### 3.1 Contextual Decision Flow
Strategy activation and sizing conceptually depend on empirical market context, following a strictly uni-directional evaluation chain:

$$\begin{aligned}
\text{Market Data Stream} &\longrightarrow \text{Feature Engineering (Price Structure, Dynamics, Microstructure)} \\
&\longrightarrow \text{Market State Vector } \mathbf{s}(t) \\
&\longrightarrow \text{Regime Classification } \mathcal{R}_t \text{ with Confidence } c_t \\
&\longrightarrow \text{Strategy Eligibility \& Activation Filtering} \\
&\longrightarrow \text{Candidate Strategy Proposal: } (\text{TargetPosition}, \text{RiskBudget}, \text{EntrySchedule}) \\
&\longrightarrow \mathbf{Deterministic\ Risk\ Engine\ Evaluation\ (Admissibility\ Gate)} \\
&\longrightarrow \begin{cases} \mathbf{ADMIT} & \longrightarrow \text{OrderIntent Generation} \longrightarrow \text{Execution} \\ \mathbf{REJECT} & \longrightarrow \text{Zero Orders Transmitted (Fail-Closed)} \end{cases}
\end{aligned}$$

### 3.2 Strategy Suitability Matrix (Conceptual Archetypes)
Market regimes inform strategy eligibility; they do **not** dictate mechanical execution:

| Market Regime Context | Characteristic Dynamics | Eligible Strategy Archetypes | Ineligible / High-Risk Archetypes | Risk Engine Default Action |
| :--- | :--- | :--- | :--- | :--- |
| **TRENDING (Strong Directional)** | High directional velocity, low mean reversion | Trend Following, Breakout, Swing Momentum | Mean Reversion, Tight Range Grid | Scale-in via confirmation; trailing stops |
| **RANGING (Mean-Reverting)** | Low directional velocity, high boundary bounce | Statistical Mean Reversion, Boundary Scalp | Trend Following, Momentum Breakout | Tight stop distances; bounded targets |
| **BREAKOUT (Volatility Expansion)**| Sudden range expansion, volume spike | Volatility Breakout, Liquidity Momentum | Static Grid, Mean Reversion | Require slippage buffer; strict latency check |
| **HIGH VOLATILITY / DISLOCATION** | Elevated ATR, wide spreads, fat tails | Volatility Arbitrage, Capital Preservation | Large Notional Sizing, Tight Stop Scalping| Monotonic size reduction or **NO_TRADE** |
| **LOW LIQUIDITY / OFF-HOURS** | Wide bid-ask spread, thin book depth | Patient Limit Order Execution, Long Horizon | High-Frequency Scalping, Market Orders | Reject aggressive market orders |
| **UNCERTAIN / INSUFFICIENT DATA** | Ambiguous classification ($c_t < c_{\min}$) | Capital Preservation (**NO_TRADE**) | All Directional Strategies | **REJECT ALL PROPOSALS (Cash = 100%)** |

> [!CAUTION]
> **GOVERNANCE INVARIANT: MARKET REGIME NEVER OVERRULES RISK LIMITS**  
> Even if a strategy identifies a "perfect regime match" (e.g. 99% probability Trend regime), the Risk Engine maintains complete sovereign authority. If the proposed trade breaches portfolio margin, correlation ceilings, or daily loss limits, the trade is **UNCONDITIONALLY REJECTED**.

---

## 4. Position Model: Rejection of Fixed Capital Slices

### 4.1 Rejection of Global Fixed Slice Ratios
The core architecture **STRICTLY REJECTS** embedding arbitrary capital divisions as global engine policy:
- **Rejected:** Global hardcoded rules such as "divide capital into 3 fixed pieces (30% / 30% / 40%)".
- **Rejected:** Global hardcoded rules such as "always trade 25% initial, 25% second, 50% third".

These ratios are strategy-specific heuristics or historical trader preferences. Encoding them into the ACASH core engine would:
1. Couple the infrastructure to a single sizing methodology.
2. Violate risk-first principles by allocating capital based on percentage of wallet rather than distance to stop.
3. Obscure actual downside risk exposure.

### 4.2 The Four Pillars of Position Sizing
ACASH decouples position sizing into four mathematical abstractions:
1. **Target Position ($\text{TargetPosition}$):** The ultimate net position (units/notional) the strategy seeks to accumulate.
2. **Risk Budget ($\text{RiskBudget}$):** The maximum allowable currency loss ($) permitted for this trade idea.
3. **Entry Schedule ($\text{EntrySchedule}$):** The dynamic, condition-driven tranches through which the target position is accumulated.
4. **Dynamic Recalculation:** Re-evaluating cumulative portfolio risk before every individual tranche entry.

---

## 5. Target Position Abstraction

A Strategy does not emit raw order tickets. A Strategy emits a `TargetPositionProposal`:

$$\text{TargetPositionProposal} = \big(\text{StrategyID}, \text{Instrument}, \text{TargetUnits}, \text{TargetNotionalUSD}, \text{Direction}, \text{Horizon}, \text{ThesisID}\big)$$

- **Meaning:** Represents the strategy's desired final economic exposure if all entry conditions and thesis confirmations are satisfied.
- **Non-Immediacy:** Emitting a target of $+500\text{k EURUSD}$ does **NOT** mean sending a market order for 500k. It signifies the upper bound of intended accumulation.
- **Under-Consumption Permitted:** A strategy is never obligated to fill 100% of its target position. If the market reaches target profit or loses thesis confirmation early, remaining tranches are discarded.

---

## 6. Risk Budget Abstraction: Risk-First Position Sizing

### 6.1 The Fundamental Mathematical Relation
Capital allocation alone must **NEVER** determine risk. Position size must be derived from the explicit distance to invalidation (Stop Loss):

$$\text{Allowable Position Size (Units)} \le \frac{\text{Risk Budget (\USD)}}{\text{Stop Distance (Points)} \times \text{Point Value (\USD / Unit)}} \times \prod_k (1 - \text{Haircut}_k)$$

Where:
- $\text{Risk Budget (\USD)}$: The explicit dollar loss permitted for this trade (e.g. $1\%$ of equity = $\$30$ on a $\$3,000$ account).
- $\text{Stop Distance}$: Distance between proposed entry price and structural invalidation level:
  $$\Delta_{\text{stop}} = |\text{Entry Price} - \text{Stop Loss Price}|$$
- $\text{Haircut}_k$: Regulatory, broker margin, slippage, and volatility haircut discounts.

### 6.2 Illustrative Scenarios (Non-Normative)
| Account Equity | Strategy Risk Budget | Stop Distance | Derived Maximum Position Size | Implied Gross Leverage |
| :--- | :--- | :--- | :--- | :--- |
| $\$3,000$ | $\$30.00$ (1.0%) | 100 pips (1.0%) | $\approx \$3,000$ notional (0.03 lots) | $1.0\times$ |
| $\$3,000$ | $\$30.00$ (1.0%) | 200 pips (2.0%) | $\approx \$1,500$ notional (0.015 lots)| $0.5\times$ |
| $\$3,000$ | $\$30.00$ (1.0%) | 20 pips (0.2%) | $\approx \$15,000$ notional (0.15 lots)| $5.0\times$ (Subject to max leverage cap) |

> [!NOTE]
> The numbers above are purely illustrative to demonstrate the mathematical relationship. Production sizing is calculated dynamically by the Risk Engine using exact contract specifications, tick values, broker margin tiers, and portfolio exposure limits.

---

## 7. Entry Allocation & Scale-In Philosophy

### 7.1 Confirmation-Driven Pyramiding vs Blind Averaging Down

$$\boxed{\mathbf{CORE\ PHILOSOPHY:\ CONFIRMATION\text{-}DRIVEN\ PYRAMIDING\ >\ BLIND\ AVERAGING\ DOWN}}$$

```
A. CONFIRMATION-DRIVEN PYRAMIDING (ACASH Default):
   Signal Generated
          │
          ▼
   Initial Entry (e.g. 20-25% of Target)
          │
          ▼
   Market confirms thesis (Price moves favorably / Breakout confirmed)
          │
          ▼
   Adjust Stop to Breakeven / Trailing
          │
          ▼
   Add Second Tranche (e.g. 25-35% of Target)
          │
          ▼
   Market confirms continuation
          │
          ▼
   Add Final Tranche (e.g. 40-50% of Target)
          │
          ▼
   Target Reached OR Risk Limit Reached → STOP ADDING

-------------------------------------------------------------------------

B. BLIND AVERAGING DOWN (Strictly Banned as Core Default):
   Signal Generated → Initial Entry
          │
          ▼
   Price falls against position → BUY MORE
          │
          ▼
   Price falls further → BUY EVEN MORE
          │
          ▼
   (Accelerating loss curve & margin liquidation risk)
```

### 7.2 Invariants Governing Position Additions
1. **No Core Averaging Down:** The ACASH core engine will never automatically buy more simply because an asset became cheaper against an open position.
2. **Strict Strategy Admission for Non-Pyramiding Styles:** A strategy that employs dynamic mesh, grid, or statistical averaging-down must be explicitly declared as `StrategyStyle.GRID_PROGRESSION`, tested against catastrophic tail regimes, bounded by an absolute maximum loss cap, and admitted through the formal Phase 17 11-Gate Governance Standard.
3. **Stop Invalidation Invariance:** Adding to a winning position (pyramiding) must never increase total currency risk beyond the original authorized `RiskBudget`. As new tranches are added, stops on existing tranches must be trailed to lock in risk reduction.

---

## 8. Dynamic Risk Re-Calculation

Every proposed additional tranche MUST trigger a completely independent, fresh evaluation by the Risk Engine.

$$\text{RiskEvaluation}(t_k) = \mathcal{F}_{\text{Risk}}\Big(\mathbf{E}_{\text{current}}(t_k), \mathbf{O}_{\text{proposed}}(t_k), \Delta_{\text{stop}}(t_k), \mathbf{\Sigma}_{\text{portfolio}}, \mathcal{L}_{\text{market}}, \mathcal{C}_{\text{account}}\Big)$$

```
Current Portfolio Exposure
          +
Proposed Tranche Order
          +
Stop-Loss Invalidation Risk
          +
Cross-Asset Correlation Matrix (Σ)
          +
Portfolio Concentration Limits
          +
Market Spread & Depth Liquidity
          +
Account Balance & Margin Utilization
          │
          ▼
   DETERMINISTIC RISK ENGINE
          │
   ┌──────┴──────┐
   ▼             ▼
 ALLOW        REJECT (Tranche blocked; existing position retained or closed)
```

- **Zero Temporal Carryover:** An approval granted for Tranche 1 at $t_0$ confers **zero automatic authorization** for Tranche 2 at $t_1$.
- **Adverse State Changes:** If market volatility spikes, broker spread expands, or portfolio margin deteriorates between tranches, the Risk Engine rejects Tranche 2 without affecting Tranche 1.

---

## 9. Strategy & Horizon Abstraction (`ITradingStrategy`)

### 9.1 Conceptual Domain Interface
To prevent hardcoding holding periods (e.g. `holding_period = "SWING"`), the strategy abstraction decouples market analysis from execution timing:

```python
class ITradingStrategy(Protocol):
    """Sovereign interface contract for all ACASH strategy plugins."""

    @property
    def strategy_id(self) -> str: ...

    @property
    def strategy_version(self) -> str: ...

    @property
    def mechanism(self) -> StrategyMechanism: ...

    @property
    def style(self) -> StrategyStyle: ...

    @property
    def expected_horizon(self) -> StrategyHorizon: ...

    @property
    def eligible_regimes(self) -> Tuple[str, ...]: ...

    def evaluate_market_context(
        self,
        market_state: MarketStateVector,
        regime_estimate: RegimeClassificationEstimate,
    ) -> StrategySuitabilityAssessment:
        """Evaluate whether current market conditions warrant strategy engagement."""
        ...

    def propose_target_position(
        self,
        market_state: MarketStateVector,
        current_portfolio_exposure: Decimal,
    ) -> Optional[TargetPositionProposal]:
        """Propose desired aggregate position, risk budget request, and invalidation rules."""
        ...

    def propose_entry_schedule(
        self,
        target_proposal: TargetPositionProposal,
        market_state: MarketStateVector,
    ) -> EntrySchedulePlan:
        """Propose conditional tranche entry schedule (pyramiding confirmation rules)."""
        ...
```

### 9.2 Strategy Metadata Attributes
Every strategy plugin must formally declare its operating parameters in its `StrategyDefinition`:
- `strategy_id`: Deterministic unique identifier (e.g. `STRAT_FX_TREND_D1_001`).
- `expected_horizon`: `SCALPING` ($< 15\text{m}$), `INTRADAY` ($15\text{m} - 8\text{h}$), `SWING` ($1\text{d} - 5\text{d}$), `POSITION` ($> 1\text{w}$).
- `eligible_regimes`: Tuple of supported regime labels (e.g. `("TRENDING_BULL", "TRENDING_BEAR")`).
- `invalidation_model`: Explicit rule defining how Stop Loss and target positions are computed.
- `scale_in_policy`: Explicit policy (`CONFIRMATION_PYRAMID`, `SINGLE_TRANCHE`, `BOUNDED_GRID`).
- `max_gross_exposure_ratio`: Absolute cap on gross notional relative to allocated capital.

---

## 10. Market Regime Domain Model

### 10.1 Continuous Measurements vs Discrete Regimes
ACASH separates empirical measurements from contextual labels:
1. **`MarketStateVector`:** Continuous, non-discretized numerical measurements (returns, range/ATR, body/range ratio, wick asymmetry, realized volatility, spread bps).
2. **`RegimeClassificationEstimate`:** Probabilistic interpretation assigning confidence scores to discrete operating regimes.

### 10.2 Canonical Regime Taxonomy
```python
class CanonicalMarketRegime(str, Enum):
    """Standardized institutional regime taxonomy."""
    TREND_STRONG = "TREND_STRONG"          # High directional persistence, expanding volume
    TREND_WEAK = "TREND_WEAK"              # Mild drift, vulnerable to chop
    RANGE_TIGHT = "RANGE_TIGHT"            # Low volatility, mean-reverting boundaries
    RANGE_EXPANDED = "RANGE_EXPANDED"      # High volatility oscillations without trend
    BREAKOUT_IMMINENT = "BREAKOUT_IMMINENT"# Volatility compression (coiling)
    BREAKOUT_ACTIVE = "BREAKOUT_ACTIVE"    # Rapid directional range expansion
    HIGH_VOLATILITY_TAIL = "HIGH_VOL_TAIL" # Extreme tail risk, event dislocation
    LOW_LIQUIDITY = "LOW_LIQUIDITY"        # Illiquid book, wide spreads
    UNCERTAIN = "UNCERTAIN"                # Conflicting signals, low classifier confidence
    NO_TRADE = "NO_TRADE"                  # Explicit operational lockout
```

### 10.3 The Epistemic Authority Rule
- **Observation Only:** A regime tag is purely an environmental descriptor.
- **Zero Inherent Authority:** A regime classification has **zero authority** to open, close, or modify orders directly.
- **Uncertainty Fail-Closed:** If `confidence_score < min_regime_confidence` $\to$ status is `INSUFFICIENT_EVIDENCE` $\to$ default to `NO_TRADE`.

---

## 11. Strategy Tournament & Empirical Selection

ACASH rejects developer favoritism and qualitative dogmatism. Strategy selection is governed by the **Strategy Tournament Pipeline**:

```
1. Formal Strategy Specification (Gate 0–1 Definition & Economic Hypothesis)
                          │
                          ▼
2. Tick-Aware Event Backtest (Phase 5 Realistic Simulation & Slippage Models)
                          │
                          ▼
3. Out-of-Sample & Walk-Forward Matrix (Phase 6 CSCV, White's Reality Check, PBO)
                          │
                          ▼
4. Forward Demo & Shadow Execution (Phase 12 Broker Reality & Latency Tracking)
                          │
                          ▼
5. Strategy Tournament Evaluation (Phase 18 Multi-Model Competition & Regimes)
                          │
                          ▼
6. 11-Gate Strategy Admission Standard (Phase 17 Governance Certification)
                          │
                          ▼
7. Bounded Risk-Based Capital Allocation (Phase 21 Mathematical Solvers)
                          │
                          ▼
8. Authoritative Production Deployment (Live Micro-Capital Execution)
```

### 11.1 Addressing the Current System Baseline
- **Current Observation:** The current ACASH execution and data architecture (MT5 demo telemetry, bar-level event processing, 6-D reconciliation, network latency) provides a natural initial substrate for **Swing and Medium-Horizon Strategies**.
- **Non-Permanent Invariant:** This operational baseline is an observation of current maturity, **NOT an architectural ceiling**. Scalping and ultra-low-latency execution require specialized tick infrastructure, queue-position modeling, and co-located execution gateways (Phase 5/12 extensions). ACASH core must remain architecturally compatible with both fast and slow horizons.

---

## 12. Auditability, Determinism & Decision Memory

Every strategy proposal, regime assessment, and risk decision must be fully auditable and reproducible:
1. **Deterministic Inputs:** Every decision takes explicit `MarketStateVector` instances with verifiable cryptographic SHA-256 data provenance.
2. **Replayable Decisions:** Given the same market state vector and risk configuration, the Strategy and Risk Engine must emit bit-for-bit identical outputs.
3. **Decision Audit Ledger:** Every target position proposal and risk evaluation report is appended to the sovereign immutable decision log (`var/audit/decision_ledger.jsonl`), linking:
   - `strategy_id` and `strategy_version`
   - `market_state_digest`
   - `regime_classification_digest`
   - `risk_evaluation_digest`
   - `verdict` (`ALLOW`, `REDUCE`, `REJECT`)
   - `timestamp_utc`

---

## 13. Governance Compatibility & Invariants

Phase 23 strictly upholds all foundational ACASH governance invariants:

| Governance Principle | Phase 23 Architectural Binding |
| :--- | :--- |
| **Strategy $\neq$ Authority** | Strategies propose target positions; only the Risk Engine admits, and only Governance authorizes. |
| **Signal $\neq$ Order** | A market signal is a data feature; it never directly generates broker network packets. |
| **Target $\neq$ Execution** | Target positions define maximum exposure bounds; actual execution is governed by tranche schedules. |
| **Paper $\neq$ Live** | Simulation and paper results are evidence inputs; they confer zero automatic live capital authority. |
| **Risk Approval $\neq$ Live Order** | Risk Engine admission confirms risk safety; order transmission requires active, unrevoked Governance Tokens. |
| **Fail-Closed Default** | Ambiguous market data, missing regime models, or unverified risk states default immediately to `Cash = 100% (NO_TRADE)`. |

---

## 14. Implementation-Readiness & Architectural Delta

To preserve repository integrity and avoid premature code mutations during governance repair, Phase 23 status is categorized with institutional transparency:

### 14.1 Status Classification Ledger
- **Architectural Decision:** **COMPLETE / APPROVED (ADR-024 Recorded)**
- **Proposed Design & Domain Models:** **COMPLETE / SPECIFIED (This Document)**
- **Production Source Code:** **NOT YET IMPLEMENTED (Zero mutations in Phase 23)**
- **Unit & Integration Tests:** **NOT YET IMPLEMENTED (Deferred to Implementation Phase)**
- **Live Trading Authority:** **STRICTLY BLOCKED ($0.00 Live Capital)**

### 14.2 Future Design Delta & Files Requiring Modification
When Phase 23 advances from Architectural Specification to Implementation:

| Component | Target File | Proposed Implementation Delta |
| :--- | :--- | :--- |
| **Strategy Domain Contracts** | `src/acash/strategy/schema.py` | Add `TargetPositionProposal`, `RiskBudgetSpec`, `EntrySchedulePlan`, `TrancheSpec`, `CanonicalMarketRegime`. |
| **Strategy Interface Protocol**| `src/acash/strategy/interface.py` | Implement `ITradingStrategy` protocol defining `propose_target_position` and `propose_entry_schedule`. |
| **Risk Engine Incremental Gate**| `src/acash/risk/risk_engine.py` | Add `evaluate_incremental_tranche()` checking stop-distance risk and portfolio limits per tranche. |
| **Adversarial Test Suite** | `tests/unit/strategy/test_adaptive_architecture.py`| Implement boundary tests covering regime mismatch, confirmation pyramiding, averaging-down rejection, and dynamic recalculation. |

---

## 15. Canonical Architectural Statement

```markdown
════════════════════════════════════════════════════════════════════════════════
            ACASH PHASE 23 CANONICAL ARCHITECTURAL STATEMENT
════════════════════════════════════════════════════════════════════════════════

1. ACASH is a risk-controlled autonomous trading infrastructure capable of
   supporting multiple trading horizons and strategy families.

2. Scalping, Intraday, Swing, Long-term, Trend Following, Mean Reversion,
   Breakout, and Momentum belong exclusively to the Strategy Layer.

3. The appropriate strategy depends dynamically on market situation and regime.

4. The Deterministic Risk Engine remains the sole common enforcement boundary
   for all strategies across all horizons.

5. Execution performs only actions admitted by Risk and authorized by Governance.

6. ACASH must NOT be architecturally locked to any single trading style before
   empirical research, backtesting, walk-forward validation, paper trading,
   tournament evaluation, and risk admission have been formally completed.
════════════════════════════════════════════════════════════════════════════════
```
