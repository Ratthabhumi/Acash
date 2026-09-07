# ACASH Research Candidate Note: NY Open First 5-Minute Candle / EMA12 Directional Strategy

> **Document ID:** `docs/phase14/candidates/candidate_ny_open_first5_ema12.md`  
> **Status:** UNVALIDATED PROPOSAL — CANDIDATE INTAKE ONLY  
> **Date:** 2026-09-07  
> **Authority:** `AGENTS.md` (Strict Fail-Closed, Zero Unverified Claims, Single Canonical Authority), Phase 14 Master Architecture (`docs/phase14/phase14_master_research_architecture_plan.md`), Strategy Admission Standard (Phase 17 / ADR-023)  

---

> [!CAUTION]
> ### FORMAL GOVERNANCE & EPISTEMIC BOUNDARY DECLARATION
> - **NOT REGISTERED:** This candidate is NOT registered in the canonical research registry.
> - **NOT SEALED:** No hypothesis specification or parameter space is cryptographically sealed.
> - **NO MARKET DATA ACCESSED:** Zero market data feeds, parquet files, or historical bars have been accessed or queried.
> - **NO BACKTEST EXECUTED:** Zero backtests, simulations, or trial computations have been conducted.
> - **NO TRADING AUTHORITY:** Live Capital Authority remains strictly locked at **$0.00**; Live Trading Authority is **LOCKED**; Broker Connection is **DISCONNECTED / NONE**.
> - **THIS NOTE IS NOT AUTHORIZATION TO CREATE HYP_003.**

---

## 1. Candidate Identity

- **Working Title:** NY Open First 5-Minute Candle / EMA(12) Intraday Directional Strategy
- **Candidate Identifier:** `CAND-NY-OPEN-FIRST5-EMA12-001`
- **Candidate Family:** Opening-session / intraday event-conditioned directional signal
- **Target Asset Class:** Equity Index Futures / CFDs (Claimed: NASDAQ 100 / NQ / US100)
- **Claimed Primary Bar Timeframe:** 5-minute (M5)
- **Claimed Event Anchor:** First 5-minute bar after the New York Cash Equity Market Open (09:30–09:35 ET)
- **Claimed Conditioning Indicator:** Exponential Moving Average of length 12 ($\text{EMA}_{12}$)

---

## 2. Source Claim & Epistemic Demarcation

### 2.1 Source Attribution
- **Origin Channel:** External media / video transcription (`source_type: SOCIAL / VIDEO`)
- **Evidence Role:** `HYPOTHESIS_SOURCE` (Unverified external claim)
- **Verification Status:** `UNVERIFIED` (100% self-reported by creator)

### 2.2 Unverified Self-Reported Metrics
The source asserts the following performance figures:
- **Claimed Cumulative Return:** $+406\%$ (over claimed historical window)
- **Claimed Maximum Drawdown:** $19\%$
- **Claimed Historical Period:** Approximately 7 years
- **Claimed Operational Status:** Claimed to be operating live on a proprietary "funded account"
- **Claimed Risk Allocation:** $1\%$ account risk per trade

### 2.3 Epistemic Classification
In accordance with ACASH core research guidelines:
$$\boxed{\text{Observed/Claimed Profit} \neq \text{Proven Skill} \neq \text{Structural Edge} \neq \text{Luck-Free Performance}}$$

Every figure above is formally classified as:
$$\text{Status} = \mathbf{SELF\text{-}REPORTED} \ / \ \mathbf{UNVERIFIED}$$

**Under zero circumstances will these self-reported figures be accepted as empirical evidence, nor will they influence statistical rejection hurdles, parameter tuning, or data window selection in ACASH.**

---

## 3. Transcript-Derived Rules (Nominal Specification)

From the supplied transcript, the nominal rule set consists solely of the following:

1. **Session Timing & Trigger Event:**
   - Wait for the open of the New York cash equity session (09:30 Eastern Time).
   - Form the first 5-minute bar (09:30:00 to 09:34:59 ET).
2. **Conditioning Indicator Calculation:**
   - Compute a 12-period Exponential Moving Average ($\text{EMA}_{12}$) on 5-minute bars.
3. **Directional Entry Signal (at 09:35:00 ET close/open):**
   - **LONG:** If $\text{Close}_{\text{bar 1}} > \text{EMA}_{12}(\text{bar 1})$
   - **SHORT:** If $\text{Close}_{\text{bar 1}} < \text{EMA}_{12}(\text{bar 1})$
   - **FLAT / NO TRADE:** Undefined if $\text{Close}_{\text{bar 1}} == \text{EMA}_{12}(\text{bar 1})$ (tie policy missing).
