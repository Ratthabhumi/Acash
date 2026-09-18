# MEC-0013 Price-Only Opening Range Breakout (ORB) — Final Pre-Registration Specification

```text
[HUMAN-RATIFIED]
[PRE-REGISTRATION FROZEN]
[NO EMPIRICAL AUTHORITY]
[NO BACKTEST AUTHORITY]
[NOT HYP_003]
[MEC-0013 REMAINS ARCHIVED]
```

- **Document ID:** `docs/phase14/mec_0013_price_only_preregistration.md`
- **Base Scaffold:** `docs/phase14/mec_0013_price_only_draft_scaffold.md` (Human-Accepted 2026-09-18)
- **Governance Basis:** Human Decision Record `docs/phase14/mec_0013_ca1_orb_human_decision_surface.md` (Decisions C1, C2, C3) & Human Decision D-PREREG-1 (Option A)
- **Object:** Final, frozen, non-empirical pre-registration specification for the decoupled price-only Opening Range Breakout (ORB) research lane on SPY.
- **Purpose:** Freeze all 14 research-design parameters, mathematical rules, anti-HARKing constraints, data-quality boundaries, and empirical evaluation metrics ex-ante before any empirical calculation, dataset exposure, or backtesting.
- **Ratification Status:** RATIFIED & FROZEN (Decision D-PREREG-1 Option A, 2026-09-18 by Human Operator)
- **Date:** 2026-09-18
- **Operating Environment:** Windows 10/11 x64, Python 3.14.x (`.venv`)
- **Authority:** Strict Fail-Closed (`AGENTS.md`). Zero empirical claims, zero return calculations, zero backtests.

---

> [!IMPORTANT]
> ### HARD GOVERNANCE LOCKS (STRICTLY PRESERVED & UNCHANGED)
> - **MEC-0013:** Remains **ARCHIVED** / `NOT PROMOTED` per ratified Human Decisions `MEC-0013-D01` and `MEC-0013-D02`.
> - **HYP_003:** **NOT CREATED** (absent repository-wide).
> - **Inception Gate R1:** **NOT STARTED** / `ResearchReInceptionGate` not invoked.
> - **Empirical Validation / Backtesting:** **STRICTLY LOCKED** / **NOT AUTHORIZED**.
> - **Trading Authority:** Paper `NOT AUTHORIZED`, Live `LOCKED`, Capital `$0.00`, `NO_REAL_ORDERS=true`.
> - **Scope:** This document specifies and freezes the research protocol only. It does **NOT** grant empirical execution or model backtesting authority. Final pre-registration completion does not automatically alter these governance states.

---

## 1. Frozen Research Scope

| Dimension | Frozen Specification | Authority / Lineage Basis |
|---|---|---|
| **Instrument** | `SPY` (SPDR S&P 500 ETF Trust) | Single-instrument US cash equity proxy. Dynamic multi-stock universes and constituent rankings excluded to eliminate survivorship and selection bias. |
| **Market Data Feed** | Consolidated SIP 1-Minute Aggregates | Unadjusted raw trade-day aggregates (`feed=sip`, `timeframe=1Min`, `adjustment=raw`). |
| **Session Authority** | Accepted `NyseCa1Calendar` (CA-1) | Official NYSE Core Trading Hours `[09:30:00, 16:00:00) America/New_York` (390 expected 1-minute bars). Pre-market and after-hours excluded from breakout detection. |
| **Universe Scope** | Single instrument only (`SPY`) | Zero constituent selection, zero sector rotation. |
| **Price Basis** | Unadjusted Intraday Trade-Day Prices | Intraday price triggers and range boundaries are computed on raw trade-day tape levels ($P_{\text{raw}}$). Cash distributions and corporate actions are handled downstream in forward return accounting. |
| **Primary OR Windows** | 5 minutes (`09:30:00`–`09:35:00 ET`), 15 minutes (`09:30:00`–`09:45:00 ET`) | Ex-ante frozen geometry. |
| **Directional Lanes** | `LONG`, `SHORT` | Symmetric two-sided evaluation. |
| **Primary Research Cells** | Exactly $K = 4$ Cells:<br>1. `ORB_5M_LONG`<br>2. `ORB_5M_SHORT`<br>3. `ORB_15M_LONG`<br>4. `ORB_15M_SHORT` | Bounded ex-ante census. No additional primary cells may be added after empirical results are viewed. |

