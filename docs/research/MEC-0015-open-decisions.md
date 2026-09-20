# MEC-0015: Architectural, Econometric & Operational Decisions Ledger

This document tracks the status of all architectural, mathematical, and execution decisions for **MEC-0015**. Decisions are categorized into **`RESOLVED`** (grounded in audited author reference implementations or canonical literature) and **`OPEN_BLOCKER`** (requiring formal human ratification prior to registering `HYP_005`).

---

## Master Decision Summary

| Decision ID | Description | Current Status | Governing Authority / Classification |
| :--- | :--- | :--- | :--- |
| `DEC-MEC015-01` | Exact Execution Bar & Price Semantics | `PARTIALLY_RESOLVED` | Signal = 1-min Close, 1-min exposure lag; Real fill model = `OPEN` |
| `DEC-MEC015-02` | Exact Session VWAP Definition | `RESOLVED` | Typical Price $(H+L+C)/3$, cumulative RTH, daily reset |
| `DEC-MEC015-03` | Transaction Cost & Fee Schedule | `PARTIALLY_RESOLVED` | Literature commission = $\max(\$0.35, \$0.0035 \times \text{sh})$; SEC/TAF = `OPEN_BLOCKER` |
| `DEC-MEC015-04` | Bid-Ask Spread & Slippage Model | `OPEN_BLOCKER` | Corrected: full spread $0.01, half spread $0.005; NBBO spread model open |
| `DEC-MEC015-05` | Daily Volatility Targeting Definition | `PARTIALLY_RESOLVED` | Simple returns, current day excluded; 14 vs 15 days cardinality = `OPEN_BLOCKER` |
| `DEC-MEC015-06` | Corporate Actions & Dividend Adjustment| `RESOLVED` | Band anchor adjusted by dividend ($\text{prev\_close} - \text{div}$); unadjusted intraday bars |
| `DEC-MEC015-07` | Early-Close Days Policy | `OPEN_BLOCKER` | Quarantine/exclusion vs truncated 13:00 timeline |
| `DEC-MEC015-08` | Market Data Provider & Feed Qualification| `OPEN_BLOCKER` | `ALPACA_SIP_BAR_MAPPING = UNQUALIFIED` |
| `DEC-MEC015-09` | Missing Bar & Zero-Volume Handling | `OPEN_BLOCKER` | Forward-fill vs fail-closed exception policy |
| `DEC-MEC015-10` | Warmup Window & Historical Burn-In | `PARTIALLY_RESOLVED` | Nominal 14 sessions; 13 vs 14 min_periods = `OPEN_NARROW_DECISION` |
| `DEC-MEC015-11` | Market-Close Execution Rule (EOD Flat) | `PARTIALLY_RESOLVED` | Zero overnight inventory resolved; MOC auction vs 15:59 continuous open |
| `DEC-MEC015-12` | Short-Sale Mechanics & Margin Rules | `OPEN_BLOCKER` | SPY borrow availability & locate fees; long-only substitution prohibited |
| `DEC-MEC015-13` | Benchmark Definition | `RESOLVED` | Primary benchmark = SPY buy-and-hold total return |
| `DEC-MEC015-14` | Historical Sample Partitioning | `OPEN_MAJOR_GOVERNANCE_DECISION` | 2023–2026 exposed in replications; partition design requires ratification |
| `DEC-MEC015-15` | Economic Acceptance & Invalidation Gates| `OPEN_BLOCKER` | Strategy-native gates (Net Sharpe, Cost-Stress survivability, Max DD) |

---

## Detailed Decision Records