4. **Execution Timing:**
   - Decision executed immediately at the close of the first 5-minute candle.
   - No secondary filter, confirmation bar, or volume threshold mentioned in the core rule.
5. **Reported Frequency:**
   - Exactly one directional decision per trading day.

---

## 4. Explicitly Unknown & Ambiguous Rules (Unresolved Specification Gaps)

The source material completely fails to specify an institutionally reproducible quantitative contract. The following parameters and operational details are **EXPLICITLY UNKNOWN**:

| Dimension | Ambiguity / Missing Specification | Current Classification |
|---|---|---|
| **Instrument & Contract Proxy** | Whether signals are computed on CME E-mini NASDAQ (NQ futures), Micro E-mini (MNQ), Cash Index (NDX), or Broker CFD (US100 / NAS100). Futures roll policy and contract month switching are absent. | **UNKNOWN** |
| **Timezone & Session Anchor** | Exact timezone definition, handling of US Daylight Saving Time (EDT vs EST) shifts relative to UTC or non-US servers. | **UNKNOWN** |
| **EMA Initialization & History** | Warm-up lookback window for $\text{EMA}_{12}$. Whether EMA is computed across overnight/pre-market Globex bars (00:00–09:30 ET) or solely RTH bars (Regular Trading Hours), and how overnight sessions reset. | **UNKNOWN** |
| **Execution Fill & Friction** | Assumed execution price (M5 close vs next open tick), bid-ask spread, slippage model at the volatile 09:35 open, exchange fees, and NFA clearing costs. | **UNKNOWN** |
| **Stop-Loss Specification** | Mentioned ambiguously as "according to first-candle range" (e.g. high/low of bar 1? high/low $\pm$ buffer? entry $\pm$ range?). No exact formula provided. | **NOT PROVEN / UNKNOWN** |
| **Trailing-Stop Algorithm** | Mentioned in related commentary, but zero mathematical formula, ratchet trigger, or step size is defined. | **NOT PROVEN / UNKNOWN** |
| **Target Horizon / Exit Timing** | Transcript states "trade the entire day" in one sentence and "next six hours" in another. No deterministic exit rule (e.g., 15:55 ET MOC, 16:00 ET close, time stop, or opposite signal). | **NOT PROVEN / AMBIGUOUS** |
| **Position Sizing Formula** | How "1% account risk" is translated into integer contracts or lot sizes given a dynamic dollar range stop and tick value. | **UNKNOWN** |
| **Holiday / Half-Day Sessions** | Behavior during early closes (Thanksgiving Friday, Christmas Eve), major economic releases at 09:30 (e.g., CPI/NFP coinciding with the open bar). | **UNKNOWN** |

**Rule:** ACASH research will never silently invent, guess, or optimize these parameters to fit historical data.

---

## 5. Evidence Classification (Epistemic Matrix)

In accordance with Phase 14 / Phase 17 taxonomy:

| Component | Source Statement | ACASH Epistemic Classification | Rationale |
|---|---|---|---|
| **First-Bar EMA Directional Bias** | Close vs EMA(12) determines day trend | `UNVALIDATED HYPOTHESIS` | Unproven statistical correlation; requires independent econometric test. |
| **Stop-Loss Logic** | "Stop loss according to first-candle range" | `NOT PROVEN / INFERRED` | Ambiguous verbal description without exact algorithmic equation. |
| **Trailing-Stop Logic** | Trailing behavior mentioned in ancillary commentary | `NOT PROVEN / SPECULATIVE` | No operational rules or triggers provided. |
| **Holding Period** | "Trade entire day" vs "next 6 hours" | `AMBIGUOUS / UNRESOLVED` | Internal contradiction in source material. |
| **Claimed PnL (+406%)** | "+406% cumulative return over ~7 years" | `SELF-REPORTED / UNVERIFIED` | Zero audit trail, zero execution logs, unverified marketing claim. |
| **Claimed Drawdown (19%)** | "Max drawdown was 19%" | `SELF-REPORTED / UNVERIFIED` | Subject to survivorship bias, curve-fitting, and unknown capital denominator. |
| **Funded Live Track Record** | Strategy is running live on funded account | `SELF-REPORTED / UNVERIFIED` | No independent broker statement or cryptographic verification. |

---

## 6. Economic & Behavioral Mechanisms to Investigate

Before any empirical work, an economic mechanism must justify why directional information might exist at the 09:35 boundary:

1. **Institutional Price Discovery & Order Imbalance:**
   - Cash equity open (09:30 ET) brings the aggregation of overnight order flow, mutual fund net flows, and opening cross-auctions on NYSE/NASDAQ.
   - Initial 5-minute directional momentum could reflect inventory digestion and institutional execution algorithms (TWAP/VWAP programs commencing at 09:35 ET).
