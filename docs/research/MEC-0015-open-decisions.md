# MEC-0015: Architectural, Econometric & Operational Decisions Ledger

This document tracks the status of all architectural, mathematical, and execution decisions for **MEC-0015**. All decisions have been formally analyzed, tested, and resolved prior to registering `HYP_005`.

---

## Master Decision Summary

| Decision ID | Description | Current Status | Governing Authority / Classification |
| :--- | :--- | :--- | :--- |
| `DEC-MEC015-01` | Exact Execution Bar & Price Semantics | `RESOLVED` | `PRIMARY_EXECUTION_MODEL = FIRST_VALID_SIP_NBBO_AT_OR_AFTER_EXECUTION_BOUNDARY`; BUY at Ask, SELL at Bid |
| `DEC-MEC015-02` | Exact Session VWAP Definition | `RESOLVED` | Typical Price $(H+L+C)/3$, cumulative RTH, daily reset |
| `DEC-MEC015-03` | Transaction Cost & Fee Schedule | `RESOLVED` | Commission $\max(\$0.35, \$0.0035 \times \text{sh})$; SEC Section 31 & FINRA TAF historical schedules frozen |
| `DEC-MEC015-04` | Bid-Ask Spread & Slippage Model | `RESOLVED` | `ACASH_SPREAD_MODEL = EMBEDDED_IN_NBBO_FILL`; standalone slippage $\$0.001$/sh; double deduction prohibited |
| `DEC-MEC015-05` | Daily Volatility Targeting Definition | `RESOLVED` | Canonical MATLAB: 15 daily simple returns, `ddof=1`, shift 1 ($t-1$), current day excluded |
| `DEC-MEC015-06` | Corporate Actions & Dividend Adjustment| `RESOLVED` | Alpaca complete cash dividends qualified; gap anchor adjusted ($\text{prev\_close} - \text{div}$); fail-closed |
| `DEC-MEC015-07` | Early-Close Days Policy | `RESOLVED` | `EARLY_CLOSE_POLICY = EXCLUDE_NON_STANDARD_REGULAR_SESSIONS`; 210-min sessions excluded |
| `DEC-MEC015-08` | Market Data Provider & Feed Qualification| `RESOLVED` | Alpaca SIP 1-min bars qualified (manifest sealed); SIP quotes qualified (manifest sealed) |
| `DEC-MEC015-09` | Missing Bar & Zero-Volume Handling | `RESOLVED` | `MISSING_REQUIRED_MINUTE_POLICY = FAIL_CLOSED_SESSION_EXCLUSION`; zero silent imputation |
| `DEC-MEC015-10` | Warmup Window & Historical Burn-In | `RESOLVED` | `NOISE_AREA_WARMUP_POLICY = REQUIRE_FULL_14_PRIOR_COMPLETED_SESSIONS`; 13-period variant excluded |
| `DEC-MEC015-11` | Market-Close Execution Rule (EOD Flat) | `RESOLVED` | Forced flat at 16:00 ET; zero overnight inventory |
| `DEC-MEC015-12` | Short-Sale Mechanics & Margin Rules | `RESOLVED` | SPY ETB locate assumed; baseline 0 bps; mandatory 50 bps annualized stress |
| `DEC-MEC015-13` | Benchmark Definition | `RESOLVED` | Primary benchmark = SPY buy-and-hold total return |
| `DEC-MEC015-14` | Historical Sample Partitioning | `RESOLVED` | M1: 2007-05 to 2024-04 (replication); M2: 2024-05 to exposed date (stress); M3: prospective holdout |
| `DEC-MEC015-15` | Economic Acceptance & Invalidation Gates| `RESOLVED` | M1 gates (Sharpe $\ge 1.00$, MDD $\le 30\%$, trades $\ge 100$, 2× stress); M2 gates (Sharpe $\ge 0.50$, MDD $\le 35\%$) |

---

## Detailed Decision Records

