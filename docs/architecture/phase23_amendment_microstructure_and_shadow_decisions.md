# ACASH PHASE 23 — AMENDMENT
# Market Microstructure, Order-Book Event Intelligence & Decision Learning

> **Document ID:** `ACASH-SPEC-PHASE23-AMEND-MICROSTRUCTURE-v1.0`  
> **Related ADR:** `ADR-024` (Amendment Addendum) & `ADR-025` in [`docs/DECISIONS.md`](../DECISIONS.md)  
> **Status:** Phase 23 Amendment — Architectural Extension Only  
> **Parent Specification:** [`docs/architecture/adaptive_multi_horizon_strategy_architecture.md`](adaptive_multi_horizon_strategy_architecture.md) (Governing Baseline)  
> **Parent Governance:** `ADR-003` (Deterministic Hard Risk Engine), `ADR-007` (Bi-Temporal Point-in-Time Alpha Lake), `ADR-022` (Market-Adaptive Governance), `ADR-023` (Strategy Admission Standard)  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed, Evidence > Belief, Implementation Correctness $\neq$ Mathematical Validity)  
> **Date:** 2026-09-05  
> **Version:** 1.0.0  

---

## DOCUMENT STATUS & GOVERNANCE BOUNDARIES

```text
════════════════════════════════════════════════════════════════════════════════
                        DOCUMENT STATUS: ARCHITECTURAL EXTENSION ONLY
════════════════════════════════════════════════════════════════════════════════
STATUS: ARCHITECTURAL SPECIFIED
IMPLEMENTATION: NOT YET IMPLEMENTED (ZERO PRODUCTION SOURCE CODE MUTATIONS)
UNIT / INTEGRATION TESTS: NOT YET IMPLEMENTED (DEFERRED TO IMPLEMENTATION PHASES)
LIVE CAPITAL: HARD-LOCKED AT $0.00 (ZERO LIVE TRADING / ORDERS = 0)
BROKER CONNECTIVITY: STRICTLY DISCONNECTED
GATE B AUTHORIZATION: UNCHANGED (STEP 3 CEREMONY & STEP 4 ACTIVATION LOCKED)
SLICE 3: STRICTLY BLOCKED
════════════════════════════════════════════════════════════════════════════════
```

> [!CAUTION]
> **MANDATORY GOVERNANCE RESTRICTIONS:**
> 1. **DO NOT START LIVE TRADING.**
> 2. **DO NOT MODIFY GATE B AUTHORIZATION OR REV10 GOVERNANCE STATE.**
> 3. **DO NOT UNLOCK STEP 3 (CEREMONY) OR STEP 4 (ACTIVATION).**
> 4. **DO NOT ENABLE SLICE 3.**
> 5. **DO NOT CONNECT TO A LIVE BROKER.**
> 6. **DO NOT ADD UNVALIDATED SPOOFING OR MICROSTRUCTURE HEURISTICS TO THE PRODUCTION RISK ENGINE.**
> 7. **DO NOT CLAIM SPOOFING DETECTION CAPABILITY WITHOUT FORMAL EMPIRICAL VALIDATION.**
>
> This amendment extends the Phase 23 architecture. It does **NOT** replace the existing Phase 23 specification. The existing Phase 23 baseline (`adaptive_multi_horizon_strategy_architecture.md`) remains the governing architectural foundation.

---

# 1. PURPOSE

This amendment formally extends the scope of Phase 23 from:

$$\text{Adaptive Multi-Horizon Strategy \& Market-Regime Architecture}$$

to additionally incorporate:

$$\boxed{\mathbf{Market\ Microstructure,\ Order\text{-}Book\ Event\ Intelligence\ \&\ Decision\ Learning}}$$

The primary architectural goal is to ensure that the ACASH platform can eventually reason about market dynamics that are fundamentally **invisible to conventional OHLCV-only and trade-tape-only backtests**.

This includes, but is not limited to:
- Liquidity supply and demand behavior at granular depth levels.
- Order-book imbalance and its temporal persistence.
- Order-book absorption (passive limit liquidity absorbing aggressive market flow).
- Rapid liquidity withdrawal (fading liquidity prior to execution).
- Order persistence and time-in-queue dynamics.
- Order cancellation behavior (burst cancellations, cancel/add ratios).
- Displayed versus executed liquidity dynamics (phantom liquidity vs executed volume).
- Microstructure trade-flow toxicity and aggressor response.
- Potential spoofing-like patterns and quote manipulation artifacts.

### The Epistemic Invariant for Microstructure Research
> [!IMPORTANT]
> **ACASH MUST NOT CLAIM THAT OBSERVED MARKET BEHAVIOR IS DEFINITIVELY MARKET MANIPULATION MERELY BECAUSE A HEURISTIC OR ANOMALY DETECTOR FIRES.**
>
> - **The Correct Architectural Objective:** Detect suspicious, abnormal, or fragile market microstructure conditions and **reduce confidence in a trading signal or scale down risk exposure** when empirical evidence warrants it.
> - **Strictly Prohibited Objective:** Automatically claiming to identify, prove, or label that an external market participant is engaging in illegal market manipulation or intentional spoofing.

---

# 2. FUNDAMENTAL BACKTESTING LIMITATION

The platform architecture formally codifies the following empirical principle:

$$\boxed{\mathbf{Conventional\ OHLCV\ and\ trade\text{-}based\ backtesting\ CANNOT\ reconstruct\ non\text{-}executed\ orders\ absent\ from\ historical\ data.}}$$

### Canonical Illustration: The Non-Executed Order Problem
Consider a market participant executing a classic quote-stuffing or phantom-depth cycle:

```text
Time t_0:   ADD Limit Bid   10,000 units @ 100.00   (Apparent massive buying support)
Time t_1:   ADD Limit Bid   15,000 units @ 100.00   (Apparent buying pressure amplifies)
Time t_2:   ADD Limit Bid   20,000 units @ 100.00   (Top-of-book depth appears deep & resilient)
Time t_3:   ADD Limit Bid   25,000 units @ 100.00   (Naive indicators signal heavy demand)
--------------------------------------------------------------------------------------
Time t_4:   CANCEL Order #1 (10,000 units)          (Sudden liquidity withdrawal)
Time t_5:   CANCEL Order #2 (15,000 units)          (Sudden liquidity withdrawal)
Time t_6:   CANCEL Order #3 (20,000 units)          (Sudden liquidity withdrawal)
Time t_7:   CANCEL Order #4 (25,000 units)          (Depth collapses to near zero)
Time t_8:   Sell Order executes 100 units @ 99.95   (Price breaks through unsupported book)
```

If the historical research dataset contains only:
1. OHLCV bars (1-minute, 5-minute, or daily),
2. Aggregated volume,
3. Executed trade prints (Tape/Ticks), or
4. Fill summaries,

then the research engine has **zero mathematical record that the 70,000 units of bid liquidity ever existed**, let alone that they were systematically posted and cancelled within milliseconds prior to the trade print.

### Architectural Conclusion
> **Backtesting is NOT inherently incapable of studying spoofing-like or microstructure behavior.**  
> **The limitation is purely the information content and granularity of the historical dataset.**

---

# 3. RESEARCH INFORMATION HIERARCHY