### Explicit Exclusions from Primary Signal Lane:
The following components are strictly excluded from the primary price-only signal definition:
- **Volume-Weighted Average Price (VWAP):** Decoupled from primary signal lane. D14 point-in-time consolidated volume is NOT a dependency for price-only testing.
- **Volume Filters / Thresholds:** Zero volume surge, relative volume gates, or volume confirmations in the primary signal.
- **Macro / Volatility Regime Classifiers:** Excluded from primary pre-registration grid.
- **Multi-Stock / Basket Ranking:** Excluded.
- **Fundamental Data & Corporate Filings:** Excluded.
- **News / Sentiment Feeds:** Excluded.
- **Machine Learning Models:** Zero algorithmic model weights or feature selection.
- **Post-Hoc Technical Indicators:** Moving averages, RSI, Bollinger Bands, and ATR filters are excluded from primary hypothesis census.

---

## 2. Complete Specification of the 14 Frozen Parameters

All 14 research-design degrees of freedom identified in the draft scaffold are fully and unambiguously frozen:

### 1. Breakout Confirmation
- **Frozen Rule:** `CLOSE-THROUGH`.
- **Mathematical Definition:** A breakout signal occurs if and only if a completed 1-minute bar closes strictly beyond the frozen opening-range boundary:
  - **Long Signal:** $\text{Close}_t > \text{OR}_{\text{high}}$
  - **Short Signal:** $\text{Close}_t < \text{OR}_{\text{low}}$
- **Exclusion of Intrabar Touch:** A mere intrabar touch, wick penetration, or high/low breach ($\text{High}_t > \text{OR}_{\text{high}}$ or $\text{Low}_t < \text{OR}_{\text{low}}$) without a bar close strictly through the boundary does **NOT** constitute a breakout signal.

### 2. Entry Timing & Latency
- **Frozen Rule:** `NEXT-BAR OPEN`.
- **Mathematical Definition:** Following signal bar $t$ confirming a breakout close-through, entry execution is simulated at the open of bar $t+1$:
  $$\text{Execution Time} = \text{Open}(t+1)$$
- **No Same-Bar Execution:** Execution at bar $t$ close is prohibited to eliminate lookahead and execution latency distortion.
- **End-of-Session Boundary:** If signal bar $t$ occurs on the last eligible bar of the session (15:59 ET) or no valid subsequent regular-session minute bar exists, no trade is executed.

### 3. Directional Lane
- **Frozen Rule:** `SYMMETRIC LONG + SHORT`.
- **Structure:** Both long and short directions are primary research cells and must be tracked and reported independently.
- **No Early Aggregation:** Long and short cell outcomes must not be collapsed into a pooled figure prior to reporting cell-level statistics.

### 4. Stop-Loss Rule
- **Frozen Rule:** `OPPOSITE OPENING-RANGE BOUNDARY`.
- **Mathematical Definition:** Fixed price stop level established at entry:
  - **Long Position Stop:** $\text{Stop}_{\text{long}} = \text{OR}_{\text{low}}$
  - **Short Position Stop:** $\text{Stop}_{\text{short}} = \text{OR}_{\text{high}}$
- **Invariance Constraints:** The stop level remains strictly fixed throughout the trade lifecycle.
  - Zero trailing stops.
  - Zero midpoint stops.
  - Zero ATR-based adjustments.
  - Zero post-hoc optimization.

### 5. Exit / Holding Horizon
- **Frozen Rule:** `END-OF-DAY FLATTEN`.
- **Definition:** If the protective stop is not triggered during the session, the position is held until the final eligible regular-session minute and exited according to the execution price convention.
- **Profit Target Restriction:** Zero fixed profit targets. Zero $R$-multiple profit targets.

### 6. Transaction Cost Model
- **Frozen Rule:** Fixed institutional research assumption of **1.6 bps round-trip** (basis points of traded notional).
- **Component Breakdown:**
  - **Entry Cost:** $0.8\text{ bps}$ ($0.00008 \times \text{Price}_{\text{entry}}$)
  - **Exit Cost:** $0.8\text{ bps}$ ($0.00008 \times \text{Price}_{\text{exit}}$)