### 1. Exact Execution Bar & Price Semantics
- **Decision ID:** `DEC-MEC015-01`
- **Current Status:** `RESOLVED`
- **Governing Specification:**
  - `SIGNAL_PRICE_FIELD = RESOLVED_AUTHOR_REFERENCE_IMPLEMENTATION` (Evaluated on 1-minute `Close`).
  - `ENTRY_REQUIRES_VWAP_CONFIRMATION = RESOLVED_TRUE` (Long: Close > Band AND Close > VWAP; Short: Close < Band AND Close < VWAP).
  - `DECISION_FREQUENCY = 30_MINUTES` (`min_from_open % 30 == 0`, `America/New_York` / ET).
  - `REFERENCE_BACKTEST_EXPOSURE_LAG = RESOLVED_1_MINUTE` (Exposure lagged by 1 minute: `position = signal.shift(1)`, P&L begins at $t+1$).
  - `STOP_EVALUATION_FREQUENCY = RESOLVED_30_MINUTE_DECISION_EPOCHS`.
  - `FLAT_SIGNAL_AT_REBALANCE_CLOSES_POSITION = RESOLVED_AUTHOR_IMPLEMENTATION`.
  - `OPPOSITE_SIGNAL_FLIPS_POSITION = RESOLVED_AUTHOR_IMPLEMENTATION`.
  - `PRIMARY_EXECUTION_MODEL = FIRST_VALID_SIP_NBBO_AT_OR_AFTER_EXECUTION_BOUNDARY`:
    - For a BUY: `fill_price = ask`
    - For a SELL: `fill_price = bid`
    - Preserves conservative latency ordering: signal depends on completed bar ending at $T$; execution fill uses the first valid quote arriving at or after $T$.

---

### 2. Exact Session VWAP Definition & Numerator Convention
- **Decision ID:** `DEC-MEC015-02`
- **Current Status:** `RESOLVED`
- **Governing Specification:**
  - `VWAP_NUMERATOR = RESOLVED_TYPICAL_PRICE_HLC3`: $\text{TypicalPrice}_i = (\text{High}_i + \text{Low}_i + \text{Close}_i)/3$.
  - `VWAP_SESSION = RESOLVED_REGULAR_SESSION_CUMULATIVE`: $\text{VWAP}_t = \frac{\sum_{i=1}^t \text{TypicalPrice}_i \cdot \text{Volume}_i}{\sum_{i=1}^t \text{Volume}_i}$.
  - Resets to zero at the beginning of each regular trading day.
  - Close-only, provider-native, and tick SIP VWAP are explicitly prohibited for baseline replication.

---

### 3. Realistic Transaction Cost & Fee Model
- **Decision ID:** `DEC-MEC015-03`
- **Current Status:** `RESOLVED`
- **Governing Specification:**
  - Literature baseline commission: $\max(\$0.35, \$0.0035 \times \text{shares})$ per order execution side.
  - Regulatory fees: Governed by exact historical effective-date schedules.
    - SEC Section 31 Fee: `docs/research/manifests/MEC-0015-sec31-fee-schedule.json` (covers 2007-05-01 through 2024-04-30 across 25 distinct regulatory rate intervals; sales only).
    - FINRA TAF: `docs/research/manifests/MEC-0015-finra-taf-fee-schedule.json` (covers 2007-05-01 through 2024-04-30 across 5 distinct fee tiers with per-trade caps; sales only).
  - Pure deterministic Decimal calculation implemented in `src/acash/execution/regulatory_fees.py` (`compute_sec31_fee`, `compute_finra_taf`). Fail-closed outside schedule boundaries.

---

