# MEC-0016 / HYP_006: Scientific Strategy Preregistration

```text
[GOVERNANCE ARTIFACT: SCIENTIFIC STRATEGY PREREGISTRATION]
[MECHANISM_ID: MEC-0016]
[HYPOTHESIS_ID: HYP_006]
[CANONICAL_TITLE: HYP_006 — SPY Noise-Area Intraday Momentum Post-2016 Free-Data Net-Profitability Replication]
[CANONICAL_COMMIT_LINEAGE: 4061d832b9be5dd44f53bc5fc48ba20ff5490de4]
[PREREGISTRATION_STATUS = FINAL_PENDING_HYPOTHESIS_REGISTRATION]
[OPEN_METHODOLOGICAL_BLOCKERS = 0]
[HYP_006 = NOT_CREATED]
[EMPIRICAL_EXECUTION = NOT_AUTHORIZED]
[TRIAL_COUNT_K = 1]
[R1_MARKET_DATA_ACCESS = ZERO]
[M1_SAMPLE: 2016-01-01 THROUGH 2024-04-30]
[M2_SAMPLE: 2024-05-01 ONWARD (LOCKED)]
[M3_SAMPLE: PROSPECTIVE_ONLY]
[CAPITAL: $0.00 / NO_REAL_ORDERS=true]
```

- **Document ID:** `docs/research/MEC-0016-HYP-006-strategy-preregistration.md`
- **Governing Standard:** ACASH `AGENTS.md` (Strict Fail-Closed Contract, Single Canonical Authority, Literature Alignment, Zero Unverified Claims).

---

## 1. Executive Summary & Hypothesis Statement

### 1.1 Hypothesis Formal Statement
> **HYP_006:** In the post-2016 United States equity market (SPY), intraday price extensions beyond a 14-session trailing same-minute Noise Area anchored by dividend-adjusted prior close and confirmed by cumulative regular-session VWAP generate positive net economic returns after deducting realistic broker commissions, Section 31 and FINRA regulatory fees, quoted bid-ask spread crossing, and adverse execution slippage under zero-cost historical SIP data infrastructure ($K = 1$).

### 1.2 Motivation & Free-Data Lineage
HYP_005 established the complete mathematical and institutional architecture for the Zarattini, Aziz, and Barbon (2024) noise-area intraday momentum mechanism. However, HYP_005 is sealed as `BLOCKED_NON_FALSIFIED_BY_PRIMARY_DATA_ENTITLEMENT` due to pre-2016 data coverage limitations under zero-cost providers.

HYP_006 replicates the exact scientific mechanism over the post-2016 sample (`2016-01-01` through `2024-04-30`, ~8.3 years, 2,096 trading sessions) where free, consolidated SIP bars and historical quotes are authoritatively available from Alpaca Markets without requiring paid subscriptions.

---

## 2. Partition Architecture & Governance

- **M1 (Replication Sample):** `2016-01-01` through `2024-04-30`.
  - Role: `PUBLICATION_EXPOSED_POST_2016_REPLICATION_SAMPLE`.
  - Governed by frozen baseline specification $K = 1$.
- **M2 (Post-Publication Stress Sample):** `2024-05-01` onward.
  - Role: `PUBLICLY_EXPOSED_POST_PUBLICATION_STRESS_SAMPLE`.
  - Access State at R1: `STRICTLY_LOCKED_ZERO_ACCESS`.
- **M3 (Prospective Holdout):** Genuine future out-of-sample data post-ratification.
  - Role: `PROSPECTIVE_ONLY`.
- **Anti-Contamination Rule:** Neither M1 nor M2 is ever described as pristine out-of-sample data.

---

## 3. Search Space & Anti-HARKing Invariants

- **Search Space Cardinality:** Exactly $K = 1$.
- **Specification:** `MEC_0016_NOISE_AREA_INTRADAY_MOMENTUM_BASELINE`.
- **Prohibitions:**
  - Zero lookback searches ($14$ days strictly frozen).
  - Zero threshold or noise multiplier tuning ($1.0$ strictly frozen).
  - Zero long-only or short-only parameter search (trades both directions symmetric).
  - Zero alternative VWAP specifications.
  - Zero intraday stop-loss additions.
  - Zero post-hoc sample adjustments.

---

## 4. Market Data Contract & Independent VWAP

### 4.1 Primary Market Data Authority
- **Primary Bars:** Alpaca Historical SIP (`feed=sip, symbol=SPY, timeframe=1Min, adjustment=raw`).
- **Primary Quotes:** Alpaca Historical SIP (`feed=sip, symbol=SPY, endpoint=/v2/stocks/quotes`).
- **Bar Timestamp Semantics:** Left-edge indexing (`[09:30:00, 09:31:00)` for bar `09:30`).
- **Missing Bar Policy:** `FAIL_CLOSED_SESSION_EXCLUSION`. Any missing minute in a standard 390-minute session excludes the entire session. Zero forward fill, zero interpolation, zero synthetic bars. No $\le 5$ missing bars allowance.
- **Secondary Bar Cross-Check:** HF Data Library (`hfdatalibrary.com`). Role: `SECONDARY_INDEPENDENT_BAR_CROSS_CHECK_ONLY`. Zero execution, NBBO, or fill authority.