- **Nature:** Deterministic research friction model, not an empirical claim regarding specific broker commission schedules. Gross and net returns must be reported separately.

### 7. Slippage Model
- **Frozen Rule:** Adverse slippage of **0.5 bps per side** ($0.00005 \times \text{Price}$).
- **Application:**
  - **Long Trade:**
    $$\text{Fill}_{\text{entry}} = \text{Price}_{\text{observable}} \times (1 + 0.00005)$$
    $$\text{Fill}_{\text{exit}} = \text{Price}_{\text{observable}} \times (1 - 0.00005)$$
  - **Short Trade:**
    $$\text{Fill}_{\text{entry}} = \text{Price}_{\text{observable}} \times (1 - 0.00005)$$
    $$\text{Fill}_{\text{exit}} = \text{Price}_{\text{observable}} \times (1 + 0.00005)$$
- **Independence:** Applied separately from and in addition to transaction costs.

### 8. Execution Price Convention
- **Entry Fill:** Simulated at `Open(t+1)`.
- **Stop-Loss Fill:** If the stop boundary is crossed or gapped through, fill price is determined conservatively as the worse of the stop boundary price versus the first observable executable bar price in the adverse direction:
  - **Long Stop Fill:** $\min(\text{Stop}_{\text{long}}, \text{Open}_t, \text{Low}_t)$ (conservative adverse fill)
  - **Short Stop Fill:** $\max(\text{Stop}_{\text{short}}, \text{Open}_t, \text{High}_t)$ (conservative adverse fill)
  - No simulated fill may be executed at a price more favorable than the observable market extremes of that bar.
- **EOD Exit Fill:** Executed using the `Close` price of the final eligible regular-session 1-minute bar (`15:59 ET`).

### 9. Opening Auction Handling
- **Frozen Rule:** The official `09:30 ET` minute bar is **INCLUDED** in opening-range construction.
- **Rationale & Lineage:** Under accepted CA-1 authority, the core trading session regular minute grid commences at `09:30:00 ET`. The `09:30` bar aggregate provided by the SIP feed contains both the opening auction cross print and continuous trades in that first minute.
- **Microstructure Boundary:** No attempt is made to decompose or separate the opening cross print from the continuous tape in the primary lane. Documented as a known market-microstructure limitation.

### 10. Closing Auction Handling
- **Frozen Rule:** All bars timestamped `16:00 ET` or later are **EXCLUDED**.
- **Session Boundary:** Primary trading session is strictly $[09:30:00, 16:00:00)\text{ America/New_York}$.
- **Final Eligible Minute:** `15:59 ET` (representing interval `[15:59:00, 16:00:00)`).
- **Exit Price Reference:** EOD flatten uses `Close` of the `15:59` bar.
- **Exclusion of Closing Cross:** The `16:00` closing auction print is explicitly excluded from simulated fills to avoid auction imbalance modeling assumptions.

### 11. In-Sample (IS) / Out-of-Sample (OOS) Partition
- **Frozen Date Boundaries:**
  - **In-Sample (IS) Partition:** `2017-01-01` through `2022-12-31` (6 calendar years).
  - **Out-of-Sample (OOS) Partition:** `2023-01-01` through `2026-12-31` (4 calendar years).
- **Session Alignment:** Evaluated strictly across regular CA-1 sessions falling within these calendar intervals.
- **Secrecy & Holdout Protocol:** The OOS partition must remain unseen, uninspected, and held out during any future parameter analysis. No parameter, threshold, or model rule may be adjusted or tuned based on OOS observations.

### 12. Embargo / Purge Rules
- **Frozen Rule:** **0 trading days** embargo / purge between partitions.
- **Rationale:** Each ORB trade is strictly an intraday observation initiated after `09:35`/`09:45` and flattened at or before `15:59` on the same session. There is zero multi-day overnight inventory, zero multi-session holding horizon, and zero overlapping forward-return labeling across session boundaries.
- **Conditional Boundary:** If future model variants introduce multi-day holding or overlapping temporal labels, an embargo window must be formally pre-registered prior to execution.

