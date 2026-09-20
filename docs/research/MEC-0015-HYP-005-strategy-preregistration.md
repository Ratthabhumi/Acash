# MEC-0015 / HYP_005 Strategy Pre-Registration: SPY Noise-Area Intraday Momentum Net-Profitability Replication

```text
[GOVERNANCE ARTIFACT: STRATEGY PRE-REGISTRATION — RATIFIED CHOICES]
[PREREGISTRATION_STATUS: FINAL_PENDING_HYPOTHESIS_REGISTRATION]
[CANONICAL STARTING HEAD: 4ec8e0fcaee73ea8cfbaf71f5d338ef813e1e33d]
[HYP_005: NOT_CREATED]
[EMPIRICAL_EXECUTION: NOT_AUTHORIZED]
[MARKET_DATA_RETRIEVAL: ZERO OPERATIONS THIS DOCUMENT]
[OOS_ACCESS: STRICTLY FORBIDDEN (M2 STRESS & M3 PROSPECTIVE)]
[CAPITAL_AUTHORITY: $0.00 / NO_REAL_ORDERS=true]
[PAPER_TRADING: NOT AUTHORIZED]
[LIVE_TRADING: LOCKED]
```

- **Document ID:** `docs/research/MEC-0015-HYP-005-strategy-preregistration.md`
- **Hypothesis ID:** `HYP_005` (Canonical Hypothesis Ordinal 5)
- **Mechanism:** `MEC-0015` — SPY Noise-Area Intraday Momentum Net-Profitability Replication
- **Canonical Title:** `HYP_005 — SPY Noise-Area Intraday Momentum Net-Profitability Replication`
- **Research Class:** `STRATEGY_NATIVE_EXECUTABLE_ECONOMIC_HYPOTHESIS`
- **Primary Research Objective:** `NET_ECONOMIC_PERFORMANCE_AFTER_REALISTIC_FRICTION`
- **Base Canonical Commit:** `4ec8e0fcaee73ea8cfbaf71f5d338ef813e1e33d`
- **Governing Standard:** ACASH AGENTS.md (Zero Unverified Claims, Single Canonical Authority, Strict Fail-Closed)
- **Target Instrument:** SPY (US Equity ETF)
- **Primary Market Data Feed:** Alpaca Historical SIP (`symbol=SPY, feed=sip, timeframe=1Min, adjustment=raw`)

---

## 1. Upstream Contract Authority Ledger

Prior to formal inception, all upstream MEC-0015 contracts and manifests were audited, completed, and verified to have zero open blockers. The following SHA-256 digests constitute the immutable upstream authority for `HYP_005`:

| Authority Contract Document | Repository Path | Canonical SHA-256 Digest |
| :--- | :--- | :--- |
| **Research Intake Document** | `docs/research/MEC-0015-profitability-first-intraday-momentum-intake.md` | `87ad129470bbd03076ba060448ba53614e9f5cb9fdd31cd5c59d554fd7b5cf48` |
| **Strategy Contract Audit** | `docs/research/MEC-0015-strategy-contract-audit.md` | `282b421ce224f01889684efa1f19c8d2f32c26e5463ba113b1b366a0820568d0` |
| **Open Decisions Document** | `docs/research/MEC-0015-open-decisions.md` | `ca27d4a3cae9cc24d4bbe11e1839c9459f6415ae2f9d044151699e3ed5667dbb` |
| **Provider Qualification Contract** | `docs/research/MEC-0015-provider-qualification-contract.md` | `6b6168f693becf2c6258054f60feaf80ad044bfa6b80f89dc6dda531f72023da` |
| **Friction Contract** | `docs/research/MEC-0015-friction-contract.md` | `db6afb133141de32a442709c0fc754e28f9bb12155408f2bfff766489d4e0b30` |
| **Partition & Acceptance Contract** | `docs/research/MEC-0015-partition-and-acceptance-contract.md` | `1859850b61f1081674521e4b6c248a8bff18f7bd25e738a300bbbba337e8fe3f` |
| **Bar Provider Contract Manifest** | `docs/research/manifests/MEC-0015-bar-provider-contract-manifest.json` | `1a739b794a28de28199b466127d37428b7164ceca78e9d6b959a894a8b0d6c61` |
| **Dividend Provider Contract Manifest** | `docs/research/manifests/MEC-0015-dividend-provider-contract-manifest.json` | `d018e556d611bce47d08a4135681cd84c0f3a13e8559f2abc019365baa7ec027` |
| **Quote Provider Contract Manifest** | `docs/research/manifests/MEC-0015-quote-provider-contract-manifest.json` | `63876c3e0040f0e268c13bc5ad621ecd2a04af14d381f2c48e54fc0765cfb581` |
| **SEC Section 31 Fee Schedule** | `docs/research/manifests/MEC-0015-sec31-fee-schedule.json` | `d1b85853834bd92c63d435f04fd1fec3e4ca6a97128135037378c0a20d52fc0c` |
| **FINRA TAF Fee Schedule** | `docs/research/manifests/MEC-0015-finra-taf-fee-schedule.json` | `2ec11e8339e3f99b438124ea6879e6f75f6fcec7879adf46b0b31f5eb4faeaa8` |