### 4. Bid-Ask Spread Crossing & Slippage Model
- **Decision ID:** `DEC-MEC015-04`
- **Current Status:** `RESOLVED`
- **Governing Specification:**
  - `ACASH_SPREAD_MODEL = EMBEDDED_IN_NBBO_FILL`:
    - BUY executed at NBBO Ask; SELL executed at NBBO Bid.
    - `EXPLICIT_HALF_SPREAD_DEDUCTION_WITH_NBBO = PROHIBITED` (Zero additional half-spread deduction to prevent double-counting).
  - `BASELINE_STANDALONE_SLIPPAGE = $0.001/share` per executed side:
    - BUY: $\text{Ask} + \$0.001$
    - SELL: $\text{Bid} - \$0.001$
  - 2× Friction Stress Specification:
    - Retain observed NBBO bid/ask fill.
    - Multiply all non-spread explicit transaction costs (commissions, regulatory fees) by 2.0.
    - Apply an additional adverse slippage stress component equal to one observed half-spread per side:
      $$\text{Adverse Slippage Stress} = \frac{\text{Ask} - \text{Bid}}{2}$$

---

### 5. Daily Volatility Targeting & Return Definition
- **Decision ID:** `DEC-MEC015-05`
- **Current Status:** `RESOLVED`
- **Governing Specification:**
  - Canonical author code authority: MATLAB reference implementation (`backtesting-riding-intraday-trends-in-us-markets-using-matlab`).
  - `DAILY_VOL_RETURN_TYPE = SIMPLE_CLOSE_TO_CLOSE`: $\text{daily\_ret}_t = \text{Close}_t / \text{Close}_{t-1} - 1$.
  - `DAILY_VOL_WINDOW_RETURNS_COUNT = 15`: Exactly 15 daily simple returns ending at $t-1$ (`spy_return(d-15:d-1)` in 1-indexed MATLAB).
  - `DAILY_VOL_DDOF = 1`: Sample standard deviation ($N-1$).
  - `DAILY_VOL_SHIFT = 1`: Lagged to yesterday ($t-1$).
  - `DAILY_VOL_CURRENT_DAY_INCLUDED = false`: Current day return strictly excluded from sizing volatility.
  - `DAILY_VOL_DIVIDEND_TREATMENT = UNADJUSTED_CLOSE_TO_CLOSE`: Unadjusted daily closes per author reference.
  - `AUTHOR_IMPLEMENTATION_DIVERGENCE`: MATLAB canonical implementation (15 returns) takes precedence over the Python educational tutorial which suffered a half-open slice off-by-one bug (`iloc[d-15:d-1]` yielding 14 returns ending at $d-2$).

---

### 6. Corporate Actions, Dividends & Split Treatment
- **Decision ID:** `DEC-MEC015-06`
- **Current Status:** `RESOLVED`
- **Governing Specification:**
  - `BAND_PREVIOUS_CLOSE_DIVIDEND_TREATMENT = RESOLVED_AUTHOR_IMPLEMENTATION`:
    $$\text{prev\_close\_adjusted} = \text{Close}[t-1, 16:00] - \text{dividend}[t]$$
  - Overnight gap anchors: $\text{UpperAnchor} = \max(\text{Open}, \text{prev\_close\_adjusted})$, $\text{LowerAnchor} = \min(\text{Open}, \text{prev\_close\_adjusted})$.
  - Intraday bars remain unadjusted to preserve real execution boundaries.
  - Data Provider Mapping: Alpaca corporate-actions endpoint (`/v1/corporate-actions`) qualified for SPY cash dividends (`types=cash_dividend`, `data_quality=complete`).
  - Classifications:
    - `DIVIDEND_PROVIDER_MAPPING = QUALIFIED_HISTORICAL_COMPLETE_SNAPSHOT`
    - `DIVIDEND_POINT_IN_TIME_VINTAGE = NOT_GUARANTEED_BY_PROVIDER`
  - Fail-closed contract: If an ex-date dividend required by strategy is absent or ambiguous, raise `DATA_CONTRACT_EXCLUSION`. Never assume dividend = 0 under corporate action uncertainty.

---

### 7. Early-Close Days Policy
- **Decision ID:** `DEC-MEC015-07`
- **Current Status:** `RESOLVED`
- **Governing Specification:**
  - `EARLY_CLOSE_POLICY = EXCLUDE_NON_STANDARD_REGULAR_SESSIONS`.
  - Non-standard sessions closing early at 13:00 ET (e.g. Day after Thanksgiving, Christmas Eve, 210-minute sessions) are strictly excluded from the `HYP_005` baseline sample.
  - Support for early-close detection remains in infrastructure code, but does not grant entry to the baseline evaluation set.

