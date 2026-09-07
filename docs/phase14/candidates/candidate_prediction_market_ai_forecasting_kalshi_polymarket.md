# ACASH Phase 14 Research Candidate Note: Kalshi + Polymarket AI Probability Forecasting, and Global Arbitrage

> **Document ID:** `docs/phase14/candidates/candidate_prediction_market_ai_forecasting_kalshi_polymarket.md`
> **Candidate Identifier:** `PREDICTION_MARKET_AI_FORECASTING_KALSHI_POLYMARKET`
> **Candidate Family:** `PREDICTION-MARKET PROBABILISTIC FORECASTING` + `GLOBAL ARBITRAGE`
> **Status:** `UNVALIDATED RESEARCH CANDIDATE` / `UNVALIDATED RESEARCH DIRECTION` | `NOT REGISTERED` | `NOT SEALED` | `NOT HYP_003`
> **Epistemic Classification:** `REPORTED / RESEARCH EVIDENCE`
> **Authority:** `AGENTS.md` (Strict Fail-Closed, Zero Unverified Claims, Single Canonical Authority), Phase 14 Master Research Architecture (`docs/phase14/phase14_master_research_architecture_plan.md`)
> **Date:** 2026-09-07

---

> [!CAUTION]
> ### HARD GOVERNANCE & SAFETY INVARIANTS
> - **THIS DOCUMENT IS A RESEARCH DIRECTION / CANDIDATE — NOT HYP_003.**
> - **NO HYPOTHESIS REGISTRATION:** Not entered into `ResearchReInceptionGate` and not registered under R1. **HYP_003 remains nonexistent.**
> - **NO IMPLEMENTATION:** Zero source-code changes. Slice 1 and Slice 2 remain UNCHANGED. No arbitrage engine, market-data connector, or crypto/FX connector is implemented.
> - **NO MARKET-DATA ACCESS:** Zero prediction-market prices, order-book snapshots, exchange quotes, or external data retrieved.
> - **NO NETWORK / INTEGRATION ACCESS:** No connection to Kalshi, Polymarket, any crypto exchange, any FX venue, or any broker.
> - **NO BACKTEST / SIMULATION / PAPER TRADE / LIVE TRADE / LLM EXECUTION:** Zero backtests, zero paper trades, zero model runs.
> - **NO DATA REUSE:** Strictly zero access to `HYP_001` partitions, `HYP_002` Validation/OOS partitions, or any 2026 Holdout. Prior hypothesis validation or OOS data may NOT be reused merely because the asset/domain differs.
> - **CAPITAL & TRADING HARD-LOCKED:** Live Capital Authority = **$0.00**; Live Trading Authority = **LOCKED**; Broker Connection = **DISCONNECTED / NONE**.

---

## 1. Document Purpose

This document registers a **research direction / research candidate** for later human review. It deliberately does **NOT** convert the idea into a formal hypothesis. There is currently no hypothesis specification, no dataset, no partition, and no falsification criteria.

Two research lines are preserved here:

1. **Prediction-market AI probability forecasting** (Kalshi + Polymarket).
2. **Global arbitrage research** across multiple market types (documentation update).

- **Central Research Question (Prediction Markets):**
  > *"Can an AI agent identify probabilistic mispricing relative to prediction-market consensus?"*

- **Central Research Question (Global Arbitrage):**
  > *"Under what verified conditions, if any, do observed cross-market price discrepancies constitute bounded-risk, executable, economically equivalent arbitrage?"*

This document is a **RESEARCH DIRECTION / CANDIDATE ONLY**. It is **NOT**:
- `HYP_003`
- a validated strategy
- an alpha
- a trading system
- an execution specification
- evidence of profitability

---

## 2. Epistemic Status (Strict Labeling)

The supplied Prediction Arena material is classified as:

$$\boxed{\text{REPORTED / RESEARCH EVIDENCE}}$$

The entire Global Arbitrage section is classified as:

$$\boxed{\text{UNVALIDATED RESEARCH DIRECTION}}$$

All numerical examples in this document are:

$$\boxed{\text{ILLUSTRATIVE ONLY}}$$