2. **Overnight vs Intraday Drift (Session Momentum):**
   - The relation between the 09:35 price and the 12-bar EMA (spanning the immediate pre-market/early open) might capture whether the opening auction confirmed or rejected the overnight Globex direction.
3. **Counter-Hypothesis (Random Noise / Auction Mean Reversion):**
   - The first 5 to 15 minutes of the US equity open feature the highest volatility, widest spreads, and maximum institutional manipulation of the day.
   - Opening bars frequently form liquidity sweeps (false breakouts) that mean-revert once opening crosses conclude, rendering a pure momentum rule severely unprofitable after spreads.

---

## 7. Risks of Overfitting, Data Snooping & Survivorship Bias

1. **Magic Constant Vulnerability ($\text{EMA}_{12}$):**
   - Why period 12? In 5-minute space, 12 periods = 60 minutes (1 hour). If period 12 was chosen after testing periods 5, 8, 9, 10, 12, 15, 20, 50, then $\text{EMA}_{12}$ is a post-hoc curve-fit selection from an unrecorded multiple-testing trial space ($K$).
2. **Single-Bar Brittleness:**
   - Conditioned on exactly one 5-minute candle. A single large trade or quote tick at 09:34:59 can flip the signal from Long to Short, introducing extreme sensitivity to microscopic market microstructure noise.
3. **Execution Gap (Friction Erasure):**
   - Claimed $+406\%$ returns frequently assume mid-quote entry with zero slippage. In reality, market orders on NQ at 09:35:00 encounter severe bid-ask bounce and slippage (often 1–4 ticks or 0.25–1.00 index points per side), which can completely erode gross returns across ~250 trades/year.
4. **Survivorship & Publication Bias:**
   - Social media and retail educational sources present only strategies that showed positive sample runs, omitting dozens of failed variations (the classic "file-drawer effect").

---

## 8. Reproducibility Requirements

Prior to any formal consideration as an institutional research candidate, the following engineering prerequisites must be satisfied:

1. **Authoritative Market Data Specification:**
   - CME NQ continuous futures dataset with explicit roll policy (e.g., volume-based roll on Thursday prior to expiry) OR spot cash NDX index with explicit proxy execution model.
   - High-fidelity tick or 1-minute historical data with verified UTC timestamps.
2. **Deterministic Timezone Mapping:**
   - UTC-canonical timestamps accounting for US DST shifts (EDT = UTC-4, EST = UTC-5).
3. **Formalized Cost & Friction Model:**
   - Round-turn commission: $4.50 per standard NQ contract ($1.50 per MNQ).
   - Minimum slippage: $\ge 1$ tick ($0.25 index point) entry and $\ge 1$ tick exit.
   - Historical bid-ask spread accounting during 09:30–09:35 open volatility.
4. **Explicit State Machine:**
   - Deterministic mathematical definition for:
     - Entry price
     - Stop-loss calculation
     - Profit target / trailing logic (or explicit exclusion if fixed time exit)
     - Mandatory flat time (e.g. 15:55 ET).

---

## 9. Proposed Research Questions (Objective Scientific Form)

The candidate research question must not assume profitability:

> **Primary Research Question:**  
> *"Does the directional relationship between the close of the first 5-minute New York equity market candle (09:30–09:35 ET) and its 12-period Exponential Moving Average contain statistically significant predictive information regarding subsequent intraday NQ price returns, after accounting for execution frictions, time-varying volatility, and multiple-testing deflation?"*

> **Secondary Econometric Invariant Questions:**  
> 1. Is any observed directional correlation stationary across bull, bear, and high-volatility regimes (e.g. 2020 COVID, 2022 rate hike cycle, 2023–2024 tech rally)?  
> 2. Does the signal survive when varying the EMA parameter $\tau \in [8, 24]$, or does performance collapse outside $\tau=12$ (proving curve-fitting)?  
> 3. Does the first 5-minute bar exhibit greater predictive power than the first 15-minute or 30-minute opening range?  
> 4. Does the gross edge exceed the realistic cost of crossing the spread at 09:35:00 ET?

---

## 10. Reasons the Candidate May Be Rejected at Intake

This candidate will be rejected without advancing to R1 if:
1. **Unresolvable Operational Specification:** The original claim cannot be mathematically formalized without inventing arbitrary rules.
2. **Microstructure Frictions Exceed Gross Theoretical Edge:** If average gross intraday return per trade is less than the round-turn spread and slippage cost ($\sim 1.5\text{--}2.0\text{ ticks}$).
3. **Data Snooping Signature:** If the signal's historical performance exists exclusively for $\text{EMA}_{12}$ and vanishes for $\text{EMA}_{10}$ or $\text{EMA}_{14}$.
4. **Failure to Pass ResearchReInceptionGate:** If the proposed design attempts to reuse existing quarantined holdouts or fails to present a falsifiable statistical pre-registration.