- **Bar Provider Manifest Internal Probe Digest:** `cc399c5df3c9970ff89a308f60036c0014f9152d9b280c57feb7b7e782fc7316`.
- **FINRA TAF Schedule Authority:** 7 historical tiers covering 2004–2024, including SR-FINRA-2020-032 phased rates: 2022 ($0.000130 / cap $6.49), 2023 ($0.000145 / cap $7.27), 2024 ($0.000166 / cap $8.30).
- **SEC Section 31 Operationalization:** `SEC31_CUSTOMER_PASS_THROUGH = ACASH_CONSERVATIVE_OPERATIONALIZATION`, `SEC31_ROUNDING = ROUND_CEILING_TO_CENT` (20 official rate advisory segments).

---

## 2. Formal Hypothesis Statement

> **Under the exact preregistered MEC-0015 Noise-Area intraday momentum strategy specification, SPY over the publication-exposed M1 replication window will satisfy all preregistered net economic qualification gates after realistic ACASH transaction frictions.**

- The hypothesis is accepted on M1 **ONLY** if **ALL** primary M1 gates pass simultaneously.
- **Zero Partial-Credit Acceptance:** No weighted averaging, scorecards, or discretionary interpretation.
- **Hypothesis Class:** Strategy-native executable economic hypothesis. This is **NOT** an econometric beta-significance hypothesis.

---

## 3. Instrument, Calendar & Session Contract

- **Target Instrument:** SPY (US Equity ETF).
- **Exchange Session:** NYSE regular trading sessions only (09:30:00 to 16:00:00 America/New_York).
- **Session Duration:** Exactly 390 standard regular-session minutes.
- **Early Close Policy:** `EARLY_CLOSE_POLICY = EXCLUDE_NON_STANDARD_REGULAR_SESSIONS`. All non-standard sessions (e.g. 13:00 ET early closes on Thanksgiving eve or Christmas eve) are excluded fail-closed.
- **Overnight & Extended Hours Policy:** Strictly zero pre-market trading, zero after-hours trading, and strictly zero overnight positions held.

---

## 4. Market Data Contract & Independent VWAP

- **Data Source:** Alpaca Historical SIP (`feed=sip, symbol=SPY, timeframe=1Min, adjustment=raw`).
- **Bar Timestamp Semantics:** `LEFT_EDGE_OF_ONE_MINUTE_INTERVAL`.
  - Minute `09:30` bar covers interval `[09:30:00, 09:31:00)`.
  - Minute `15:59` bar covers interval `[15:59:00, 16:00:00)`.