To ensure analytical clarity and prevent methodological conflation, ACASH establishes three canonical data levels for quantitative research:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       LEVEL 3: ORDER-BOOK EVENT DATA                        │
│   • Order Add, Modify, Cancel, Execute events (MBO)                         │
│   • Exact price, size, side, sequence, depth, order lifetime, queue pos     │
│   • Capability: Temporal order-book reconstruction & liquidity dynamics     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      LEVEL 2: TRADE TAPE / TICK DATA                        │
│   • Executed trade prints: Price, Size, Timestamp, Aggressor Side           │
│   • Capability: Trade flow, CVD, VWAP, aggressive trade intensity           │
│   • Limitation: Cannot reconstruct non-executed posted/cancelled orders     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            LEVEL 1: OHLCV BARS                              │
│   • Aggregated Open, High, Low, Close, Volume, Bar Timestamps               │
│   • Capability: Classical indicators, macro trend, volatility regimes       │
│   • Limitation: Coarse temporal resolution; blind to intraday micro-dynamics│
└─────────────────────────────────────────────────────────────────────────────┘
```

### Level 1: OHLCV Bar Data
- **Information Content:** Aggregated Open, High, Low, Close prices, volume, bar start/end timestamps.
- **Analytical Utility:** Macro trend identification, long-term volatility regimes, moving averages, geometric candlestick metrics (`PriceStructureMeasurements`).
- **Critical Limitation:** Coarse time resolution; completely blind to order placement, queue dynamics, and non-executed liquidity.

### Level 2: Trade Tape / Tick Data
- **Information Content:** Executed transactions, execution prices, exchange timestamps, knowledge timestamps, trade sizes, aggressor side (`BUY`, `SELL`, `UNKNOWN`), trade conditions.
- **Analytical Utility:** Cumulative Volume Delta (CVD), Volume-Weighted Average Price (VWAP), aggressive trade intensity, trade-size distribution, bar-level absorption indicators.
- **Critical Limitation:** Cannot reconstruct orders that were posted, modified, or cancelled without executing. Blind to resting depth changes that did not match against a trade.

### Level 3: Order-Book Event Data (Target Research Model)
- **Information Content:** Discrete order lifecycle events:
  - `OrderAdd`
  - `OrderModify`
  - `OrderCancel`
  - `OrderExecute`
  - Price level, Side (`BID`, `ASK`), Size, Timestamp, Sequence Number, Depth Level, Queue Position (where provided by venue), Order Lifetime (reconstructable).
- **Analytical Utility:** True temporal order-book reconstruction, dynamic liquidity withdrawal measurement, cancel/add velocity, queue depletion, and microstructure anomaly research.

### Core Architectural Invariant
$$\boxed{\mathbf{Order\ Book\ Snapshot} \neq \mathbf{Order\ Book\ Intelligence}}$$
$$\boxed{\mathbf{Required\ Capability} = \mathbf{Order\text{-}Book\ Event\ Stream} + \mathbf{Temporal\ Analysis}}$$

Periodic snapshots (e.g. 1-second Top-of-Book snapshots) alias high-frequency order insertions and cancellations occurring between sampling ticks. Real microstructure intelligence requires continuous event stream processing.

---

# 4. MARKET MICROSTRUCTURE DATA LAYER

Phase 23 defines the canonical data ingestion and feature pipeline for microstructure research:

```
                    EXTERNAL MARKET / VENUE
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
       PRICE / OHLCV       TRADE TAPE         ORDER BOOK
         (Level 1)          (Level 2)       EVENTS (Level 3)
            │                  │                  │
            └──────────────────┼──────────────────┘
                               ▼
                   NORMALIZED MARKET STATE
                               ▼
                    POINT-IN-TIME STORAGE
               (Bi-Temporal Alpha Lake Engine)
                               ▼
                      FEATURE EXTRACTION
              (Temporal Microstructure Engine)
                               ▼
               REGIME / MICROSTRUCTURE ANALYSIS