### 1. Exact Execution Bar & Price Semantics
- **Decision ID:** `DEC-MEC015-01`
- **Current Status:** `PARTIALLY_RESOLVED`
- **Resolved Elements:**
  - `SIGNAL_PRICE_FIELD = RESOLVED_AUTHOR_REFERENCE_IMPLEMENTATION` (Evaluated on 1-minute `Close`).
  - `ENTRY_REQUIRES_VWAP_CONFIRMATION = RESOLVED_TRUE` (Long: Close > Band AND Close > VWAP; Short: Close < Band AND Close < VWAP).
  - `DECISION_FREQUENCY = 30_MINUTES` (`min_from_open % 30 == 0`, `America/New_York` / ET).
  - `REFERENCE_BACKTEST_EXPOSURE_LAG = RESOLVED_1_MINUTE` (Exposure lagged by 1 minute: `position = signal.shift(1)`, P&L begins at $t+1$).
  - `STOP_EVALUATION_FREQUENCY = RESOLVED_30_MINUTE_DECISION_EPOCHS`.
  - `FLAT_SIGNAL_AT_REBALANCE_CLOSES_POSITION = RESOLVED_AUTHOR_IMPLEMENTATION`.
  - `OPPOSITE_SIGNAL_FLIPS_POSITION = RESOLVED_AUTHOR_IMPLEMENTATION`.
- **Remaining Open Element:**
  - `ACASH_EXECUTION_FILL_PRICE_MODEL = OPEN`: In live or realistic simulated execution, whether orders cross at next bar Open or prevailing NBBO quote.

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
- **Current Status:** `PARTIALLY_RESOLVED`
- **Resolved Elements:**
  - Literature baseline commission: $\max(\$0.35, \$0.0035 \times \text{shares})$ per order execution side.
  - Literature slippage separated: `PAPER_REPORTED_SLIPPAGE = 0.0010` is a textual reporting convention, not present as a standalone continuous deduction in author reference code.
- **Remaining Open Elements:**
  - `ACASH_REGULATORY_FEE_MODEL = OPEN_BLOCKER`: Regulatory fees are time-varying. SEC Section 31 fee (e.g., FY2026 rate $\$20.60$ per $\$1,000,000$ of principal on sells effective 4 April 2026) and FINRA TAF must follow historical schedules or an explicit conservative constant proxy.

---

### 4. Bid-Ask Spread Crossing & Slippage Model
- **Decision ID:** `DEC-MEC015-04`
- **Current Status:** `OPEN_BLOCKER`
- **Terminology Correction:**
  - Under SEC Rule 612, US equities priced $> \$1.00$ trade with a minimum quoting increment of $\$0.01$.
  - In a standard one-tick market: $\text{Full Spread} = \$0.01/\text{share} \implies \text{Half-Spread} = \$0.005/\text{share}$.
  - The previous draft stating "minimum $0.01 half-spread" was erroneous.
  - SEC Rule 612 amendments introducing $\$0.005$ quoting tick categories have compliance delayed until **November 2026**.
- **Remaining Open Blocker:**
  - `ACASH_SPREAD_MODEL = OPEN_BLOCKER`: Baseline ACASH friction must model contemporaneous historical NBBO spreads or a ratified conservative proxy.

---

### 5. Daily Volatility Targeting & Return Definition
- **Decision ID:** `DEC-MEC015-05`
- **Current Status:** `PARTIALLY_RESOLVED`
- **Resolved Elements:**
  - `DAILY_VOL_RETURN_TYPE = SIMPLE_CLOSE_TO_CLOSE`: $\text{daily\_ret}_t = \text{Close}_t / \text{Close}_{t-1} - 1$.
  - `CURRENT_DAY_RETURN_IN_VOL = PROHIBITED`: Current day return strictly excluded from sizing volatility.
  - Sizing parameters: $\sigma_{\text{target}} = 0.02$, $\max \text{leverage} = 4.0\times$, sizing price = Session Open, share rounding = nearest integer.
- **Remaining Open Blocker:**
  - `DAILY_VOL_WINDOW_EXACT_CARDINALITY = OPEN_BLOCKER`: Discrepancy between prose (14 days) and reference code indexing (14 vs 15 returns, pandas `ddof=1` vs MATLAB default).

---

### 6. Corporate Actions, Dividends & Split Treatment
- **Decision ID:** `DEC-MEC015-06`
- **Current Status:** `RESOLVED`
- **Governing Specification:**
  - `BAND_PREVIOUS_CLOSE_DIVIDEND_TREATMENT = RESOLVED_AUTHOR_IMPLEMENTATION`:
    $$\text{prev\_close\_adjusted} = \text{Close}[t-1, 16:00] - \text{dividend}[t]$$
  - Overnight gap anchors: $\text{UpperAnchor} = \max(\text{Open}, \text{prev\_close\_adjusted})$, $\text{LowerAnchor} = \min(\text{Open}, \text{prev\_close\_adjusted})$.
  - Intraday bars remain unadjusted to preserve real execution boundaries.