Any empirical claims copied from external material remain:

$$\boxed{\text{REPORTED / RESEARCH EVIDENCE}}$$

unless independently verified.

Reported results are **NOT** converted into VERIFIED facts. The following claims remain explicitly labeled **REPORTED** unless independently verified later:

| Claim | Epistemic Status |
|---|---|
| AI agents were evaluated on Kalshi and Polymarket | `REPORTED` |
| The reported 57-day evaluation period | `REPORTED` |
| Reported Kalshi losses | `REPORTED` |
| Reported Polymarket aggregate performance | `REPORTED` |
| Reported model-by-model returns | `REPORTED` |
| Reported market selection | `REPORTED` |
| Reported weather-market concentration | `REPORTED` |

These claims must not be silently corrected, expanded, or reinterpreted.

---

## 3. Research Rationale: Why Prediction Markets Are Interesting

Prediction markets offer structural properties that make them candidates for AI research:

1. **Binary/event outcomes provide clear ground truth.**
2. **Market prices can be interpreted as market-implied probabilities**, subject to the exact contract/market mechanics.
3. **AI probability forecasts can be compared against:**
   - AI probability
   - vs. market probability
   - vs. realized outcome
4. **This enables evaluation using:**
   - calibration
   - Brier score
   - log loss
   - expected value
   - market-vs-model probability edge
   - execution cost
   - spread
   - slippage
   - PnL
   - drawdown
   - resolution accuracy

### The Key Research Standard

$$\boxed{\text{AI being correct is NOT sufficient.}}$$

The relevant question is whether AI can produce a probability estimate that is **superior to the market consensus after appropriate costs and uncertainty**.

---

## 4. Candidate Research Directions (Distinct Problems — Do Not Combine)

### 4.1 Prediction-Market Direction Ranking

| Rank | Direction | Identifier |
|---|---|---|
| **PRIMARY** | AI probability forecasting vs. market consensus | `PM-AI-FORECAST` |
| **SECONDARY** | Cross-market arbitrage: Kalshi ↔ Polymarket | `PM-CROSS-ARB` |
| **TERTIARY** | Prediction-market market making | `PM-MARKET-MAKING` |

### 4.2 High-Priority Parallel Direction

| Priority | Direction | Identifier |
|---|---|---|
| **HIGH (PARALLEL)** | Global arbitrage research across market types | `GA-ARBITRAGE` |

These are **distinct research problems**. They must NOT be combined into one hypothesis.

---

## 5. PRIMARY DIRECTION — AI Probability Forecasting vs. Market Consensus

### 5.1 Conceptual Design (Illustrative)

For an event:

- Market probability: $P_{market}$
- AI probability: $P_{AI}$
- Potential informational discrepancy: $\Delta = P_{AI} - P_{market}$

**Illustrative example only:**

$$P_{market} = 0.42 \qquad P_{AI} = 0.57 \qquad \Delta = +0.15$$

> [!WARNING]
> This example is **illustrative only**. It is **NOT a trading signal** and **NOT evidence of edge**.

### 5.2 Potential Evaluation Pipeline

$$\text{forecast probability} \to \text{market probability} \to \text{eventual resolution} \to \text{calibration} \to \text{scoring} \to \text{cost-adjusted economic value}$$

---

## 6. SECONDARY DIRECTION — Prediction-Market Cross-Arbitrage (Kalshi ↔ Polymarket)

### 6.1 Potential Research Question

> *"Do economically equivalent event contracts on Kalshi and Polymarket ever exhibit exploitable probability/price discrepancies after accounting for fees, settlement rules, timing, liquidity, and execution constraints?"*

### 6.2 Illustrative Example (ILLUSTRATIVE ONLY)

Kalshi: YES = 47¢

Polymarket: YES = 52¢

**Naive interpretation:** $52 - 47 = 5\text{¢}$ apparent discrepancy.

But this is **NOT automatically arbitrage**. Before calling it arbitrage, verify:
- same event
- same outcome definition
- same resolution criteria
- same resolution source
- same deadline
- same settlement mechanics
- same economic exposure
- fees
- bid/ask spread
- available liquidity
- position limits
- execution timing
- settlement/counterparty conditions

