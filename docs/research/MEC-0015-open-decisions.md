# MEC-0015: Open Architectural, Econometric & Operational Decisions

This document establishes the binding checklist of open design and governance decisions required before any hypothesis specification (e.g. `HYP_005`) may be registered under the **MEC-0015** mechanism family.

Every decision below is classified as **`OPEN`** and blocks empirical registration until formally ratified by human authority.

---

## Decision Checklist

### 1. Exact Execution Bar & Price Semantics
- **Decision ID:** `DEC-MEC015-01`
- **Current Status:** `OPEN_BLOCKER`
- **Description:** At the 30-minute decision timestamp $HH:MM$ (e.g., 10:00, 10:30):
  - *Option A:* Order executes at the Close price of the 1-minute bar ending at $HH:MM$ (assumes zero latency execution at bar close).
  - *Option B:* Order evaluates on the bar ending at $HH:MM$ and executes at the Open price of the subsequent bar ending at $HH:01$ (realistic 1-bar execution delay).
  - *Option C:* Order evaluates against the NBBO quote prevailing at $HH:MM:00$ with explicit simulated queue / fill modeling.
- **Literature Precedent:** Ambiguous; implicitly assumes bar-close or next-open execution.

---

### 2. Exact Session VWAP Definition & Numerator Convention
- **Decision ID:** `DEC-MEC015-02`
- **Current Status:** `OPEN_BLOCKER`
- **Description:** For the regular-session VWAP trailing stop:
  - *Option A:* $\text{VWAP} = \frac{\sum \text{Close}_i \cdot \text{Volume}_i}{\sum \text{Volume}_i}$
  - *Option B:* $\text{VWAP} = \frac{\sum \text{TypicalPrice}_i \cdot \text{Volume}_i}{\sum \text{Volume}_i}$ where $\text{TypicalPrice} = (H+L+C)/3$.
  - *Option C:* Exact tick-level SIP VWAP aggregated across all exchange prints.
- **Literature Precedent:** States "VWAP using regular-session market hours", but leaves numerator convention unspecified. External replications indicate material trigger discrepancies depending on choice.

---

### 3. Realistic Transaction Cost & Fee Model
- **Decision ID:** `DEC-MEC015-03`
- **Current Status:** `OPEN_BLOCKER`
- **Description:** The paper assumes $\$0.0035$/share commission and $\$0.0010$/share slippage. ACASH must establish a conservative fee schedule:
  - *Commissions:* Institutional direct-market-access (DMA) vs. retail broker tiered vs. zero-commission with PFOF latency.
  - *Exchange & Regulatory Fees:* SEC Section 31 fee (e.g. $\$0.0000278 \times \text{Principal}$ on sells) + FINRA Trading Activity Fee (TAF) ($\$0.000166$/share, capped at $\$8.30$).
  - *Minimum Ticket Charge:* Whether a minimum ticket fee (e.g. $\$1.00$) applies.
- **Literature Precedent:** Oversimplified retail friction model.

---

### 4. Bid-Ask Spread Crossing & Slippage Model
- **Decision ID:** `DEC-MEC015-04`
- **Current Status:** `OPEN_BLOCKER`
- **Description:** Intraday market orders cross the full bid-ask spread:
  - *Option A:* Fixed $\$0.01$/share half-spread (minimum quote tick for SPY).
  - *Option B:* Dynamic historical spread modeling based on contemporaneous NBBO width.
  - *Option C:* Volatility-scaled slippage penalty: $\text{Slippage} = \max(\$0.01, k \cdot \sigma_{\text{bar}})$.
- **Literature Precedent:** Uses $\$0.001$/share, which is substantially smaller than the minimum $\$0.01$ quote spread for US equities.

---

### 5. Daily Volatility Targeting & Return Definition
- **Decision ID:** `DEC-MEC015-05`
- **Current Status:** `OPEN_BLOCKER`
- **Description:** In calculating the 14-day trailing realized volatility $\sigma_{\text{SPY}, t}$:
  - *Return Space:* Simple close-to-close returns vs. log returns vs. open-to-close returns.
  - *Bessel Correction:* Sample variance with $N-1 = 13$ degrees of freedom vs. population variance with $N = 14$.
  - *Mean Assumption:* De-meaned sample variance vs. zero-mean assumed variance.
- **Literature Precedent:** Standard sample standard deviation of daily returns, but exact formula parameters are omitted.

---

### 6. Corporate Actions, Dividends & Split Treatment
- **Decision ID:** `DEC-MEC015-06`
- **Current Status:** `OPEN_BLOCKER`
- **Description:** SPY distributes quarterly dividends resulting in overnight price drops on ex-dividend dates:
  - *Intraday Bars:* Unadjusted prices must be used for live/execution simulation to preserve real quote boundaries.
  - *Daily Volatility Lookback:* Dividend-adjusted daily returns vs. unadjusted returns.
  - *Overnight Gap Anchor:* On ex-date, does $\text{Close}[t-1]$ reflect unadjusted raw close or dividend-adjusted prior close?
- **Literature Precedent:** Silent on ex-dividend overnight gap impact on Noise Area boundaries.

---