- **Missing Bar Policy:** `FAIL_CLOSED_SESSION_EXCLUSION`. Any session missing any single required minute bar is completely excluded from strategy simulation. Zero forward-fill, zero linear interpolation, zero synthetic OHLC, zero silent recovery.
- **VWAP Calculation Contract:**
  - Independent OHLCV derivation:
    $$\text{TypicalPrice}_i = \frac{\text{High}_i + \text{Low}_i + \text{Close}_i}{3}$$
    $$\text{VWAP}_t = \frac{\sum_{i=1}^t (\text{TypicalPrice}_i \times \text{Volume}_i)}{\sum_{i=1}^t \text{Volume}_i}$$
  - `VWAP_NUMERATOR = HLC3`
  - `VWAP_SESSION = CUMULATIVE_RTH` (daily reset at 09:30:00 ET).
  - Provider `vw` field is **STRICTLY REJECTED** for baseline strategy signal derivation.

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
  - `CURRENT_SESSION_LEAKAGE = PROHIBITED` (same-day minute moves are never included in historical mean).
  - Author Python heuristic `min_periods=13` is **EXCLUDED** from baseline.
  - Noise multiplier: Exactly `1.0` (zero parameter search).

### 5.2 Dividend & Gap Anchors
- Historical dividend provider: Alpaca corporate actions complete snapshot.
- Disclosure: `DIVIDEND_POINT_IN_TIME_VINTAGE = NOT_GUARANTEED_BY_PROVIDER`.
- For current session $t$:
  $$\text{prev\_close\_adjusted} = \text{previous\_regular\_close} - \text{current\_day\_cash\_dividend}$$
  $$\text{UpperAnchor} = \max(\text{current\_open}, \text{prev\_close\_adjusted})$$
  $$\text{LowerAnchor} = \min(\text{current\_open}, \text{prev\_close\_adjusted})$$
  $$\text{UpperBand}[t, m] = \text{UpperAnchor} \times (1 + \sigma_{\text{open}}[t, m])$$
  $$\text{LowerBand}[t, m] = \text{LowerAnchor} \times (1 - \sigma_{\text{open}}[t, m])$$
- If required cash dividend record is ambiguous or missing: Fail closed. Never substitute zero silently.

---

## 6. Decision Epochs & Signal Contract

### 6.1 Epoch Mapping
Author conceptual decision epochs: `10:00, 10:30, 11:00, 11:30, 12:00, 12:30, 13:00, 13:30, 14:00, 14:30, 15:00, 15:30 ET`.
Because Alpaca 1-minute bars use left-edge timestamps, the completed bar preceding epoch $HH:MM$ has timestamp $HH:(MM-1)$:
- Author 10:00 decision reads Alpaca bar `09:59:00`.
- Author 10:30 decision reads Alpaca bar `10:29:00`.
- Author 11:00 decision reads Alpaca bar `10:59:00`.
- Author 11:30 decision reads Alpaca bar `11:29:00`.
- Author 12:00 decision reads Alpaca bar `11:59:00`.
- Author 12:30 decision reads Alpaca bar `12:29:00`.
- Author 13:00 decision reads Alpaca bar `12:59:00`.
- Author 13:30 decision reads Alpaca bar `13:29:00`.
- Author 14:00 decision reads Alpaca bar `13:59:00`.
- Author 14:30 decision reads Alpaca bar `14:29:00`.
- Author 15:00 decision reads Alpaca bar `14:59:00`.
- Author 15:30 decision reads Alpaca bar `15:29:00`.

### 6.2 Entry & Exit Rules
At each decision epoch reading completed bar Close:
- **LONG** if: $\text{Close} > \text{UpperBand}$ AND $\text{Close} > \text{VWAP}$
- **SHORT** if: $\text{Close} < \text{LowerBand}$ AND $\text{Close} < \text{VWAP}$
- **FLAT** otherwise.
- `ENTRY_REQUIRES_VWAP_CONFIRMATION = true`.
- Zero threshold tolerance, zero buffer, zero optimization.

### 6.3 Position Transitions & Stop Evaluation
- Signal state updates exclusively at 30-minute decision epochs.
- If existing exposure exists and new signal is FLAT: Close position.
- If existing exposure exists and new signal is opposite direction: Close position and flip direction.
- `STOP_EVALUATION_FREQUENCY = 30_MINUTE_DECISION_EPOCHS`.
- Continuous intraminute stops and unregistered stop-loss variants are **STRICTLY PROHIBITED**.

---

## 7. Execution & End-of-Day (EOD) Contract