### 6.3 Major Research Risks (Explicit)

- contracts may not be semantically identical
- resolution criteria may differ
- settlement timing may differ
- liquidity may differ
- fees may differ
- execution latency may matter
- jurisdiction/access may differ
- apparent price discrepancies may not represent true arbitrage

$$\boxed{\text{PRICE DIFFERENCE} \neq \text{ARBITRAGE}}$$

This document does **NOT** claim arbitrage exists.

---

## 7. TERTIARY DIRECTION — Prediction-Market Market Making

Market making is recorded as a **separate, harder research direction**.

### 7.1 Key Concepts

- bid/ask spread
- inventory risk
- adverse selection
- information asymmetry
- queue position
- latency
- liquidity
- order-book dynamics

### 7.2 Critical Boundary Statement

$$\boxed{\text{Spread capture alone does NOT imply positive expected PnL.}}$$

A market maker can be **adversely selected** when informed flow arrives. This direction therefore requires **microstructure research before strategy research**.

---

## 8. GLOBAL ARBITRAGE RESEARCH DIRECTION

### 8.1 Core Research Idea

Arbitrage should be researched **globally across multiple market types** rather than being restricted to Kalshi/Polymarket.

**Core principle:**

$$\boxed{\text{Observed price discrepancy} \neq \text{arbitrage.}}$$

A candidate discrepancy becomes a potential arbitrage opportunity **only after** all of the following:

```
Observed price discrepancy
        ↓
Candidate
        ↓
Semantic / economic equivalence verified
        ↓
Executable prices verified
        ↓
All fees and transaction costs included
        ↓
Liquidity / quantity verified
        ↓
Both legs executable
        ↓
Timing / latency constraints verified
        ↓
Settlement / counterparty conditions verified
        ↓
Positive bounded-risk payoff
        ↓
ARBITRAGE CANDIDATE FOR FORMAL RESEARCH
```

Use careful language. This document does **not** claim that profitable arbitrage currently exists.

### 8.2 Core Governance Principle: Arbitrage Candidate ≠ Arbitrage

> **Formal:**
> "An arbitrage candidate is an observed or inferred pricing inconsistency that warrants further investigation. It is **not considered arbitrage** until economic equivalence, executable prices, costs, liquidity, timing, settlement, and bounded-risk payoff have been **independently verified**."

$$\boxed{\text{ARBITRAGE CANDIDATE} \neq \text{ARBITRAGE}}$$

### 8.3 Research Families & Provisional Priority

These are **RESEARCH FAMILIES**, not approved strategies.

| Priority | Family | Identifier |
|---|---|---|
| **VERY HIGH** | Prediction-market cross-platform arbitrage (Kalshi ↔ Polymarket) | `GA-PM-CROSS` |
| **VERY HIGH** | Crypto cross-venue / cross-exchange arbitrage | `GA-CRYPTO-CROSS` |
| **HIGH** | ETF ↔ NAV / underlying basket relationships | `GA-ETF-NAV` |
| **HIGH** | FX triangular / multi-venue arbitrage | `GA-FX-TRI` |
| **HIGH** | Futures ↔ spot / basis / calendar relationships | `GA-FUT-BASIS` |

#### Family 1 — Prediction-Market Cross-Platform (Illustrative Only)

Refer to Section 6.2: a `47¢ vs 52¢` appearance is a candidate, not arbitrage.

#### Family 2 — Crypto Cross-Venue (Illustrative Only)

BTC: Venue A = $100,000 | Venue B = $100,080

Potential gross discrepancy = $80.

But research must account for:
- maker/taker fees
- spread
- slippage
- withdrawal/deposit costs
- transfer latency
- funding
- inventory
- counterparty risk
- settlement finality
- execution latency
- available quantity

$$\boxed{\text{Do NOT claim that observed exchange differences are executable profit.}}$$

#### Family 3 — ETF ↔ NAV / Underlying

Research relationship:

$$\text{ETF market price vs NAV vs underlying basket / fair value}$$