### 13. Data-Quality & Completeness Threshold
- **Frozen Rule:** **100% complete CA-1 expected minute grid** for every included regular trading session.
- **Regular Session Standard:** Exactly **390 expected 1-minute bars** (`09:30` through `15:59` inclusive).
- **Fail-Closed Exclusion:** Any session exhibiting missing minute bars ($< 390$), duplicate timestamps, non-monotonic ordering, or invalid OHLC geometry ($\text{Low} > \text{High}$, negative volume, etc.) must be **completely excluded** from the analysis dataset.
- **Exclusion Accounting:** Every dropped session must be logged with an explicit cryptographic failure reason.
- **Zero Fabrication:** Zero interpolation, zero forward-filling, zero synthetic bar generation.

### 14. Session Exclusion Policy
- **Frozen Rule:** Primary analysis admits **REGULAR 390-MINUTE CA-1 SESSIONS ONLY**.
- **Mandatory Exclusions:**
  1. **Early-Close Sessions:** All 13:00 ET early-close sessions (210 minute bars, e.g., Day before Independence Day, Black Friday, Christmas Eve) are excluded from the primary sample.
  2. **Official Holidays & Special Closures:** All full-day closures (e.g., National Days of Mourning, severe weather) are excluded.
  3. **Incomplete Sessions:** Sessions failing the 390/390 data-quality threshold.
  4. **Out-of-Coverage Dates:** Any date outside accepted CA-1 authority coverage (`2013-01-01` to `2026-12-31`).
- **Robustness Scope:** Early-close sessions may only be examined in a separately pre-registered secondary robustness inquiry, never mixed into primary census cells.

---

## 3. Trade Count, Signal Rules & Position Sizing

1. **Maximum One Trade Per Cell Per Session:** Each primary research cell (`ORB_5M_LONG`, `ORB_5M_SHORT`, `ORB_15M_LONG`, `ORB_15M_SHORT`) is eligible for at most one trade per trading day.
2. **First-Confirmed-Breakout Only:** A signal is generated only on the first bar that closes through the boundary after the opening range concludes. Once a trade is triggered and subsequent exit occurs (via stop or EOD), that cell is closed for the remainder of the session (no re-entry).
3. **Independent Directional Processing:** If a session experiences an upward breakout followed later by a downward breakout (or vice-versa), the long cell and short cell process their signals independently based on their respective first-break events.
4. **No Pyramiding / No Averaging Down:** Additional positions are strictly prohibited while a position is open.
5. **No Leverage or Sizing Optimization:** Position returns are evaluated on a unit-notional / unleveraged percentage-return basis:
   $$R_{\text{gross, long}} = \frac{P_{\text{exit}} - P_{\text{entry}}}{P_{\text{entry}}}$$
   $$R_{\text{gross, short}} = \frac{P_{\text{entry}} - P_{\text{exit}}}{P_{\text{entry}}}$$
   Net returns deduct the frozen 1.6 bps round-trip transaction costs and 1.0 bps round-trip adverse slippage.
6. **No Portfolio Capital Allocation:** Portfolio allocation models, volatility parity, or dynamic Kelly scaling are excluded at this pre-registration stage.

---

## 4. Anti-HARKing & Multiple Testing Invariants

To strictly prohibit Hypothesizing After the Results are Known (HARKing) and maintain statistical validity:

1. **Fixed Hypothesis Census ($K = 4$):** The primary hypothesis census is frozen at exactly 4 cells:
   $$\text{Census} = \{\text{ORB\_5M\_LONG}, \text{ORB\_5M\_SHORT}, \text{ORB\_15M\_LONG}, \text{ORB\_15M\_SHORT}\}$$
2. **Zero Post-Hoc Cell Pruning:** No cell may be discarded, hidden, or retroactively designated as "exploratory" because of uninspiring or negative results. All 4 cells must be reported in full.
3. **No Window Fishing:** No alternative opening-range durations (e.g., 10m, 30m, 60m) may be substituted into the primary census post-hoc.
4. **Frozen Risk & Execution Model:** No stop-loss rule, holding horizon, cost parameter, or slippage allowance may be calibrated or altered using OOS performance.
5. **No VWAP Re-Introduction:** Volume or VWAP filters must not be opportunistically injected into the primary price-only lane following empirical inspection.
6. **Separation of Exploratory Variants:** Any future research variants (e.g., ATR stops, volume conditioning) must be registered in a separate secondary document and cannot supersede primary pre-registered outcomes.
7. **OOS Holdout Integrity:** OOS outcomes must not influence model selection or specification adjustments.