---

### 8. Market Data Provider & Feed Qualification
- **Decision ID:** `DEC-MEC015-08`
- **Current Status:** `RESOLVED`
- **Governing Specification:**
  - Alpaca SIP 1-minute OHLCV bars: Qualified across 6 authorized historical probe sessions (2,340/2,340 bars, 0 missing). Manifest sealed: `docs/research/manifests/MEC-0015-bar-provider-contract-manifest.json` (SHA: `cc399c5df3c9970ff89a308f60036c0014f9152d9b280c57feb7b7e782fc7316`).
  - Alpaca SIP quotes (`/v2/stocks/quotes`): Qualified across 3 authorized probe sessions at 3 execution boundaries (9/9 probe windows valid, latency median 1.67 ms). Manifest sealed: `docs/research/manifests/MEC-0015-quote-provider-contract-manifest.json` (SHA: `593b8aa6f51be0e588ea7bdf4164b3ef658c1482f3efc29aa4f0612c6a46132a`).
  - Audit Trail Classification:
    - `NETWORK_RETRIEVAL_ATTEMPTS = 2`
    - `UNIQUE_MARKET_DATES_ACCESSED = 6`
    - `UNAUTHORIZED_DATES_ACCESSED = 0`
    - `MAX_ACCESSED_DATE = 2024-03-01`
    - `EMPIRICAL_SCOPE_IMPACT = NONE`

---

### 9. Missing Bar & Zero-Volume Handling
- **Decision ID:** `DEC-MEC015-09`
- **Current Status:** `RESOLVED`
- **Governing Specification:**
  - `MISSING_REQUIRED_MINUTE_POLICY = FAIL_CLOSED_SESSION_EXCLUSION`.
  - Zero silent forward-fill or price imputation. If any of the required 390 regular trading minutes are missing from an RTH session, the session is excluded under `DataContractError`.

---

### 10. Warmup Window & Historical Burn-In
- **Decision ID:** `DEC-MEC015-10`
- **Current Status:** `RESOLVED`
- **Governing Specification:**
  - `NOISE_AREA_WARMUP_POLICY = REQUIRE_FULL_14_PRIOR_COMPLETED_SESSIONS`.
  - Baseline ACASH calculation must NOT emit a Noise Area value until all 14 prior completed sessions exist.
  - Author Python `min_periods=13` behavior documented as `AUTHOR_CODE_WARMUP_VARIANT = MIN_PERIODS_13` and explicitly excluded from baseline `HYP_005`.
  - Nominal literature rule = 14; eliminates arbitrary library warmup behavior.

---

### 11. Market-Close Execution Rule (EOD Flat)
- **Decision ID:** `DEC-MEC015-11`
- **Current Status:** `RESOLVED`
- **Governing Specification:**
  - Exit signal evaluated at 15:30 ET decision epoch.
  - Continuous order executed on final RTH minute (15:59 ET bar); forced flat at 16:00 ET. Strictly zero overnight inventory.

---

### 12. Short-Sale Mechanics & Margin Rules
- **Decision ID:** `DEC-MEC015-12`
- **Current Status:** `RESOLVED`
- **Governing Specification:**
  - `SHORT_LOCATE_ASSUMPTION = SPY_AVAILABLE_UNLESS_PROVIDER_OR_BROKER_MARKS_UNAVAILABLE`.
  - `HISTORICAL_BORROW_RATE = UNOBSERVED`.
  - Baseline borrow cost: 0 bps (justified by SPY extreme liquidity and intraday duration).
  - Mandatory Stress Test: 50 bps annualized borrow fee pro-rated to intraday holding duration, included in the mandatory 2× friction stress test for short positions.
  - Long-only substitution is strictly prohibited.

---