Research questions:
- how quickly do deviations close?
- what is actually executable?
- what creation/redemption mechanism is available?
- what costs apply?
- what access constraints exist?
- can a retail participant actually capture the theoretical spread?

Distinguish explicitly:

$$\text{THEORETICAL ARBITRAGE} \neq \text{RETAIL-EXECUTABLE ARBITRAGE}$$

#### Family 4 — FX Triangular / Multi-Venue

Research relationships such as:

$$\text{USD/JPY} \quad \text{EUR/USD} \quad \text{EUR/JPY}$$

Potential loop:

$$\text{USD} \to \text{JPY} \to \text{EUR} \to \text{USD}$$

Research must include:
- executable bid/ask prices
- spread
- fees
- latency
- quote staleness
- venue differences
- available size

$$\boxed{\text{Do NOT claim persistent profit.}}$$

Recognize that this research family may become a **latency / HFT problem**.

#### Family 5 — Futures ↔ Spot / Basis / Calendar

Potential relationships:

$$\text{spot} \leftrightarrow \text{futures} \qquad \text{near contract} \leftrightarrow \text{far contract} \qquad \text{basis} \leftrightarrow \text{implied financing / carry}$$

Research must account for:
- funding/carry
- expiry
- roll mechanics
- margin
- transaction costs
- basis risk
- liquidity
- settlement
- execution

$$\boxed{\text{Do NOT treat simple price convergence as guaranteed profit.}}$$

### 8.4 Global Arbitrage Research Engine — CONCEPT ONLY

The following is a **conceptual architecture only**. Do **NOT** implement it.

```
GLOBAL MARKETS
      │
      ├── Prediction Markets
      ├── Crypto Venues
      ├── FX Venues
      ├── ETFs / Underlyings
      └── Futures / Spot
               │
               ▼
       OPPORTUNITY DETECTOR
               │
               ▼
       SEMANTIC / ASSET MATCH
               │
               ▼
       PRICE CONSISTENCY CHECK
               │
               ▼
       COST / FRICTION MODEL
               │
               ▼
       EXECUTABLE EDGE?
          │          │
         NO         YES
          │          │
       discard    REFEREE
                     │
                     ▼
              PAPER RESEARCH
```

### 8.5 AI Role (Proposition — No Authority)

AI may eventually assist with:
- identifying potentially equivalent assets/contracts
- parsing market rules
- interpreting contract semantics
- discovering relationships
- gathering external evidence
- proposing candidate opportunities

But AI must **NOT** have authority to declare:
- arbitrage
- guaranteed profit
- executable edge
- strategy qualification
- trading authorization

### 8.6 Deterministic Referee Role (Verification — Sole Authority)

A future deterministic referee should be responsible for:
- exact executable prices
- bid/ask
- fees
- spread
- quantity
- liquidity
- latency
- settlement
- execution sequence
- counterparty constraints
- net PnL
- worst-case / bounded-risk payoff

$$\boxed{\text{AI PROPOSES} \quad \longrightarrow \quad \text{DETERMINISTIC REFEREE VERIFIES}}$$

### 8.7 Global Arbitrage Priority

- **Primary research direction:** AI probability forecasting vs. market consensus.
- **High-priority parallel research direction:** GLOBAL ARBITRAGE.

Initial arbitrage priority (provisional — NOT a final research decision):

1. Prediction-market cross-platform
2. Crypto cross-venue
3. FX multi-venue / triangular
4. ETF/NAV/underlying
5. Futures/spot/basis/calendar

---

## 9. Kalshi / Polymarket Comparison (Research-Oriented Only)

This document does **NOT** declare one platform universally superior. It records only the **research-oriented distinction**:

| Platform | Research-Oriented Characterization |
|---|---|
| **Kalshi** | Useful candidate environment for regulated prediction-market research; event-contract structure; potentially useful market/order-book data; suitable for probabilistic forecasting research. |
| **Polymarket** | Useful candidate environment for broader/global event research; prediction-market/order-book structure; potentially useful for cross-market comparison. |

> [!CAUTION]
> This document makes **NO** regulatory, fee, accessibility, or API claims unless independently sourced and cited later. This is a **research candidate**, not a platform due-diligence report.

---