### 7.1 Execution Mechanics
- Signal information must strictly exist prior to execution.
- Execution boundary: First valid consolidated SIP NBBO quote at or after the decision timestamp ($T$).
  - BUY (Long entry or Short cover): Fills at NBBO **Ask**.
  - SELL (Long exit or Short entry): Fills at NBBO **Bid**.
- Standalone adverse slippage:
  - BUY effective fill: $\text{Ask} + \$0.001 / \text{share}$.
  - SELL effective fill: $\text{Bid} - \$0.001 / \text{share}$.
- Quoted spread is embedded directly via NBBO crossing.
- `EXPLICIT_HALF_SPREAD_DEDUCTION_WITH_NBBO = PROHIBITED` (eliminates double-counting).
- Same-signal-bar Close fills are **STRICTLY PROHIBITED**.

### 7.2 End-of-Day Contract
- Strictly zero overnight exposure. All remaining open positions must be completely flat by regular session close (16:00:00 ET).
- Ratified MEC-0015 EOD execution semantics frozen; auction/MOC variations are excluded.
- Any EOD execution ambiguity discovered during implementation mandates immediate fail-closed stop before R2/R3 execution.

---

## 8. Volatility Sizing Contract

- **Canonical Authority:** Canonical Author MATLAB implementation.
- **Daily Return Definition:** Simple close-to-close returns on unadjusted daily prices.
- **Parameters:**
  - `DAILY_VOL_WINDOW_RETURNS_COUNT = 15` (15 historical returns requiring 16 historical closes).
  - `DAILY_VOL_DDOF = 1` (sample standard deviation).
  - `DAILY_VOL_SHIFT = 1` (strictly lagged; returns through session $t-1$).
  - `DAILY_VOL_CURRENT_DAY_INCLUDED = false`.
  - `DAILY_VOL_DIVIDEND_TREATMENT = UNADJUSTED_CLOSE_TO_CLOSE`.
  - Target daily volatility: $\sigma_{\text{target}} = 0.02$ (2.0%).
  - Leverage multiplier:
    $$\text{leverage} = \min\left(4.0, \frac{\sigma_{\text{target}}}{\sigma_{\text{realized}}}\right)$$
  - Maximum leverage cap: $4.0\times$.
  - Sizing denominator: Current session Open price ($\text{Open}[t, 09:30]$).
  - AUM reference: Prior-day ending AUM.
  - Position shares: Nearest integer rounding according to frozen reference semantics.
  - Zero alternative leverage or sizing rules permitted.

---

## 9. Friction Stack & 2× Stress Contract

### 9.1 Baseline Friction Stack
For every executed side:
1. **Spread:** Embedded via consolidated SIP NBBO (Ask for buy, Bid for sell).
2. **Slippage:** $\$0.001 / \text{share}$ adverse per side.
3. **Broker Commission:** $\max(\$0.35, \$0.0035 \times \text{shares})$ per side.
4. **SEC Section 31 Fee:** Applicable to covered **SELL** transactions only.
   - Pinned 20-segment schedule (`MEC-0015-sec31-fee-schedule.json`).
   - `SEC31_CUSTOMER_PASS_THROUGH = ACASH_CONSERVATIVE_OPERATIONALIZATION`.
   - `SEC31_ROUNDING = ROUND_CEILING_TO_CENT`.
5. **FINRA TAF:** Applicable to covered **SELL** transactions only.
   - Pinned 7-tier schedule (`MEC-0015-finra-taf-fee-schedule.json`) with statutory caps.
6. **Short Borrow Cost:** Baseline $0\text{ bps}$ (`HISTORICAL_BORROW_RATE = UNOBSERVED`; SPY extreme liquidity).

### 9.2 2× Friction Stress Contract
Frozen prior to observing any P&L:
- Quoted market remains observed NBBO Bid/Ask.
- Commissions $\times 2.0$.
- Regulatory fees (SEC Section 31 + FINRA TAF) $\times 2.0$.
- Additional adverse slippage stress equal to **one observed half-spread per executed side**:
  $$\text{Additional Slippage Stress} = \frac{\text{Ask} - \text{Bid}}{2} \times \text{shares}$$