```

### Data Layer Invariants
1. **Bi-Temporal Point-in-Time Correctness (`ADR-007`):** Every event must preserve both $t_{\text{exchange}}$ (event time in venue clock) and $t_{\text{knowledge}}$ (observation time in ACASH ingestion clock).
2. **Zero Lookahead Contamination:** No future event, fill, cancellation, or regime classification may ever leak into historical feature evaluation:
   $$\text{Features}(t) = \mathcal{F}\Big(\big\{e_k \;\big|\; t_{\text{knowledge}}(e_k) \le t_{\text{decision}}\big\}\Big)$$
3. **Fail-Closed on Timestamp Corruption:** Events with backwards knowledge timestamps, missing exchange timestamps, or non-monotonic sequence numbers must raise `DataContractError` immediately.

---

# 5. ORDER-BOOK EVENT MODEL

ACASH establishes a canonical, venue-agnostic Order-Book Event Model. Venue-specific adapters (e.g. CME MDP 3.0, Nasdaq ITCH, Binance WebSocket, MT5 MarketDepth) normalize raw venue payloads into this unified schema.

### Canonical Event Types
- `OrderAdd`: Insertion of a new resting limit order into the depth ladder.
- `OrderModify`: Change in price and/or size of an existing resting order.
- `OrderCancel`: Partial or total voluntary cancellation of an unexecuted resting order.
- `OrderExecute`: Matching and execution of resting order volume against an incoming aggressive order.

### Canonical Event Schema Contract
```python
class CanonicalOrderBookEvent(BaseModel):
    """Canonical Level-3 / Level-2 Order Book Mutation Event."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    # Scope & Routing Identity
    venue: str                          # Venue / Exchange identifier (e.g. "CME", "NASDAQ", "BINANCE")
    channel_id: str                     # Market data channel or multicast feed ID
    instrument: str                     # Standardized ACASH symbol (e.g. "NQ", "EURUSD", "BTCUSDT")
    trading_date: date                  # Financial calendar session date

    # Bi-Temporal Timestamps & Sequencing
    event_timestamp_utc: datetime       # Venue exchange timestamp (nanosecond resolution where available)
    receive_timestamp_utc: datetime     # Ingestion / network receipt timestamp
    knowledge_timestamp_utc: datetime   # ACASH Alpha Lake commit timestamp (PIT barrier)
    sequence_number: int                # Monotonically increasing sequence number from venue
    sub_index: int = 0                  # Sub-transaction index for atomic multi-event packets

    # Mutation Core
    event_type: BookEventType           # ADD, MODIFY, CANCEL, EXECUTE, CLEAR
    side: BookSide                      # BID, ASK, ALL
    price: Optional[Decimal]            # Order price (None strictly for side-wide CLEAR actions)
    quantity: Optional[Decimal]         # Mutated or resulting quantity
    order_id: Optional[str] = None      # MBO unique order identifier (None for aggregated MBP feeds)
    queue_position: Optional[int] = None# Dynamic queue ranking if venue exposes queue priority
    level_idx: Optional[int] = None     # Price ladder index (0 = BBO, 1..N = Depth)

    # Data Quality & Provenance
    data_quality_flag: MarketDataQuality = MarketDataQuality.COMPLETE
    provenance_hash: str                # SHA-256 digest of upstream payload
```

### Separation of Concerns: Canonical vs Venue-Specific
- Universal fields (`price`, `quantity`, `side`, `event_type`, `sequence_number`, `timestamps`) belong to the **Canonical Model**.
- Venue-specific artifacts (e.g. CME match event reasons, Nasdaq order reference numbers, crypto WebSocket sequence IDs) are handled inside **Venue Adapters** and must never pollute core analysis logic.

---

# 6. TEMPORAL MICROSTRUCTURE FEATURES

Phase 23 reserves a formal feature space for temporal microstructure analytics. These features quantify liquidity dynamics across rolling time windows:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TEMPORAL MICROSTRUCTURE FEATURE SPACE                    │
├──────────────────────────────┬──────────────────────────────────────────────┤
│ 1. Imbalance & Depth Dynamics│ • Bid/Ask Book Imbalance (OBI Top-1, 5, 10)  │
│                              │ • Imbalance Persistence (half-life in ms)    │
│                              │ • Depth Concentration & Ladder Dispersion    │
├──────────────────────────────┼──────────────────────────────────────────────┤
│ 2. Order Cancellation Ratios │ • Add/Cancel Ratio & Cancel Velocity         │
│                              │ • Order Lifetime Distribution (median, p95)  │
│                              │ • Reprice & Modify Frequency                 │
│                              │ • Pull/Stack Ratio (withdrawn vs added size) │
├──────────────────────────────┼──────────────────────────────────────────────┤
│ 3. Liquidity Velocity        │ • Replenishment Rate post-execution          │
│                              │ • Withdrawal Rate prior to trade prints      │
│                              │ • Order Book Resilience & Recovery Speed     │
├──────────────────────────────┼──────────────────────────────────────────────┤
│ 4. Execution vs Displayed    │ • Executed-to-Displayed Liquidity Ratio      │
│                              │ • Aggressive Trade Intensity                 │
│                              │ • Price Response to Displayed Size           │
│                              │ • Order Flow Toxicity (VPIN-like proxy)      │
└──────────────────────────────┴──────────────────────────────────────────────┘
```

### Feature Governance Rules
1. **Research Inputs Only:** Microstructure features are quantitative research observations. They are **NOT** hardcoded universal trading rules.
2. **Deterministic Reproducibility:** Every feature must be reproducible bit-for-bit from the underlying point-in-time event stream.
3. **Cryptographic Lineage:** Feature sets must be sealed in a `FeatureManifest` recording the exact parameter config hash, source event hash, and software calculation version.

---

# 7. SPOOFING / SUSPICIOUS LIQUIDITY BEHAVIOR RESEARCH

### Microstructure Anomaly Detection
ACASH defines an empirical research framework for **Microstructure Anomaly Detection**. The objective is to identify statistical dislocations between displayed liquidity intent and actual execution reality.

Candidate composite anomaly signals include:
1. **Fleeting Liquidity Bursts:** Unusually large limit orders posted near the BBO that are cancelled within an extremely short lifetime (e.g. $< 50\text{ ms}$) without taking fills.
2. **Abnormal Pull/Stack Asymmetry:** Excessive cancellation of resting orders on one side of the book immediately following an aggressive trade on the opposite side.
3. **High Displayed Size / Low Fill Rate:** Persistent large depth displayed at Level 1 or 2 that consistently vanishes before aggressive market orders reach the queue.
4. **Imbalance Dislocation without Price Discovery:** Extreme bid/ask depth imbalance persisting over multiple cycles that fails to induce expected directional price movement (absorption or phantom quote).
5. **Rapid Add-Cancel Oscillation:** High-frequency insertion and deletion cycles around key psychological support/resistance levels.

### Strict Labeling Standard
```text
PROHIBITED OUTPUT:
"SPOOFING_CONFIRMED"
"MARKET_MANIPULATION_DETECTED"

REQUIRED CANONICAL OUTPUTS:
MICROSTRUCTURE_NORMAL      → Clean liquidity, standard cancel/add dynamics
MICROSTRUCTURE_CAUTION     → Mild liquidity withdrawal or elevated cancel ratios
MICROSTRUCTURE_ANOMALOUS   → Severe imbalance dislocation, fleeting depth bursts
SUSPICIOUS_LIQUIDITY       → High-confidence statistical outlier in displayed liquidity
```

Unless an external regulatory authority or legally certified forensic data provider provides an immutable legal ruling, ACASH strictly treats these patterns as **probabilistic liquidity fragility indicators**, never as legal proofs of intent.

---

# 8. MICROSTRUCTURE TRUST ADJUSTMENT IN THE STRATEGY PIPELINE

Microstructure intelligence integrates into the strategy pipeline as a **Confidence and Sizing Adjuster**, not as an unconstrained execution bypass.

### The Extended Strategy Pipeline
```text
                  STRATEGY SIGNAL GENERATION
                              │
                              ▼
                  MARKET MICROSTRUCTURE CHECK
           (Evaluates Book Integrity & Fragility)
                              │
                              ▼
                 MICROSTRUCTURE CONTEXT REPORT
                              │
                              ▼
                  DETERMINISTIC RISK ENGINE
          (Evaluates Portfolio, Margin, Risk Budget)
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
            ALLOW                           REJECT
              │                               │
              ▼                               ▼
       EXECUTION ENGINE                SHADOW DECISION
 (Admitted OrderIntents Only)         (Counterfactual Log)
```

### Practical Adjustment Matrix
When a strategy emits a directional signal (e.g. `LONG_BREAKOUT`) but the Microstructure Check observes suspicious or anomalous liquidity:

| Microstructure Assessment | Observed Book Phenomenon | Trust Adjustment Action | Downstream Effect |
| :--- | :--- | :--- | :--- |
| **MICROSTRUCTURE_NORMAL** | Deep book, low cancel rate, genuine absorption | Trust Factor = $1.0$ | Full authorized position sizing |
| **MICROSTRUCTURE_CAUTION** | Elevated cancel/add ratio, wide spread variance | Trust Factor = $0.5 - 0.7$ | Scale down proposed target position |
| **MICROSTRUCTURE_ANOMALOUS** | Large phantom bids, rapid withdrawal before prints | Trust Factor = $0.2 - 0.5$ | Block incremental tranches; require confirmation |
| **SUSPICIOUS_LIQUIDITY** | Extreme fleeting depth burst; spoofing-like pattern | Trust Factor = $0.0$ | **NO_TRADE (Proposal suppressed)** |
| **DATA_QUALITY_DEGRADED** | Sequence gap, stale book, uncertain reconstruction | Trust Factor = $0.0$ | **FAIL-CLOSED (Reject all proposals)** |

> [!IMPORTANT]
> **NO HARDCODED UNIVERSAL VETO WITHOUT EMPIRICAL VALIDATION:**  
> The exact reaction to a microstructure warning must be declared in the strategy's and risk policy's admitted configuration. The system must not hardcode `"microstructure anomaly = always reject"` until empirical out-of-sample research confirms its net benefit across regimes.

---

# 9. MICROSTRUCTURE MUST NOT BYPASS RISK ENGINE

The architecture preserves non-negotiable jurisdictional boundaries:

$$\mathbf{Signal} \neq \mathbf{Order}$$
$$\mathbf{Microstructure\ Classification} \neq \mathbf{Authorization}$$
$$\mathbf{Market\ Regime} \neq \mathbf{Authorization}$$
$$\mathbf{Strategy\ Plugin} \neq \mathbf{Authorization}$$

```text
CORRECT ARCHITECTURAL FLOW:
Signal Proposal ──► Microstructure Context ──► Risk Engine ──► ALLOW / REDUCE / REJECT ──► Execution

STRICTLY FORBIDDEN / ILLEGAL FLOW:
Microstructure Detector ──► Direct Broker Order (BYPASSES RISK & GOVERNANCE)
```

Only the **Deterministic Risk Engine** (`ADR-003`) possesses the authority to admit orders. Only the **Governance Layer** possesses the authority to grant operational capital authority. Microstructure is an observational and contextual input; it possesses **zero execution authority**.

---

# 10. SHADOW DECISION & SHADOW TRADE SYSTEM

To prevent hindsight bias, survivorship bias, and unmeasured filter damage, ACASH introduces the **Shadow Decision Evaluation System**.

Whenever a strategy produces a valid signal or target position proposal, but the proposal is **REJECTED, SUPPRESSED, OR SCALED DOWN** by:
1. The Market Microstructure Check,
2. The Regime Suitability Filter, or
3. The Deterministic Risk Engine,

ACASH retains an immutable, research-only **Shadow Decision Record**.

```text
Strategy Signal Proposal
           │
           ▼
Risk / Microstructure Gate
           │
           ├────────────────────────────┐
           ▼                            ▼
         ALLOW                        REJECT
           │                            │
           ▼                            ▼
    Live Execution               SHADOW DECISION RECORD
           │                            │
           ▼                            ▼
   Broker Fills & PnL           Observe Subsequent Market Outcome
           │                            │
           └─────────────┬──────────────┘
                         ▼
             OUTCOME ATTRIBUTION ENGINE
                         │
                         ▼
        STRATEGY TOURNAMENT & POLICY EVALUATION
```

### Core Empirical Questions Answered by Shadow Evaluation
- What would the strategy have done if the proposal had not been rejected?
- Which exact gate or rule rejected it (Microstructure, Regime, Margin, Daily Loss)?
- What were the precise market regime and microstructure measurements at rejection time?
- What did the market actually do over the strategy's expected holding horizon?
- **Was the rejection beneficial?** (Did it save the system from an adverse dislocation?)
- **Was the rejection harmful?** (Did it filter out a highly profitable, low-risk trade?)

---

# 11. SHADOW DECISION DATA CONTRACT

Shadow decisions are first-class financial research records. They must conform to a strict schema:

```python
class ShadowDecisionRecord(BaseModel):
    """Immutable research record tracking rejected or modified strategy proposals."""
    model_config = ConfigDict(frozen=True, extra="forbid")

    # Identification & Provenance
    decision_id: str                    # Unique deterministic UUID
    timestamp_utc: datetime             # Evaluation timestamp
    strategy_id: str                    # Strategy producing proposal
    strategy_version: str               # Semantic version of strategy
    instrument: str                     # Target symbol

    # Contextual State Snapshots
    market_regime: str                  # Active regime label at decision time
    market_state_digest: str            # SHA-256 digest of MarketStateVector
    microstructure_state_digest: str    # SHA-256 digest of MicrostructureMeasurements
    data_quality_status: MarketDataQuality

    # Proposal Details
    proposed_action: str                # BUY, SELL, HOLD, SCALE_IN
    proposed_target_position: Decimal   # Desired net units
    proposed_risk_budget: Decimal       # Requested currency risk ($)
    proposed_entry_schedule: str        # JSON representation of tranche plan

    # Rejection & Suppression Forensics
    rejection_layer: str                # MICROSTRUCTURE_GATE, REGIME_GATE, RISK_ENGINE
    rejection_reason: str               # Explicit human/machine readable explanation
    applied_haircut_ratio: Decimal      # 0.0 for total reject, 0.0 < r < 1.0 for reduction

    # Counterfactual Simulation Parameters
    hypothetical_entry_price: Decimal   # Prevailing benchmark price at decision
    hypothetical_stop_price: Decimal    # Proposed stop loss level
    hypothetical_target_price: Optional[Decimal]
    assumed_slippage_bps: Decimal       # Realistic liquidity-adjusted friction
    assumed_fee_bps: Decimal            # Broker commission model

    # Realized Market Counterfactual Outcomes (Populated Ex-Post)
    realized_market_outcome_window: str # e.g. "1H", "4H", "1D"
    counterfactual_max_favorable_excursion: Optional[Decimal] = None # MFE
    counterfactual_max_adverse_excursion: Optional[Decimal] = None   # MAE
    counterfactual_pnl: Optional[Decimal] = None                     # Hypothetical net PnL ($)
    was_rejection_beneficial: Optional[bool] = None                  # True if counterfactual hit SL
```

### Strict Demarcation Invariant
$$\boxed{\mathbf{ACTUAL\ TRADING\ PERFORMANCE} \quad \ne \quad \mathbf{SHADOW\ /\ HYPOTHETICAL\ PnL}}$$

Under no circumstances may hypothetical or shadow PnL be merged into actual account equity, broker reconciliation ledgers, or live track records. Shadow data is strictly partitioned for offline research, filter evaluation, and tournament selection.

---

# 12. WHY SHADOW DECISIONS MATTER: MEASURING FILTER EFFICIENCY

A trading system that only records executed trades suffers from massive cognitive bias:
> "We only see the disasters we survived and the trades we took; we are blind to the alpha we killed."

ACASH establishes six mandatory decision memory categories:
1. **Trades Taken (Executed):** Complete live/demo fills, slippage, latency, actual PnL.
2. **Trades Rejected (Filtered):** Complete proposed parameters suppressed by gates.
3. **Why Rejected:** Specific layer, threshold, and causal trigger.
4. **Market Context at Decision:** Exact regime, spread, depth, and microstructure state.
5. **Subsequent Market Outcome:** Counterfactual path over horizon $H$.
6. **Strategy Attribution:** Decomposition of filter impact on strategy expectancy.

```text
SCENARIO A: BENEFICIAL FILTER (Edge Preserved)
Signal: LONG ──► Microstructure Gate: REJECT (Fleeting depth detected)
Subsequent Market: Price drops 150 pips, would have hit Stop Loss.
Conclusion: Filter saved capital. Counterfactual loss avoided.

SCENARIO B: HARMFUL FILTER (Alpha Destruction)
Signal: LONG ──► Microstructure Gate: REJECT (False-positive anomaly)
Subsequent Market: Price trends cleanly upward +300 pips to target.
Conclusion: Filter destroyed edge. False positive cost measured.
```

By systematically logging both scenarios, ACASH can mathematically optimize gate thresholds rather than guessing whether a risk control is protecting capital or strangling profitability.

---

# 13. DECISION LEDGER EXTENSION & 100% AUDIT RECONSTRUCTION

The ACASH `OperationalLedger` (`ADR-006`, Phase 10) is extended to guarantee **100% point-in-time decision replayability**:

```text
MARKET DATA SNAPSHOT (SHA-256)
               │
               ▼
REGIME CLASSIFICATION (SHA-256)
               │
               ▼
MICROSTRUCTURE CONTEXT (SHA-256)
               │
               ▼
STRATEGY SIGNAL PROPOSAL (Immutable DTO)
               │
               ▼
TARGET POSITION & RISK BUDGET (Immutable DTO)
               │
               ▼
DETERMINISTIC RISK EVALUATION (ALLOW / REDUCE / REJECT)
               │
               ▼
EXECUTION INTENT  OR  SHADOW DECISION
               │
               ▼
REALIZED BROKER OUTCOME  OR  COUNTERFACTUAL OUTCOME
```

Every record is bound by:
- Unique deterministic UUIDs.
- Monotonic sequence indices.
- SHA-256 hash chaining (`previous_event_digest == digest(Event_{n-1})`).
- Cryptographic code/model manifests (`config_sha256`, `model_sha256`, `code_version`).

---

# 14. MULTI-DIMENSIONAL STRATEGY ATTRIBUTION

ACASH rejects simplistic aggregate PnL evaluation. Strategies are evaluated across orthogonal dimensions:

$$\boxed{\text{Performance} = \mathcal{G}\big(\text{Strategy}, \text{Instrument}, \text{Regime}, \text{Microstructure State}, \text{Execution Quality}\big)}$$

Research must answer:
1. **Which strategy worked?** (Specific plugin and version).
2. **Where did it work?** (Instrument, venue, liquidity profile).
3. **When did it work?** (Session, volatility condition, time-of-day).
4. **Under which regime?** (Trend Strong, Range Tight, Breakout Active).
5. **Under which microstructure state?** (High book resilience, balanced flow, low toxicity).
6. **Why did it work or fail?** (Structural edge vs uncompensated risk vs filter distortion).

---

# 15. PHASE 23 EXTENDED CONCEPTUAL ARCHITECTURE

The governing conceptual architecture of ACASH is formally extended as follows:

```
                                  MARKET
                                     │
                  ┌──────────────────┼──────────────────┐
                  ▼                  ▼                  ▼
                PRICE              VOLUME           ORDER BOOK
                  │                  │                  │
                  │              TRADE TAPE             │
                  │                  │                  │
                  └──────────────────┼──────────────────┘
                                     ▼
                             MARKET STATE VECTOR
                                     │
                                     ▼
                           REGIME DETECTION ENGINE
                                     │
                                     ▼
                         MICROSTRUCTURE CHECK ENGINE
                                     │
                                     ▼
                         STRATEGY ELIGIBILITY GATE
                                     │
                         STRATEGY PLUGINS (PLUGINS)
                          ┌─────┬─────┬─────┬─────┐
                          ▼     ▼     ▼     ▼     ▼
                          A     B     C     D   Future
                          └─────┴─────┴─────┴─────┘
                                     │
                                     ▼
                              SIGNAL PROPOSAL
                                     │
                          TARGET POSITION PROPOSAL
                                     │
                                RISK BUDGET
                                     │
                              ENTRY SCHEDULE
                                     │
                         DETERMINISTIC RISK ENGINE
                                /         \
                               /           \
                            ALLOW         REJECT
                             │               │
                             ▼               ▼
                      EXECUTION ENGINE   SHADOW DECISION
                             │               │
                             ▼               ▼
                       RECONCILIATION   OUTCOME TRACKING
                             │               │
                             └───────┬───────┘
                                     ▼
                              DECISION LEDGER
                                     │
                                     ▼
                            STRATEGY TOURNAMENT
                                     │
                                     ▼
                              RISK ADMISSION
```

---

# 16. BOUNDARY DISCIPLINE: MICROSTRUCTURE VS RISK VS GOVERNANCE VS EXECUTION

The platform strictly enforces conceptual and operational boundaries:

| Architectural Domain | Sovereign Question Answered | Authority Level | Prohibited Actions |
| :--- | :--- | :--- | :--- |
| **Market Microstructure Engine** | *"What is happening in the internal market liquidity structure?"* | **Observational / Contextual Only** | CANNOT approve risk; CANNOT transmit orders; CANNOT allocate capital. |
| **Deterministic Risk Engine** | *"Are we mathematically allowed to assume this risk exposure?"* | **Sovereign Admissibility Gatekeeper** | CANNOT manufacture trading alpha; CANNOT authorize capital above governance limits. |
| **Governance Layer** | *"Are we cryptographically authorized to operate with real capital?"* | **Constitutional Authority Boundary** | CANNOT manipulate backtest results; CANNOT bypass deterministic risk engine. |
| **Execution Engine** | *"How do we mechanically fulfill an already admitted order intent?"* | **Deterministic Protocol Mechanism** | CANNOT generate trade thesis; CANNOT scale position outside admitted bounds. |

---

# 17. DATA QUALITY AS A FIRST-CLASS CONSTRAINT

Order-book research is fragile against data corruption. Missing deltas cause phantom books; unhandled packet drops cause false crossed-book signals.

### Market Data Quality Enumeration
```python
class MarketDataQuality(str, Enum):
    """Canonical data quality states for order book and microstructure streams."""
    COMPLETE = "COMPLETE"                          # Fully validated, contiguous sequence, no drops
    DEGRADED = "DEGRADED"                          # Feed latency elevated, non-critical telemetry missing
    STALE = "STALE"                                # Heartbeat delayed, book not updated within threshold
    PARTIAL = "PARTIAL"                            # Limited depth levels available (e.g. BBO only)
    SEQUENCE_GAP = "SEQUENCE_GAP"                  # Upstream sequence number skip detected
    RECONSTRUCTION_UNCERTAIN = "RECONSTRUCT_UNCERTAIN" # Book reconstruction checksum mismatch
    INVALID = "INVALID"                            # Crossed book in continuous market, corrupt prices
```

### The Absence Invariant
$$\boxed{\mathbf{No\ cancellation\ event\ received} \quad \ne \quad \mathbf{No\ cancellation\ occurred}}$$

If a feed drops packets (`SEQUENCE_GAP`), the system must **fail-closed** or degrade confidence immediately. Missing events must never be silently interpreted as resting liquidity.

---

# 18. POINT-IN-TIME REQUIREMENT & ZERO LOOKAHEAD LEAKAGE

All microstructure features, anomaly flags, and regime inferences must be evaluated strictly using data known as of decision time $t_{\text{decision}}$:

$$\text{Knowledge}(e) \le t_{\text{decision}}$$

Any design where:
- Future order-book events,
- Future trade executions or fills,
- Future cancel bursts, or
- Post-hoc regime labels,

are accessible to candidate strategies or filters is fundamentally invalid. Such pipelines will be immediately rejected at Gate 4 and Gate 6.

---

# 19. DETERMINISTIC REPLAY ENGINE SPECIFICATION

To validate microstructure strategies, ACASH requires a deterministic **Historical Event Replay Engine**:

```text
HISTORICAL L3 / L2 EVENT STREAM
               │
               ▼
         REPLAY CLOCK (Monotonic Tick Coordinator)
               │
               ▼
     RECONSTRUCT ORDER BOOK (Level 3 / Level 2 Ladder)
               │
               ▼
     COMPUTE MICROSTRUCTURE FEATURES (Time-aligned)
               │
               ▼
     ESTIMATE REGIME & LIQUIDITY INTEGRITY
               │
               ▼
     EXECUTE CANDIDATE STRATEGIES
               │
               ▼
     EVALUATE MICROSTRUCTURE CHECK & RISK ENGINE
               │
               ▼
     LOG ACTUAL / SHADOW DECISION & ATTRIBUTE OUTCOME
```

### Replay Invariants
1. **Sequence Order Primacy:** Replay must follow venue sequence numbers where available. Wall-clock timestamps must never override venue sequence semantics during packet bursts.
2. **State Consistency:** Replaying identical event logs must yield bit-for-bit identical order books, feature tables, and decision outputs.

---

# 20. DUAL-PATH INTEGRATION: LIVE EVENT BUS VS HISTORICAL REPLAY

ACASH rejects architectures where the research engine uses a different schema or data model than production:

```text
                  VENUE DATA ADAPTER
                           │
                           ▼
                 CANONICAL MARKET EVENT
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
      LIVE EVENT BUS           POINT-IN-TIME Alpha Lake
             │                           │
             ▼                           ▼
      LIVE TRADING /             HISTORICAL REPLAY /
       SHADOW ENGINE              RESEARCH TOURNAMENT
```

Both live execution and offline research consume the identical `CanonicalOrderBookEvent` and `MarketStateVector` interfaces.

---

# 21. PHANTOM / GHOSTBOT AS EXTERNAL REFERENCE ONLY

The public materials, demonstrations, and community commentary concerning commercial or public systems (e.g. Phantom Trader / GhostBot) indicate conceptual interest in:
- Level-2 depth dynamics,
- Bid/ask absorption,
- Order-flow toxicity,
- Strategy arm selection,
- Rejection/shadow decision tracking.

These concepts offer valid architectural inspiration for ACASH.

However:
> [!IMPORTANT]
> **ACASH STRICTLY RECORDS PHANTOM / GHOSTBOT AS AN EXTERNAL CONCEPTUAL REFERENCE ONLY.**
>
> 1. Public marketing material does **NOT** provide sufficient scientific or forensic evidence to certify that Phantom possesses a formally validated, statistically proven spoofing detection classifier.
> 2. ACASH must **NEVER** cite third-party commercial claims as proof that an algorithm works.
> 3. ACASH must **NEVER** treat external systems as validated quantitative benchmarks without raw code, verified fills, and reproducible out-of-sample data.

---

# 22. EXTERNAL REFERENCE DATA MUST NOT BECOME TRAINING TRUTH

Published trade logs (such as public 44-trade sample runs, isolated NQ performance snapshots, or promotional win-rate figures):
- Represent tiny, statistically insignificant sample sizes ($N = 44 \implies$ massive standard error on Sharpe and Win Rate).
- Suffer from severe survivorship, selection, and cherry-picking bias.
- Lack complete fee, slippage, and market-impact attribution.

### Mandatory Policy
$$\boxed{\mathbf{External\ sample\ logs\ are\ OBSERVABLE\ REFERENCE\ DATA,\ NOT\ ground\text{-}truth\ training\ sets.}}$$

ACASH must collect, clean, verify, and validate its own empirical datasets through the Phase 2/3/4/6/17 pipeline.

---

# 23. RESEARCH VALIDATION REQUIREMENTS FOR MICROSTRUCTURE HEURISTICS

Before any microstructure anomaly detector or heuristic filter may be admitted into candidate strategy pipelines:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│             15-POINT MANDATORY RESEARCH VALIDATION CHECKLIST                │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. Formal economic & market microstructure hypothesis defined in writing.  │
│  2. Explicit mathematical feature definitions with zero lookahead bias.     │
│  3. Formal objective labeling methodology (no discretionary visual tags).   │
│  4. Quantified False Positive cost (alpha destroyed by premature filtering).│
│  5. Quantified False Negative cost (capital lost to adverse dislocation).   │
│  6. Out-of-sample (OOS) statistical validation across unseen periods.       │
│  7. Combinatorial Purged Cross-Validation (CSCV) and PBO calculation.       │
│  8. Walk-forward matrix evaluation across multiple distinct market regimes. │
│  9. Conservative broker commission model included.                          │
│ 10. Conservative tick-level slippage and latency model included.             │
│ 11. Feed latency and transmission delay simulation included.                │
│ 12. Synthetic data-quality degradation & packet drop stress testing.        │
│ 13. Cross-venue stability testing (ensuring signal is not an exchange bug). │
│ 14. Parameter stability analysis (ruling out razor-thin overfit optima).    │
│ 15. Mandatory benchmark comparison against unfiltered baseline strategy.    │
└─────────────────────────────────────────────────────────────────────────────┘
```

No microstructure filter will be admitted based solely on in-sample performance or theoretical elegance.

---

# 24. ADVERSARIAL RESEARCH TEST SUITE

Future microstructure implementations must be subjected to a rigorous adversarial test suite:

- **DATA-ADV-01 (Missing Packet Drops):** Synthetically drop $1\%$ to $10\%$ of order cancels; verify system detects sequence gap and flags `SEQUENCE_GAP`.
- **DATA-ADV-02 (Duplicate Packets):** Inject duplicate sequence numbers; verify fail-closed deduplication.
- **DATA-ADV-03 (Crossed Book Injection):** Inject inverted bids/asks; verify classification as `CROSSED_TRANSIENT` or `INVALID` without crashing.
- **DATA-ADV-04 (Synthetic Spoofing Wave):** Inject rapid 10,000-unit add/cancel waves; verify anomaly detector flags `SUSPICIOUS_LIQUIDITY` without emitting false "manipulation confirmed" claims.
- **DATA-ADV-05 (Genuine Large Institutional Orders):** Inject authentic resting blocks executed via iceberg; verify filter does not falsely reject legitimate execution.
- **DATA-ADV-06 (Zero-Depth Book):** Drain all liquidity; verify fail-closed transition to `NO_TRADE`.
- **DATA-ADV-07 (Timestamp Reversal):** Feed packets with $t_{\text{knowledge}} < t_{\text{previous}}$; verify immediate `DataContractError`.

---

# 25. STRATEGY ADAPTATION SAFETY: BOUNDED ADAPTATION VS EVOLUTION

Market-adaptive behavior must never degrade into unconstrained self-modifying code:

```text
FAST STATE ADAPTATION (Online, Real-Time)
• Evaluates prevailing market regime and microstructure context.
• Selects among ALREADY-ADMITTED, PRE-COMPILED strategy modules.
• Adjusts risk budgets monotonically within PRE-DEFINED, BOUNDED limits.
• ZERO authority to rewrite strategy algorithms or bypass risk rules.

SLOW STRATEGY EVOLUTION (Offline, Governed)
• Hypothesis formulation, feature engineering, and backtesting.
• Full 11-Gate Phase 17 Admission Lifecycle.
• Strategy Tournament ranking and multi-model competition.
• Requires formal cryptographic sealing and human governance sign-off.
```

Uncontrolled online reinforcement learning that dynamically alters trading system safety constraints is strictly banned.

---

# 26. THE COMPREHENSIVE ACASH LEARNING LOOP

The complete, multi-phase autonomous learning loop is formalized:

$$\begin{aligned}
\text{Market Data Stream} &\longrightarrow \text{Normalization (Canonical Schemas)} \\
&\longrightarrow \text{Bi-Temporal Storage (Alpha Lake Parquet)} \\
&\longrightarrow \text{Deterministic Replay \& Microstructure Feature Engine} \\
&\longrightarrow \text{Regime \& Liquidity Integrity Detection} \\
&\longrightarrow \text{Candidate Strategy Proposal Generation} \\
&\longrightarrow \text{Deterministic Hard Risk Engine Gate} \\
&\longrightarrow \begin{cases} \mathbf{ALLOW} \longrightarrow \text{Execution Engine} \longrightarrow \text{Reconciliation} \\ \mathbf{REJECT} \longrightarrow \text{Shadow Decision Logging} \longrightarrow \text{Counterfactuals} \end{cases} \\
&\longrightarrow \text{Append-Only Cryptographic Decision Ledger} \\
&\longrightarrow \text{Multi-Dimensional Outcome Attribution} \\
&\longrightarrow \text{Strategy Tournament Ranking} \\
&\longrightarrow \text{Phase 17 Governance Admission} \\
&\longrightarrow \text{Bounded Production Deployment}
\end{aligned}$$

---

# 27. FINAL CANONICAL ARCHITECTURAL POSITION

```markdown
════════════════════════════════════════════════════════════════════════════════
                  ACASH PHASE 23 AMENDMENT CANONICAL STATEMENT
════════════════════════════════════════════════════════════════════════════════

1. ACASH is an autonomous, risk-controlled quantitative trading infrastructure,
   not an ad-hoc collection of hardcoded indicators or single-horizon bots.

2. Conventional OHLCV backtests cannot evaluate non-executed order dynamics;
   order-book snapshots cannot capture temporal microstructure intelligence.

3. Advanced microstructure intelligence requires time-ordered order-book event
   streams (MBO/MBP) and deterministic point-in-time replay.

4. Microstructure anomaly detection produces confidence and trust adjustments,
   NOT definitive legal accusations of market manipulation.

5. Shadow decisions are first-class research assets; the system must learn
   from both the trades it executes and the trades it refuses.

6. Microstructure analysis informs; the Deterministic Risk Engine admits;
   the Execution Engine performs; the Governance Layer authorizes.

7. No heuristic or anomaly detector may bypass the Risk Engine or allocate
   unauthorized capital.
════════════════════════════════════════════════════════════════════════════════
```

---

# 28. ARCHITECTURAL DELTA REPORT

In compliance with Phase 23 requirements, this section audits the existing ACASH codebase, evaluates existing components against this amendment, and defines the future implementation roadmap.

### 28.1 Inspection of Existing ACASH Components

| Subsystem | Existing Implementation Files | Current Status & Capabilities | Amendment Delta / Gaps |
| :--- | :--- | :--- | :--- |
| **Order Book Subsystem (Phase 3B)** | `src/acash/data/orderbook/schema.py`<br>`src/acash/data/orderbook/reconstruction.py`<br>`src/acash/data/orderbook/storage.py`<br>`src/acash/data/orderbook/hashing.py` | Defines `CANONICAL_BOOK_DELTA_SCHEMA` (MBO/MBP), `CANONICAL_BOOK_SNAPSHOT_SCHEMA`, `BookAction` (`ADD`, `MODIFY`, `CANCEL`, `DELETE`, `CLEAR`), and SHA-256 depth hashing. | Currently focused on offline Parquet partition validation; lacks a streaming real-time event bus and continuous replay coordinator. |
| **Trades Domain (Phase 3A)** | `src/acash/data/trades/schema.py`<br>`src/acash/data/trades/storage.py`<br>`src/acash/data/trades/pipeline.py` | Defines `CANONICAL_TRADES_SCHEMA` with exchange timestamps, aggressor side (`BUY`, `SELL`), and trade conditions. | Static partition storage; needs unified time-synchronization with L3 book events. |
| **Microstructure Features (Phase 3C)** | `src/acash/data/features/schema.py`<br>`src/acash/data/features/engine.py`<br>`src/acash/data/features/storage.py` | Implements bar-level CVD, Delta, VWAP, absorption bars, stacked imbalances, and static OBI (Top-1, 5, 10). | Features are calculated over aggregated 1-minute bars; lacks high-frequency rolling temporal features (cancel/add velocity, pull/stack ratios, order lifetimes). |
| **Market State & Strategy Contracts (Phase 17 & 23)** | `src/acash/strategy/schema.py`<br>`docs/architecture/adaptive_multi_horizon_strategy_architecture.md` | Defines `MarketStateVector`, `MicrostructureMeasurements` (spread, effective spread, simple imbalance), `TargetPositionProposal`. | `MicrostructureMeasurements` lacks temporal cancel metrics; strategy pipeline lacks intermediate `MicrostructureCheck` stage. |
| **Risk Engine (Phase 9)** | `src/acash/risk/risk_engine.py`<br>`src/acash/risk/risk_schema.py` | Deterministic hard risk gate with `ALLOW`, `REDUCE`, `REJECT`, portfolio exposure limits, and kill switches. | Fully functional for trade admissions; currently receives only static proposals; requires interface to consume `MicrostructureContextReport`. |
| **Operational Ledger (Phase 10)** | `src/acash/runtime/ledger.py`<br>`src/acash/runtime/schema.py` | Append-only JSONL disk ledger with SHA-256 event chaining (`OperationalLedger`). | Implemented for system operational cycles; needs dedicated `ShadowDecisionRecord` schema and counterfactual tracking partition. |

### 28.2 Reusable Existing Components
ACASH possesses an exceptionally solid foundation:
1. **`src/acash/data/orderbook/schema.py`:** The `CANONICAL_BOOK_DELTA_SCHEMA` already supports both Market-By-Order (MBO) and Market-By-Price (MBP) with actions `ADD`, `MODIFY`, `CANCEL`, `DELETE`, `CLEAR`. This directly serves as the Level-3 schema baseline.
2. **`src/acash/data/features/schema.py`:** The `FeatureManifest` with SHA-256 temporal lineage DAG and parameter serialization provides the exact cryptographic lineage required for Section 6.
3. **`src/acash/runtime/ledger.py`:** The `OperationalLedger` hash-chaining engine provides the immutable persistence engine required for the Decision Ledger extension.
4. **`src/acash/risk/risk_engine.py`:** The sovereign risk gate already emits `ALLOW`, `REDUCE`, and `REJECT` verdicts, perfectly matching the required pipeline boundaries.

### 28.3 New Interfaces and Schemas Required
When advancing to implementation, the following new domain contracts must be constructed:
1. `src/acash/data/microstructure/schema.py`:
   - `CanonicalOrderBookEvent` (Extending Phase 3B delta schema for streaming).
   - `MarketDataQuality` enumeration (`COMPLETE`, `DEGRADED`, `STALE`, `PARTIAL`, `SEQUENCE_GAP`, `RECONSTRUCT_UNCERTAIN`, `INVALID`).
   - `TemporalMicrostructureFeatureVector` (imbalance persistence, cancel/add ratio, pull/stack ratio, order lifetime distribution).
2. `src/acash/research/microstructure/anomaly.py`:
   - `MicrostructureAnomalyClassification` (`MICROSTRUCTURE_NORMAL`, `MICROSTRUCTURE_CAUTION`, `MICROSTRUCTURE_ANOMALOUS`, `SUSPICIOUS_LIQUIDITY`).
   - `MicrostructureTrustAssessment` (trust score $0.0 \le \tau \le 1.0$, haircut recommendations).
3. `src/acash/research/shadow/schema.py`:
   - `ShadowDecisionRecord` (Complete counterfactual tracking DTO).
   - `CounterfactualOutcomeReport` (MFE, MAE, hypothetical PnL, filter efficiency attribution).

### 28.4 Data Storage Implications
- **Volume Scale:** Level 3 (MBO) order-book events generate massive data volume ($10^7 - 10^8$ events/day for active equity index futures or crypto perps).
- **Storage Strategy:** 
  - Raw event streams must be stored as partitioned, Snappy/ZSTD-compressed **Apache Parquet** files partitioned by `symbol`, `trading_date`, and `channel_id` (`ADR-006`).
  - Analytical feature queries will leverage **DuckDB** reading directly from Parquet.
  - Transactional operational state and shadow decision logs will utilize append-only **JSON Lines (`.jsonl`)** with cryptographic SHA-256 chaining (`OperationalLedger`).

### 28.5 Replay Engine Requirements
- Implementation of an in-memory priority queue / heap synchronizing multi-stream events by `(exchange_time_utc, sequence_number, sub_index)`.
- Synthetic clock abstraction (`ReplayClock`) driving feature calculations without system clock drift.
- Strict bi-temporal knowledge cutoff barriers preventing future record admission.

### 28.6 Test Requirements
- Implementation of the 7 Adversarial Test classes (`DATA-ADV-01` through `DATA-ADV-07`).
- Zero-variance and empty-book fail-closed assertions.
- Golden reference benchmarks comparing replay feature matrices against batch-calculated matrices.

### 28.7 Proposed Roadmap Decomposition (Future Implementation Phases)

```text
PHASE 23 (THIS RECORD) ──► Architecture Specification & Governance Boundary
        │
        ▼
PHASE 24 [PROPOSED]   ──► Market Microstructure Data Layer & L3 Normalization
                          • Streaming Venue Adapters
                          • MarketDataQuality State Machine
                          • L3 Event Validation & Parquet Storage
        │
        ▼
PHASE 25 [PROPOSED]   ──► Deterministic Microstructure Replay Engine
                          • Event-driven Replay Clock
                          • Time-ordered Book Reconstruction
                          • Zero-leakage Knowledge Barrier
        │
        ▼
PHASE 26 [PROPOSED]   ──► Temporal Feature & Anomaly Research Engine
                          • Rolling Temporal Microstructure Features
                          • Probabilistic Liquidity Fragility Detectors
                          • MicrostructureTrustAssessment Protocol
        │
        ▼
PHASE 27 [PROPOSED]   ──► Shadow Decision Evaluation & Counterfactual Learning
                          • ShadowDecisionRecord Persistence
                          • Ex-post Outcome & MFE/MAE Attribution
                          • Filter Efficiency & False-Positive Cost Solvers
        │
        ▼
PHASE 28 [PROPOSED]   ──► Adaptive Strategy Tournament & Multi-Horizon Integration
                          • Regime × Microstructure Strategy Selection
                          • Dynamic Risk Budget Modulation
                          • Unified Decision Memory Flywheel
```

---

# 29. NON-GOALS

To maintain absolute intellectual honesty and protect engineering scope, this amendment explicitly declares what it does **NOT** do:

1. **Does NOT guarantee detection of market manipulation or spoofing:** Anomaly detection identifies unusual liquidity conditions, not legal culpability.
2. **Does NOT create an automatically profitable trading strategy:** Microstructure intelligence is an observational filter, not a guarantee of alpha.
3. **Does NOT authorize High-Frequency Trading (HFT):** ACASH is an autonomous multi-horizon research and execution platform; this amendment does not build sub-microsecond FPGA execution gateways.
4. **Does NOT grant live trading authority or connect live capital:** Capital authority remains hard-locked at `$0.00`.
5. **Does NOT bypass the Deterministic Hard Risk Engine:** The Risk Engine remains the sovereign arbiter of trade admissibility.
6. **Does NOT bypass Governance:** Gate B, Rev 10, and multi-sig cryptographic boundaries remain fully intact.
7. **Does NOT replace backtesting with naive heuristics:** Rigorous statistical validation (CSCV, PBO, walk-forward) remains mandatory.
8. **Does NOT make Phantom / GhostBot a validated benchmark of truth:** External commercial systems are recorded as conceptual reference only.
9. **Does NOT authorize online self-modifying code:** Adaptive selection operates strictly within pre-compiled, admitted boundaries.

---

# 30. REQUIRED STATUS LABELS

In accordance with institutional governance standards (`AGENTS.md`), all future documentation, implementations, and empirical results relating to this amendment must be explicitly tagged using the following distinct verification states:

```text
1. ARCHITECTURAL SPECIFIED   → Formally documented in an approved architectural record.
2. IMPLEMENTED               → Python/C++ code written and committed to repository.
3. UNIT TESTED               → Passes deterministic unit tests asserting code correctness.
4. INTEGRATION TESTED        → Passes multi-component data flow and event bus tests.
5. BACKTEST VALIDATED        → Demonstrates positive expectancy in Tier-1/Tier-2 backtesting.
6. WALK-FORWARD VALIDATED    → Passes out-of-sample walk-forward matrix and PBO bounds.
7. PAPER VALIDATED           → Generates verified fills in live broker forward demo.
8. TOURNAMENT VALIDATED      → Outperforms competing models and baselines in fair tournament.
9. RISK ADMITTED             → Formally certified through Phase 17 11-Gate Admission Standard.
10. DEPLOYED                 → Authorized for live execution with non-zero capital.
```

> **NEVER collapse these states into a single generic "verified" or "done" label.**

---

## Verification Ledger

```markdown
### Verification Ledger
- Implementation Status: ARCHITECTURAL SPECIFIED (Extension Record Only; Zero Code Mutations)
- Contract Enforcement: STRICT FAIL-CLOSED (Zero Magic Constants / Silent Floors)
- Mathematical Authority: CANONICAL SPEC (Information Hierarchy Levels 1–3, Bi-Temporal Point-in-Time)
- Local Test Suite: VERIFIED (1431 passed, baseline frozen at 171b557)
- Type Checker (MyPy): VERIFIED (295 files clean, baseline frozen)
- Live Capital Authority: STRICTLY HARD-LOCKED ($0.00 Live Capital; Live Orders = 0)
- Remote CI Status: PENDING COMMIT & PUSH TO GITHUB
- Methodological Caveats: 
  1. Microstructure anomaly detection outputs probabilistic confidence/trust signals, NEVER legal claims of manipulation.
  2. Order-book snapshot data is formally recognized as insufficient for temporal microstructure research; Level-3 event streams required.
  3. External commercial systems (Phantom/GhostBot) and isolated 44-trade samples are recorded strictly as unvalidated conceptual references.
  4. Shadow decisions are research counterfactuals and must never be merged into actual trading account performance.
```