## 10. IMPORTANT PAPER EVIDENCE

- **Title:** "Prediction Arena: Benchmarking AI Models on Real-World Prediction Markets"
- **Reference:** arXiv:2604.07355 (as supplied)
- **Classification:** `REPORTED / RESEARCH EVIDENCE`

### 10.1 Mandatory Interpretation Constraint

The reported AI losses on Kalshi must **NOT** be interpreted as *"Kalshi is a bad market."*

The material itself identifies possible **interaction effects** involving:
- model capability
- weather forecasting difficulty
- market structure
- execution/liquidity
- curated market selection

$$\boxed{\text{AI losses} \neq \text{proof that Kalshi is inefficient or unusable.}}$$

---

## 11. IMPORTANT RESEARCH BASELINE (Market Calibration)

Before testing whether AI can beat a prediction market, ACASH must establish:

> *"How well calibrated is the market itself?"*

The supplied material references a **separate Kalshi calibration study**. That study is kept as:

$$\boxed{\text{REPORTED / SOURCE TO VERIFY}}$$

Its numerical findings must **NOT** be independently asserted as VERIFIED. Future research should establish an **empirical market baseline** before evaluating AI outperformance.

---

## 12. Relation to Phase 14 Architecture

This candidate could eventually fit the existing Phase 14 pipeline:

$$\text{SOURCE} \to \text{RETRIEVAL} \to \text{PROVENANCE} \to \text{EVIDENCE} \to \text{RESEARCH ANALYSIS} \to \text{REFEREE / VALIDATION}$$

### 12.1 Future Conceptual Flow (For Global Arbitrage)

$$\text{SOURCE} \to \text{RETRIEVAL} \to \text{PROVENANCE} \to \text{EVIDENCE} \to \text{MARKET / CONTRACT ANALYSIS} \to \text{ARBITRAGE CANDIDATE} \to \text{DETERMINISTIC REFEREE} \to \text{FORMAL RESEARCH}$$

### 12.2 Potential Future Evidence Inputs

- prediction-market prices
- order-book snapshots
- market rules
- resolution criteria
- external evidence sources
- event timestamps
- final settlement outcomes

> [!CAUTION]
> **DO NOT implement these now.** Slice 2 remains unchanged. The future layers (MARKET / CONTRACT ANALYSIS, ARBITRAGE CANDIDATE, DETERMINISTIC REFEREE) are **NOT** implemented.

---

## 13. Relationship to Slice 1 / Slice 2

- **Slice 1** — UNCHANGED by this document.
- **Slice 2** (`src/acash/research/ai/retrieval/`) — UNCHANGED by this document.
- This candidate is a **future consumer** of the Phase 14 SOURCE → RETRIEVAL → PROVENANCE → EVIDENCE chain, not a modification of it.

---

## 14. Governance

This documentation does **NOT** authorize:
- `HYP_003`
- hypothesis registration
- data acquisition
- live market connectivity
- backtesting
- paper trading
- live trading
- strategy qualification
- capital allocation

**HYP_003 remains NOT CREATED.**

The candidate must pass through the **same research governance discipline** as any future hypothesis. No prior `HYP_001`/`HYP_002` validation or OOS data may be reused merely because the asset/domain is different.

---

## 15. Proposed Future Research Questions (OPEN QUESTIONS — Not Claims)

| ID | Open Question |
|---|---|
| RQ1 | Can AI probability forecasts outperform market-implied probabilities after proper calibration and costs? |
| RQ2 | Does AI provide incremental information beyond market consensus? |
| RQ3 | Which evidence types actually improve probability forecasts? |
| RQ4 | Does performance persist across event categories? |
| RQ5 | Does performance persist out-of-sample and across time? |
| RQ6 | Are apparent Kalshi/Polymarket discrepancies true arbitrage after contract semantics and costs? |
| RQ7 | Can a market-making strategy survive adverse selection and inventory risk? |
| RQ8 | Does AI improve market-making decisions, or merely increase trading activity? |

---

## 16. Research Risks

### 16.1 Prediction-Market Risks