- Short positions receive **50 bps annualized borrow stress** pro-rated by exact intraday holding minutes:
  $$\text{Borrow Stress Fee} = \text{Principal} \times 0.0050 \times \frac{\text{holding\_minutes}}{390 \times 252}$$
- Modification of this stress formula after viewing backtest results is strictly prohibited.

---

## 10. Cardinality & Anti-HARKing Search Space

- Cardinality: Exactly $K = 1$.
- Search Grid: Single cell `{"primary_specification": ["MEC_0015_NOISE_AREA_INTRADAY_MOMENTUM_BASELINE"]}`.
- Zero lookback variations, zero alternative noise multipliers, zero VWAP variants, zero alternative decision intervals, zero long-only variants, zero parameter grids, zero walk-forward optimizations, zero post-result rescues.
- Any future modification constitutes a de novo, separately authorized hypothesis.

---

## 11. Partitions & Data Governance Boundaries

| Partition | Date Range | Role / Classification | Access Status in R1 |
| :--- | :--- | :--- | :--- |
| **M1** | 2007-05-01 through 2024-04-30 | `PUBLICATION_EXPOSED_REPLICATION_SAMPLE` | R3 execution only; NOT accessed in R1 |
| **M2** | 2024-05-01 through last exposed date | `PUBLICLY_EXPOSED_POST_PUBLICATION_STRESS_SAMPLE` | R4 stress only; NOT accessed in R1 |
| **M3** | Prospective (post-preregistration) | `PROSPECTIVE_ONLY` | Sealed; requires separate human authorization |

- **Prior Exposure Disclosure:** M1 and M2 are publication-exposed samples. Passing M1 evaluates replication fidelity and economic viability under friction, NOT statistical discovery on unexposed data.
- **R1 Data Access:** `R1_MARKET_DATA_ACCESS = ZERO`.

---

## 12. Primary Acceptance & Stress Gates

### 12.1 Primary M1 Replication Acceptance Gate (Logical AND of all 7)
1. `NET_TOTAL_RETURN > 0`
2. `NET_SHARPE >= 1.00` (Annualized)
3. `MAX_DRAWDOWN <= 30%`
4. `MINIMUM_COMPLETED_TRADES >= 100` (`HUMAN_RATIFIED_SAMPLE_ADEQUACY_FLOOR`)
5. `NO_MATERIAL_CONTRACT_FAILURE`
6. `2X_FRICTION_STRESS_NET_RETURN > 0`
7. `2X_FRICTION_STRESS_NET_SHARPE >= 0.75`

$$\text{PRIMARY\_ACCEPT} = G_1 \land G_2 \land G_3 \land G_4 \land G_5 \land G_6 \land G_7$$

### 12.2 M2 Continuation Gate (Frozen, R4 Only)
1. `NET_TOTAL_RETURN > 0`
2. `NET_SHARPE >= 0.50`
3. `MAX_DRAWDOWN <= 35%`
4. `2X_FRICTION_STRESS_TOTAL_RETURN >= 0`
5. `NO_CATASTROPHIC_RISK_FAILURE`

### 12.3 Opportunity Cost Benchmark
- Benchmark: SPY Buy-and-Hold Total Return over the exact M1 horizon.
- Benchmark outperformance does **NOT** substitute for absolute net economic gates.

---

## 13. Operational Readiness & Governance Boundaries

- `CAPITAL_AUTHORITY_USD = $0.00`
- `NO_REAL_ORDERS = true`
- `PAPER_TRADING = NOT_AUTHORIZED`
- `LIVE_TRADING = LOCKED`
- `R2_DATASET_BUILD = NOT_STARTED`
- `R3_REPLICATION = LOCKED`
- `R4_M2_STRESS = LOCKED`
- `TERMINAL_HYPOTHESIS_REGISTRY` protected: `HYP_003` and `HYP_004` remain permanently closed.

---

```text
PREREGISTRATION_STATUS = FINAL_PENDING_HYPOTHESIS_REGISTRATION
HYP_005 = NOT_CREATED
EMPIRICAL_EXECUTION = NOT_AUTHORIZED
OPEN_METHODOLOGICAL_BLOCKERS = 0
```