### 7. Early-Close Days Policy
- **Decision ID:** `DEC-MEC015-07`
- **Current Status:** `OPEN_BLOCKER`
- **Description:** Sessions closing early at 13:00 EST (e.g., day after Thanksgiving, Christmas Eve):
  - *Option A (Exclusion):* Quarantined and excluded from trade execution and evaluation.
  - *Option B (Truncated Timeline):* Scaled decision epochs ending with forced liquidation at 13:00 EST.
- **Literature Precedent:** Completely silent; standard full 09:30–16:00 trading days assumed.

---

### 8. Market Data Provider & Feed Qualification
- **Decision ID:** `DEC-MEC015-08`
- **Current Status:** `OPEN_BLOCKER`
- **Description:**
  - *Provider:* Alpaca Historical Data vs. Polygon vs. Databento vs. raw SIP tapes.
  - *Feed Tape:* Full SIP Consolidated Tape vs. single-exchange feed (e.g. IEX / Investors Exchange).
  - *Bar Construction:* Pre-aggregated 1-minute bars vs. synthesized bars aggregated from raw trade prints with condition code filtering (excluding out-of-sequence, derivatively priced, or late prints).
- **Literature Precedent:** Uses IQFeed 1-minute bars.

---

### 9. Missing Bar & Zero-Volume Handling
- **Decision ID:** `DEC-MEC015-09`
- **Current Status:** `OPEN_BLOCKER`
- **Description:** While SPY is the most liquid ETF in the world, occasional 1-minute intervals may exhibit zero trades (especially in historical early years) or missing feeds:
  - *Policy:* Forward-fill prior close vs. fail-closed data contract exception.
- **Literature Precedent:** Silent.

---

### 10. Warmup Window & Historical Burn-In
- **Decision ID:** `DEC-MEC015-10`
- **Current Status:** `OPEN_BLOCKER`
- **Description:** The strategy requires 14 prior days of regular-session 1-minute data for the Noise Area and 14 prior daily returns for volatility sizing.
  - *Policy:* The first 14 eligible calendar trading days of any test partition must be designated as non-trading warmup sessions. Zero trades may execute during warmup.
- **Literature Precedent:** Consistent with 14-day lookback requirement.

---

### 11. Final Market-Close Execution Rule (EOD Flat)
- **Decision ID:** `DEC-MEC015-11`
- **Current Status:** `OPEN_BLOCKER`
- **Description:** Strategy mandates 100% cash overnight:
  - *Option A:* Market-On-Close (MOC) order submitted to the NYSE Arca closing auction at 15:45 EST to cross at the 16:00:00 official close.
  - *Option B:* Continuous market order executed at 15:59:00 EST on the final regular-session 1-minute bar.
- **Literature Precedent:** States "positions are closed by market close", without specifying auction vs. continuous execution.

---

### 12. Short-Sale Mechanics & Margin Rules
- **Decision ID:** `DEC-MEC015-12`
- **Current Status:** `OPEN_BLOCKER`
- **Description:**
  - *Borrow Availability:* SPY is generally Easy-To-Borrow (ETB), but borrow fees and locate confirmations must be contractually defined.
  - *Short Surcharge:* Annualized borrow rate (e.g. 0.25%–0.50% annualized) pro-rated for intraday holding?
  - *Uptick Rule:* Compliance with SEC Rule 201 (alternative uptick rule when SPY drops $\ge 10\%$).
- **Literature Precedent:** Assumes frictionless symmetric short execution.

---

### 13. Benchmark Definition & Evaluation Horizon
- **Decision ID:** `DEC-MEC015-13`
- **Current Status:** `OPEN_BLOCKER`
- **Description:**
  - *Primary Benchmark:* Buy-and-hold total return of SPY ETF over the identical evaluation period.
  - *Secondary Benchmark:* Risk-matched buy-and-hold (e.g., cash + SPY matched to strategy realized volatility).
- **Literature Precedent:** Compares directly against raw SPY buy-and-hold.

---

### 14. Historical Sample Partitioning & Contamination Governance
- **Decision ID:** `DEC-MEC015-14`
- **Current Status:** `OPEN_BLOCKER`
- **Description:**
  - How to partition data across Discovery / In-Sample Calibration, Internal Validation, and External Holdout.
  - Resolution of the fact that 2007–2024 is exposed in the original paper, and May 2024–March 2026 is exposed in public independent replications.
  - Deciding whether 2023–2026 can be considered a valid holdout or if an alternative forward-walking protocol is required.
- **Literature Precedent:** N/A (Governance requirement).

---

### 15. Future Economic Acceptance & Invalidation Thresholds
- **Decision ID:** `DEC-MEC015-15`
- **Current Status:** `OPEN_BLOCKER`
- **Description:** Explicit numerical gates for candidate qualification:
  - Minimum Annualized Net Sharpe Ratio (e.g., $\text{Sharpe}_{\text{net}} \ge 1.00$ or $\ge 0.75$).
  - Maximum Permissible Drawdown (e.g., $\text{MaxDD} \le 20.0\%$).
  - Minimum Realized Trade Count (e.g., $N_{\text{trades}} \ge 250$).
  - Cost-Stress Survivability: Net annualized Sharpe must remain $> 0.50$ when modeled friction is multiplied by $2.0\times$.
  - Invalidation Criteria: Explicit statistical or drawdown triggers that permanently terminate the hypothesis.
- **Literature Precedent:** N/A (Governance requirement).