- selection bias
- hindsight bias
- look-ahead bias
- resolution-rule ambiguity
- contract-semantic mismatch
- liquidity bias
- survivorship bias
- changing market structure
- transaction costs
- spread/slippage
- event leakage
- information timestamp leakage
- model calibration failure
- overfitting across event categories
- multiple testing
- AI-generated narrative masquerading as evidence

### 16.2 Global Arbitrage Risks

- false equivalence
- contract semantic mismatch
- stale quotes
- bid/ask illusion
- insufficient liquidity
- transaction costs
- hidden fees
- latency
- partial fills
- legging risk
- settlement mismatch
- counterparty risk
- transfer restrictions
- funding/carry
- margin requirements
- market access restrictions
- regulatory constraints
- survivorship bias
- look-ahead bias
- selection bias
- multiple testing
- overfitting
- theoretical vs. executable arbitrage

---

## 17. Recommended Initial Path

$$\text{PRIMARY: AI probability forecasting vs. market consensus}$$

**High-priority parallel research direction:**

$$\text{GLOBAL ARBITRAGE}$$

Within global arbitrage, the provisional initial priority is prediction-market cross-platform and crypto cross-venue research — each as **research families**, not approved strategies.

**Reason:** Forecasting provides the cleanest initial scientific question and aligns most directly with the Phase 14 Evidence → Research Analysis architecture. Global arbitrage is preserved as a parallel research line without premature strategy conversion.

---

## 18. Source References

| # | Reference | Classification | Status |
|---|---|---|---|
| 1 | "Prediction Arena: Benchmarking AI Models on Real-World Prediction Markets" — arXiv:2604.07355 | `REPORTED / RESEARCH EVIDENCE` | TO VERIFY |
| 2 | Referenced Kalshi calibration study (as cited within the supplied material) | `REPORTED / SOURCE TO VERIFY` | TO VERIFY |

No primary sources were independently fetched, connected to, or verified during documentation. This document records the idea only.

---

## 19. Conditions Required Before Any Future Step

This candidate **CANNOT** advance toward any hypothesis registration until, at minimum:
1. [ ] **Human Review of this Research Direction**
2. [ ] **Human Authorization** of the Phase 14 architecture and any candidate admission path.
3. [ ] **Independent evidence sourcing** that upgrades the REPORTED material to VERIFIED, or documents the source as unverifiable.
4. [ ] **Explicit falsification criteria and dataset/partition design** authored from primary principles (no reuse of `HYP_001`/`HYP_002` data).
5. [ ] **Formal ResearchReInceptionGate consideration** (`src/acash/research/reinception.py`), if and only if later directed by human review.

---

## 20. Human Decision Checkpoint

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    RESEARCH DIRECTION REGISTRATION VERDICT                │
├───────────────────────────────────┬───────────────────────────────────────┤
│ Candidate Identifier              │ PREDICTION_MARKET_AI_FORECASTING_     │
│                                   │ KALSHI_POLYMARKET                     │
│ Direction Family                  │ PREDICTION-MARKET PROBABILISTIC       │
│                                   │ FORECASTING + GLOBAL ARBITRAGE        │
│ Status                            │ UNVALIDATED RESEARCH DIRECTION        │
│ Epistemic State                   │ REPORTED / RESEARCH EVIDENCE          │
│                                   │ (ILLUSTRATIVES = ILLUSTRATIVE ONLY)   │
│ HYP_003 Creation                  │ NOT CREATED / PROHIBITED              │
│ Implementation                    │ NONE                                  │
│ Trading                           │ LOCKED                                │
│ Next Action                       │ HUMAN REVIEW                          │
└───────────────────────────────────┴───────────────────────────────────────┘
```

**Recorded Result:**
- **Research Direction:** KALSHI + POLYMARKET AI PROBABILITY FORECASTING + GLOBAL ARBITRAGE
- **Status:** UNVALIDATED RESEARCH CANDIDATE / UNVALIDATED RESEARCH DIRECTION
- **Epistemic:** REPORTED / RESEARCH EVIDENCE
- **HYP_003:** NOT CREATED
- **Implementation:** NONE
- **Trading:** LOCKED
- **Next action:** HUMAN REVIEW

**STOP.**