---

## 11. Conditions Required Before Any Future R1 Consideration

The candidate CANNOT be proposed for Step R1 (Hypothesis Pre-Registration) until:
- [ ] Phase 14 Master Research Architecture (`docs/phase14/phase14_master_research_architecture_plan.md`) receives formal Human Approval.
- [ ] Research Intelligence intake review completes evidence and mechanism audit.
- [ ] Exact mathematical formulation of entry, exit, stop, and sizing is authored without ambiguity.
- [ ] Independent CME NQ / US100 data source and canonical schema are verified.
- [ ] Formal review by Human Quantitative Auditor is recorded.
- [ ] The proposal successfully passes the `ResearchReInceptionGate` in `src/acash/research/reinception.py`.

---

## 12. Methodological Comparison with Existing Hypotheses

| Dimension | `HYP_001` (EURUSD M5) | `HYP_002` (EURUSD H4) | Candidate `CAND-NY-OPEN-FIRST5-EMA12-001` |
|---|---|---|---|
| **Asset Class** | FX Spot (EURUSD) | FX Spot (EURUSD) | Equity Index Futures (CME NQ / US100) |
| **Strategy Family** | Univariate unconditional time-series momentum | Univariate unconditional time-series momentum | Opening-session event conditioning + trend filter |
| **Conditioning** | None (continuous rolling lookbacks) | None (continuous rolling lookbacks) | Single opening-session event (09:30–09:35 ET) |
| **Status** | **TERMINALLY FALSIFIED / CLOSED** | **TERMINALLY FALSIFIED / CLOSED** | **UNVALIDATED PROPOSAL / CANDIDATE INTAKE** |
| **Lifecycle Reached** | R1 $\to$ R2 $\to$ R3 (0/9 qualified) | R1 $\to$ R2 $\to$ R3 (0/12 qualified) | Pre-R1 Intake (Design Note Only) |
| **Quarantine Boundary** | 2026 M5 Holdout (6060..9999) | H4 Val (3751..4996) + OOS (5009..6230) | **Zero overlap allowed** (NQ is separate asset) |

> [!NOTE]
> This candidate represents an entirely distinct research family (event-conditioned intraday equity index vs unconditional FX momentum). **This distinction implies zero claim of superiority.** It simply indicates that the econometric failure of `HYP_001` and `HYP_002` does not mechanically invalidate an intraday equity opening hypothesis, nor does it grant this candidate any presumption of validity.

---

## 13. Data Quarantine & Isolation Compliance

- **EURUSD Quarantined Partitions:**
  - `HYP_001` 2026 M5 Holdout (bars 6060..9999): **STRICTLY QUARANTINED / UNTOUCHED**
  - `HYP_002` H4 Validation Partition (bars 3751..4996): **STRICTLY QUARANTINED / UNTOUCHED**
  - `HYP_002` H4 Blind OOS Partition (bars 5009..6230): **STRICTLY QUARANTINED / UNTOUCHED**
- **Instrument Isolation:** NQ / US100 is an independent equity index instrument. Under no circumstances will FX datasets or quarantined FX partitions be referenced or contaminated.
- **Cross-Hypothesis Data Quarantine Invariant:** Preserved 100%.

---

## 14. Epistemic Summary & Next Action

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    RESEARCH CANDIDATE INTAKE LEDGER                       │
├───────────────────────────────────┬───────────────────────────────────────┤
│ Candidate Identifier              │ CAND-NY-OPEN-FIRST5-EMA12-001         │
│ Epistemic State                   │ UNVALIDATED PROPOSAL                  │
│ Source Claim Classification       │ SELF-REPORTED / UNVERIFIED            │
│ Target Instrument                 │ NQ / US100 Equity Index               │
│ Candidate Family                  │ Opening-session directional signal    │
│ Specification Status              │ INCOMPLETE (7 major gaps unresolved)  │
│ HYP_003 Status                    │ NOT CREATED                           │
│ Step R1 Pre-Registration          │ NOT STARTED                           │
│ Market Data Feed                  │ NOT ACCESSED                          │
│ Historical Backtest               │ NOT RUN                               │
│ Live Capital Authority            │ $0.00 (Hard-Locked)                   │
│ Live Trading Authority            │ LOCKED                                │
│ Broker Connection                 │ DISCONNECTED / NONE                   │
│ Next Action                       │ Await Human Review & Phase 14 Auth    │
└───────────────────────────────────┴───────────────────────────────────────┘
```