---

## 5. Primary Empirical Outputs — Specification Only

When empirical execution is formally authorized in a future governance step, the backtesting engine must output the following standardized metrics per primary cell without omission. **Zero calculations or numerical values are provided in this document.**

### Required Reporting Table per Cell:
- **Session Accounting:**
  - Total CA-1 sessions in window
  - Eligible regular sessions ($N_{\text{eligible}}$)
  - Excluded sessions broken down by category (early close, incomplete $< 390$, invalid data)
- **Trade Activity:**
  - Breakout signal count ($N_{\text{signal}}$)
  - Executed trade count ($N_{\text{trade}}$)
  - Trade execution rate ($N_{\text{trade}} / N_{\text{eligible}}$)
  - Stop-loss exit count ($N_{\text{stop}}$)
  - EOD flatten exit count ($N_{\text{EOD}}$)
- **Return Distributions (Reported Separately for Gross and Net):**
  - Cumulative compounded return
  - Mean trade return ($\mu$)
  - Standard deviation of trade returns ($\sigma$)
  - Median trade return
  - Interquartile range (IQR)
  - Minimum trade return (maximum single-trade loss)
  - Maximum trade return
  - Win rate ($\% \text{ trades with } R > 0$)
  - Profit factor ($\sum \text{Gains} / \sum |\text{Losses}|$)
- **Risk & Efficiency:**
  - Maximum drawdown (MDD in %)
  - Annualized Sharpe-like ratio (computed per canonical ACASH sample standards)
  - Average holding time in minutes
  - Aggregate turnover
- **Partition Disaggregation:**
  - In-Sample (IS: 2017–2022) results reported separately.
  - Out-of-Sample (OOS: 2023–2026) results reported separately.
  - Performance degradation ratio ($\text{Sharpe}_{\text{OOS}} / \text{Sharpe}_{\text{IS}}$).

---

## 6. Success / Failure Criteria

In accordance with strict empirical integrity, this pre-registration does not fabricate an arbitrary profitability hurdle where none has been ratified. Criteria are defined as follows:

### 6.1 Technical Contract Pass Criteria:
1. Complete deterministic reproducibility of execution across identical data slices.
2. Zero lookahead violation (all signals use strictly completed bars; entry at next-bar open; stops filled at or worse than observable bounds).
3. 100% enforcement of the CA-1 390-bar session completeness threshold.
4. Strict compliance with frozen parameter rules with zero parameter modification.
5. Absolute preservation of the IS/OOS temporal partition boundary.

### 6.2 Scientific Research Outcome:
- The empirical outcome of the frozen $K=4$ census may be **positive**, **negative**, or **null**.
- **A null or negative result is a valid scientific finding.** Under ACASH research governance, a negative empirical outcome disconfirms the naive price-only opening range breakout hypothesis on SPY and provides definitive evidence to retire the candidate.
- Negative outcomes must never trigger post-hoc parameter adjustments on the same data sample.

---

## 7. Known Limitations & Research Boundaries

1. **D13 PIT/Vintage Authority Open:** Probes confirm historical availability and multi-year depth, but point-in-time release vintage and provider restatement semantics remain open.
2. **Aggregated Bar Feed:** Data consists of provider 1-minute aggregates rather than ticks reconstructed directly from consolidated raw exchange feeds.
3. **Embedded Opening Cross Microstructure:** The `09:30 ET` minute bar contains the opening auction execution alongside early continuous trading.
4. **Early-Close Exclusion:** Excluding 13:00 ET sessions eliminates half-day trading behavior from the primary sample.
5. **Single Instrument Scope:** Testing exclusively on `SPY` limits inferences regarding whether findings generalize to broad single-stock equities or alternative ETFs.
6. **Decoupled VWAP:** Volume profile is omitted from this lane; interaction between price breakouts and institutional volume benchmarks is deferred to future work.

---