### 4.2 Independent VWAP Calculation
$$\text{TypicalPrice}_{t,m} = \frac{\text{High}_{t,m} + \text{Low}_{t,m} + \text{Close}_{t,m}}{3}$$
$$\text{VWAP}_{t,m} = \frac{\sum_{i=09:30}^m (\text{TypicalPrice}_{t,i} \times \text{Volume}_{t,i})}{\sum_{i=09:30}^m \text{Volume}_{t,i}}$$
- Calculated cumulatively over RTH, resetting at `09:30:00 ET` daily.
- Provider `vw` field is **STRICTLY REJECTED** for baseline signal generation.

---

## 5. Noise-Area & Dividend Gap Contract

### 5.1 Noise Area Calculation
- For session $t$ and regular minute $m$:
  $$\text{move\_open}[t, m] = \left| \frac{\text{Close}[t, m]}{\text{Open}[t, 09:30]} - 1 \right|$$
- Noise estimate $\sigma_{\text{open}}[t, m]$: Mean same-minute absolute move across **EXACTLY** the previous 14 completed eligible sessions:
  $$\sigma_{\text{open}}[t, m] = \frac{1}{14} \sum_{k=1}^{14} \text{move\_open}[t-k, m]$$
- **Invariants:**
  - `NOISE_AREA_LOOKBACK = 14_PRIOR_COMPLETED_SESSIONS`
  - `NOISE_AREA_WARMUP_POLICY = REQUIRE_FULL_14_PRIOR_COMPLETED_SESSIONS`
  - `CURRENT_SESSION_LEAKAGE = PROHIBITED`
  - Multiplier: Exactly `1.0`.

### 5.2 Dividend & Gap Anchors
- **Primary Authority:** State Street Global Advisors (SSGA) Official Historical Distributions (`docs/research/manifests/MEC-0015-SPY-dividend-authority-manifest.json`).
- All 33 quarterly cash distributions in the post-2016 sample cataloged and verified.
- For current session $t$:
  $$\text{prev\_close\_adjusted} = \text{previous\_regular\_close} - \text{current\_day\_cash\_dividend}$$
  $$\text{UpperAnchor} = \max(\text{current\_open}, \text{prev\_close\_adjusted})$$
  $$\text{LowerAnchor} = \min(\text{current\_open}, \text{prev\_close\_adjusted})$$
  $$\text{UpperBand}[t, m] = \text{UpperAnchor} \times (1 + \sigma_{\text{open}}[t, m])$$
  $$\text{LowerBand}[t, m] = \text{LowerAnchor} \times (1 - \sigma_{\text{open}}[t, m])$$
- If required dividend record is ambiguous or missing: Fail closed.

---

## 6. Decision Epochs & Signal Contract

### 6.1 Epoch Mapping
Discrete 30-minute evaluation epochs: `10:00, 10:30, 11:00, 11:30, 12:00, 12:30, 13:00, 13:30, 14:00, 14:30, 15:00, 15:30 ET`.
Each epoch reads the completed left-edge minute bar preceding the epoch ($HH:MM \to HH:(MM-1)$):
- `10:00` reads `09:59:00`
- `10:30` reads `10:29:00`
- ...
- `15:30` reads `15:29:00`

### 6.2 Entry & Exit Rules
At each decision epoch reading completed bar Close:
- **LONG:** $\text{Close} > \text{UpperBand}$ AND $\text{Close} > \text{VWAP}$
- **SHORT:** $\text{Close} < \text{LowerBand}$ AND $\text{Close} < \text{VWAP}$
- **FLAT:** Otherwise.
- Signal state updates exclusively at designated decision epochs.
- Continuous intraminute stops and unregistered stop variants are **STRICTLY PROHIBITED**.

---

## 7. Execution, Quote Validity & End-of-Day (EOD) Contract

### 7.1 Execution Mechanics
- **Model:** `FIRST_VALID_SIP_NBBO_AT_OR_AFTER_EXECUTION_BOUNDARY`.
- Orders evaluate at decision timestamp $T$; fills execute at first valid consolidated SIP NBBO quote at or after $T$.
  - BUY: NBBO Ask. Effective fill: $\text{Ask} + \$0.001/\text{share}$ adverse slippage.
  - SELL: NBBO Bid. Effective fill: $\text{Bid} - \$0.001/\text{share}$ adverse slippage.
- Quoted spread embedded directly via NBBO crossing. `EXPLICIT_HALF_SPREAD_DEDUCTION_WITH_NBBO = PROHIBITED`.
- Same-signal-bar Close fills are **STRICTLY PROHIBITED**.