### 13. Benchmark Definition & Evaluation Horizon
- **Decision ID:** `DEC-MEC015-13`
- **Current Status:** `RESOLVED`
- **Governing Specification:**
  - Primary benchmark is SPY buy-and-hold total return over the identical evaluation horizon.

---

### 14. Historical Sample Partitioning & Contamination Governance
- **Decision ID:** `DEC-MEC015-14`
- **Current Status:** `RESOLVED`
- **Governing Specification:**
  - M1: 2007-05-01 through 2024-04-30 (`PUBLICATION_EXPOSED_REPLICATION_SAMPLE`).
  - M2: 2024-05-01 through last publicly exposed date (`PUBLICLY_EXPOSED_POST_PUBLICATION_STRESS_SAMPLE`).
  - M3: `PROSPECTIVE_ONLY` (genuine out-of-sample holdout post-preregistration).
  - Neither M1 nor M2 will ever be described as pristine out-of-sample data.

---

### 15. Future Economic Acceptance & Invalidation Thresholds
- **Decision ID:** `DEC-MEC015-15`
- **Current Status:** `RESOLVED`
- **Governing Specification:**
  - M1 Replication Gates (Pre-Declared):
    - `NET_TOTAL_RETURN > 0`
    - `NET_SHARPE >= 1.00` (annualized)
    - `MAX_DRAWDOWN <= 30%`
    - `2X_FRICTION_STRESS_NET_RETURN > 0`
    - `2X_FRICTION_STRESS_NET_SHARPE >= 0.75`
    - `MINIMUM_COMPLETED_TRADES = 100` (`HUMAN_RATIFIED_SAMPLE_ADEQUACY_FLOOR`)
  - M2 Continuation Gates (Pre-Declared):
    - `NET_TOTAL_RETURN > 0`
    - `NET_SHARPE >= 0.50` (annualized)
    - `MAX_DRAWDOWN <= 35%`
    - `2X_FRICTION_STRESS_TOTAL_RETURN >= 0`
    - `NO_CATASTROPHIC_RISK_FAILURE = ZERO`

---

## Final Pre-Inception Blocker Ledger

| Blocker | Resolution State | Governing Evidence |
| :--- | :--- | :--- |
| Bar Data Provider Qualification | `CLOSED` | Manifest `MEC-0015-bar-provider-contract-manifest.json` |
| Historical Quotes Provider Qualification | `CLOSED` | Manifest `MEC-0015-quote-provider-contract-manifest.json` |
| Dividend Provider Qualification | `CLOSED` | Manifest `MEC-0015-dividend-provider-contract-manifest.json` |
| SEC Section 31 Fee Schedule | `CLOSED` | Manifest `MEC-0015-sec31-fee-schedule.json` |
| FINRA TAF Fee Schedule | `CLOSED` | Manifest `MEC-0015-finra-taf-fee-schedule.json` |
| Noise Area Warmup Policy | `CLOSED` | Require full 14 prior completed sessions |
| Daily Volatility Exact Window | `CLOSED` | Canonical MATLAB: 15 simple returns, `ddof=1`, shift 1 |
| Execution Fill Price Model | `CLOSED` | First valid SIP NBBO at or after execution boundary |
| Spread Model | `CLOSED` | Embedded in NBBO fill; no double-counting |
| Slippage Model | `CLOSED` | Baseline standalone $0.001/share per side |
| Commission Model | `CLOSED` | $\max(\$0.35, \$0.0035 \times \text{shares})$ per side |
| Short Borrow Model | `CLOSED` | 0 bps baseline + 50 bps annualized mandatory stress |
| Early-Close Policy | `CLOSED` | Exclude non-standard sessions (210-min) |
| Historical Partitions | `CLOSED` | M1 (2007–2024), M2 (2024–exposed), M3 (prospective) |
| Acceptance Gates | `CLOSED` | M1 & M2 numerical hurdles frozen; trades $\ge 100$ |
**TOTAL REMAINING OPEN BLOCKERS: 0**
**HYP_005 READINESS: `READY_FOR_HUMAN_INCEPTION_AUTHORIZATION`**