## 8. Preserved Governance State

This pre-registration specification operates strictly within the non-authorizing governance envelope:

| Boundary Dimension | Pre-Registration State | Authority / Governance Source |
|---|---|---|
| **MEC-0013 Status** | `ARCHIVED` / `NOT PROMOTED` | Human Decisions `MEC-0013-D01` and `MEC-0013-D02` |
| **Hypothesis Registry** | `HYP_003` **NOT CREATED** | Absent repository-wide |
| **Inception Gate** | `ResearchReInceptionGate` (R1) **NOT STARTED** | Requires formal separate ratification |
| **Empirical Validation** | **STRICTLY LOCKED** | No backtests authorized or executed |
| **Paper Execution** | **NOT AUTHORIZED** | Requires Gate 4 / Paper clearance |
| **Live Execution** | **STRICTLY LOCKED** | Capital `$0.00`, `NO_REAL_ORDERS=true` |
| **Data Plane Access** | Local read-only cached data / Zero live probes | `src/acash/data/qualification/` |

---

## 9. Human Governance Decision Record — D-PREREG-1

```text
================================================================================
HUMAN DECISION RECORD: D-PREREG-1 — PRICE-ONLY ORB PRE-REGISTRATION FREEZE
================================================================================
RATIFIED SELECTION: OPTION A — RATIFY AND FREEZE PRE-REGISTRATION SPECIFICATION
Date:               2026-09-18
Ratifying Authority: Human Operator
Status:             RATIFIED & FROZEN
================================================================================
```

### Exact Ratified Scope & Meaning:
1. **Full Pre-Registration Acceptance:**
   - The Human Operator formally accepts `docs/phase14/mec_0013_price_only_preregistration.md` exactly as written.
2. **Frozen Research-Design Dimensions:**
   - **All 14 Research-Design Parameters:** Breakout confirmation (`CLOSE-THROUGH`), entry timing (`NEXT-BAR OPEN`), directional lane (`SYMMETRIC LONG + SHORT`), stop loss (`OPPOSITE OPENING-RANGE BOUNDARY`), exit horizon (`END-OF-DAY FLATTEN` at 15:59 ET close), transaction cost (`1.6 bps ROUND-TRIP`), slippage (`0.5 bps ADVERSE PER SIDE`), execution price convention (conservative executable prices), opening auction (`INCLUDE 09:30 ET BAR`), closing auction (`EXCLUDE 16:00 ET+ BARS`), IS/OOS partitions (`2017–2022 IS / 2023–2026 OOS`), embargo/purge (`0 TRADING DAYS`), data quality (`100% COMPLETE CA-1 390-MINUTE GRID`), and session exclusions (`REGULAR 390-MIN SESSIONS ONLY`).
   - **Hypothesis Census Grid:** Strictly frozen at $K = 4$ primary cells (`ORB_5M_LONG`, `ORB_5M_SHORT`, `ORB_15M_LONG`, `ORB_15M_SHORT`).
   - **Anti-HARKing Invariants:** Zero selective cell deletion; zero post-hoc tuning; OOS held out and unseen during parameter review.
3. **Hard Governance Boundaries (Preserved & Unchanged):**
   - Does **NOT** authorize empirical validation.
   - Does **NOT** authorize backtesting.
   - Does **NOT** create `HYP_003`.
   - Does **NOT** invoke `ResearchReInceptionGate` (R1).
   - Does **NOT** revive or promote `MEC-0013` (remains `ARCHIVED`).
   - Does **NOT** authorize Paper or Live execution.
   - Empirical validation authorization remains a separate, subsequent human governance gate.

---

### Verification Ledger
- Implementation Status: COMPLETE (Pre-Registration Specification Ratified & Frozen by Human Operator)
- Contract Enforcement: STRICT FAIL-CLOSED (14 parameters frozen ex-ante; zero empirical data exposure)
- Mathematical Authority: CANONICAL RATIFIED PRE-REGISTRATION SPECIFICATION (Zero empirical calculation)
- Local Test Suite: NOT REQUIRED (Pure governance documentation update)
- Type Checker (MyPy): NOT APPLICABLE
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: Design frozen ex-ante; empirical backtesting remains strictly locked pending separate Human authorization.