### 7.2 Quote Validity & Condition Policy (`MEC-0016-D08`)
- Authoritative mapping bound to Alpaca Tape B (`docs/research/manifests/MEC-0016-alpaca-quote-conditions-tape-b.json`).
- Acceptable condition codes: `{'R', '?'}` where `'R'` is Regular Market Maker Open (direct SIP) and `'?'` is Historical Vendor Unspecified (legacy pre-2021 archive).
- Invariants: `bid_price > 0`, `ask_price > 0`, `bid_size > 0`, `ask_size > 0`, and `ask_price >= bid_price`.
- Crossed markets (`bid > ask`) are strictly rejected. Locked markets (`bid == ask`) are accepted for execution if liquid.
- Unacceptable conditions: `{'N', 'C', 'L', 'A', 'B', 'H', 'E', 'F', 'U', 'W', '4'}`.
- Any unknown condition code fails closed.

### 7.3 End-of-Day (EOD) Execution Contract (`MEC-0016-D09`)
- Strictly zero overnight exposure. All positions must be completely flat by regular session close (`16:00:00 ET`).
- Final signal decision epoch: `15:30:00 ET` (evaluating `15:29:00` bar). If FLAT, exits at `15:30:00 ET`.
- Forced EOD flattening boundary: `15:59:00 ET`. Any position remaining open after `15:30:00 ET` is mandatorily flattened at the first valid continuous SIP NBBO quote arriving at or after `15:59:00.000 ET` and before `16:00:00.000 ET`.
- Fills: BUY at Ask + $0.001/share; SELL at Bid - $0.001/share.
- Closing auction / MOC crosses are excluded. Bar Close fills are prohibited.
- Fail-closed: If no valid quote exists before 16:00:00 ET, session is excluded under `DataContractError`.

---

## 8. Volatility Targeting & Position Sizing Contract

- **Canonical Authority:** Canonical Author MATLAB implementation.
- **Return Definition:** 15 historical daily simple close-to-close returns of unadjusted closes (requires 16 historical closes).
- **Parameters:**
  - `DAILY_VOL_WINDOW_RETURNS_COUNT = 15`
  - `DAILY_VOL_DDOF = 1`
  - `DAILY_VOL_SHIFT = 1` (ends at $t-1$; current day strictly excluded).
  - Target daily volatility: $\sigma_{\text{target}} = 0.02$ ($2.0\%$ daily, **NO $\sqrt{252}$ annualization**).
  - Maximum leverage: $4.0\times$.
    $$\text{leverage} = \min\left(4.0, \frac{0.02}{\sigma_{\text{realized}}}\right)$$
  - Sizing denominator: Current session Open price ($\text{Open}[t, 09:30]$).
  - AUM reference: Prior-day ending AUM.
  - Shares: Nearest integer rounding (`round(..., 0)`, preserving frozen HYP_005 semantics, **not floor**).

---

## 9. Friction Stack & 2× Stress Contract

### 9.1 Baseline Friction Stack
For every executed side:
1. **Spread:** Embedded via consolidated SIP NBBO (Ask for buy, Bid for sell).
2. **Slippage:** $\$0.001/\text{share}$ adverse per side.
3. **Broker Commission:** $\max(\$0.35, \$0.0035 \times \text{shares})$ per side.
4. **SEC Section 31 Fee:** Covered sales only, 20-segment historical rate schedule, `ROUND_CEILING_TO_CENT`.
5. **FINRA TAF:** Covered sales only, 7 historical rate tiers.
6. **Short Borrow:** 0 bps baseline.

### 9.2 2× Friction Stress Specification
- Retain observed NBBO fill.
- Multiply commissions and regulatory fees by $2.0$.
- Add adverse slippage stress equal to one observed half-spread per side:
  $$\text{Adverse Slippage Stress} = \frac{\text{Ask} - \text{Bid}}{2}$$
- Short borrow stress: 50 bps annualized, pro-rated to intraday holding duration.

---

## 10. Economic Acceptance Gates

All 7 gates must pass simultaneously on the M1 replication sample:
- **G1:** $\text{Net Total Return} > 0$
- **G2:** $\text{Net Annualized Sharpe} \ge 1.00$
- **G3:** $\text{Max Drawdown} \le 30.0\%$
- **G4:** $\text{Completed Trades} \ge 100$
- **G5:** $\text{No Material Contract Failure} = \text{true}$
- **G6:** $2\times\text{ Stress Net Return} > 0$
- **G7:** $2\times\text{ Stress Net Sharpe} \ge 0.75$

---

## 11. Pre-Registration Verification Ledger

- **Implementation Status:** `FINAL_PENDING_HYPOTHESIS_REGISTRATION`
- **Methodological Blockers:** `0`
- **Hypothesis Creation:** `NOT_CREATED`
- **Market Data Access:** `ZERO`
- **Capital Authority:** `$0.00`
- **Trading Authority:** `NO_REAL_ORDERS = true`