---

### 7. Early-Close Days Policy
- **Decision ID:** `DEC-MEC015-07`
- **Current Status:** `OPEN_BLOCKER`
- **Description:** Sessions closing early at 13:00 ET (e.g., day after Thanksgiving, Christmas Eve):
  - *Option A (Quarantine/Exclusion):* Excluded from trade execution and performance evaluation.
  - *Option B (Truncated Schedule):* Proportionally scaled decision epochs ending at 13:00 ET.
- Literature is silent; human ratification required.

---

### 8. Market Data Provider & Feed Qualification
- **Decision ID:** `DEC-MEC015-08`
- **Current Status:** `OPEN_BLOCKER`
- **Description:** Alpaca SIP 1-minute OHLCV bar mapping must be qualified for RTH filtering, volume completeness relative to IQFeed, corporate action handling, and missing-minute behavior.
- Status: `ALPACA_SIP_BAR_MAPPING = UNQUALIFIED`. Zero network calls permitted.

---

### 9. Missing Bar & Zero-Volume Handling
- **Decision ID:** `DEC-MEC015-09`
- **Current Status:** `OPEN_BLOCKER`
- **Description:** Formal policy for missing 1-minute bars during RTH (forward-fill prior close vs fail-closed data contract error).

---

### 10. Warmup Window & Historical Burn-In
- **Decision ID:** `DEC-MEC015-10`
- **Current Status:** `PARTIALLY_RESOLVED`
- **Resolved Elements:**
  - Nominal 14 completed prior sessions required (`NOISE_AREA_LOOKBACK = 14_PRIOR_SESSIONS`).
- **Remaining Open Element:**
  - `NOISE_AREA_WARMUP_MIN_PERIODS = OPEN_NARROW_DECISION`: Author Python uses `min_periods=13` for early 1-session acceleration; ACASH must decide whether to allow 13 or require strict 14.

---

### 11. Market-Close Execution Rule (EOD Flat)
- **Decision ID:** `DEC-MEC015-11`
- **Current Status:** `PARTIALLY_RESOLVED`
- **Resolved Elements:**
  - Forced flat at 16:00 ET; zero overnight inventory.
- **Remaining Open Element:**
  - MOC closing auction order at 15:45 ET vs continuous market order on 15:59 ET bar.

---

### 12. Short-Sale Mechanics & Margin Rules
- **Decision ID:** `DEC-MEC015-12`
- **Current Status:** `OPEN_BLOCKER`
- **Description:** SPY borrow availability, locate confirmation, and intraday borrow fee schedules. Long-only substitution is strictly prohibited as an undeclared baseline replacement.

---

### 13. Benchmark Definition & Evaluation Horizon
- **Decision ID:** `DEC-MEC015-13`
- **Current Status:** `RESOLVED`
- **Governing Specification:** Primary benchmark is SPY buy-and-hold total return over the identical evaluation horizon.

---

### 14. Historical Sample Partitioning & Contamination Governance
- **Decision ID:** `DEC-MEC015-14`
- **Current Status:** `OPEN_MAJOR_GOVERNANCE_DECISION`
- **Description:** 2007–2024 is exposed in the original paper (SSRN revision Sept 2025); May 2024–March 2026 is exposed in public replications (Paz Sheimy, Delgado); 2017–2022 was evaluated in ACASH `HYP_003`/`HYP_004`. 2023–2026 cannot be honestly claimed as a pristine external holdout. Partition design requires separate human ratification.

---

### 15. Future Economic Acceptance & Invalidation Thresholds
- **Decision ID:** `DEC-MEC015-15`
- **Current Status:** `OPEN_BLOCKER`
- **Description:** Strategy-native numerical gates:
  - Minimum Annualized Net Sharpe Ratio.
  - Maximum Permissible Drawdown.
  - Minimum Realized Trade Count.
  - Cost-Stress Survivability ($2.0\times$ friction multiplier).
  - Explicit fail-closed invalidation boundaries.
