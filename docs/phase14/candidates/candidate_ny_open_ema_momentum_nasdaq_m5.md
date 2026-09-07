# ACASH Phase 14 Research Candidate Note: Session-Open Momentum (NASDAQ-100 M5)

> **Document ID:** `docs/phase14/candidates/candidate_ny_open_ema_momentum_nasdaq_m5.md`  
> **Candidate Identifier:** `NY_OPEN_EMA_MOMENTUM_NASDAQ_M5`  
> **Candidate Family:** `SESSION-EVENT MOMENTUM`  
> **Status:** `UNVALIDATED PROPOSAL` | `NOT REGISTERED` | `NOT SEALED` | `NOT HYP_003`  
> **Authority:** `AGENTS.md` (Strict Fail-Closed, Zero Unverified Claims, Single Canonical Authority), Phase 14 Master Research Architecture (`docs/phase14/phase14_master_research_architecture_plan.md`), Strategy Admission Standard (Phase 17 / ADR-023)  
> **Date:** 2026-09-07  

---

> [!CAUTION]
> ### HARD GOVERNANCE & SAFETY INVARIANTS
> - **THIS CANDIDATE IS NOT HYP_003.**
> - **NO HYPOTHESIS REGISTRATION:** Not entered into `ResearchReInceptionGate` or registered under R1.
> - **NO MARKET DATA ACCESSED:** Zero market data feeds, tick databases, or parquet files queried.
> - **NO BACKTEST EXECUTED:** Zero backtests, simulations, or parameter grid searches executed.
> - **NO DATA REUSE:** Strictly zero access to `HYP_001` partitions, `HYP_002` Validation/OOS partitions, or the 2026 M5 Holdout (Quarantine is mandatory).
> - **CAPITAL & TRADING HARD-LOCKED:** Live Capital Authority = **$0.00**; Live Trading Authority = **LOCKED**; Broker Connection = **DISCONNECTED / NONE**.

---

## 1. Candidate Identity

- **Provisional Candidate Identifier:** `NY_OPEN_EMA_MOMENTUM_NASDAQ_M5`
- **Candidate Family:** `SESSION-EVENT MOMENTUM`
- **Target Instrument:** NASDAQ-100 Equity Index (Claimed: NQ / US100 / NASDAQ100)
- **Timeframe:** 5-minute bars (M5)
- **Trading Mode:** Long & Short (Bi-directional)
- **Anchor Event:** New York Cash Session Open (09:30 Eastern Time)
- **Core Premise:** Directional momentum established on the first qualifying 5-minute candle closing beyond a fast EMA following the session open, combined with a wide volatility stop, adaptive sizing, and a delayed trailing stop.

---

## 2. Source Material & Epistemic Demarcation

The candidate originates from external video commentary and strategy performance screenshots (QuantLab style backtest teardown).

### 2.1 Source Claims Summary
- **Backtest Platform:** Claimed real MT5 backtest
- **Historical Period:** Claimed 2019–2026 (~7 years)
- **Trade Count:** 1,448 trades
- **Net Return:** $+982\%$ cumulative net return
- **Profit Factor (PF):** 1.29
- **Win Rate:** $57\%$
- **Sharpe Ratio:** 1.85
- **Maximum Drawdown:** $20\%$

### 2.2 Claimed In-Sample / Out-of-Sample (IS/OOS) Partition Metrics
The source presents a partitioned performance split:
- **In-Sample (IS):**
  - Net Return: $+160\%$
  - Profit Factor: 1.18
  - $t$-statistic: $+1.9$
  - Win Rate: $56\%$
  - Expectancy: $+0.102\text{R}$
- **Out-of-Sample (OOS):**
  - Net Return: $+316\%$
  - Profit Factor: 1.33
  - $t$-statistic: $+2.6$
  - Win Rate: $59\%$
  - Expectancy: $+0.151\text{R}$
- **Compounding Mathematical Check:**
  $$1.0 \to \text{IS: } +160\% \implies \$26,000 \quad (\times 2.60)$$
  $$\$26,000 \to \text{OOS: } +316\% \implies \$26,000 \times 4.16 = \$108,160 \quad (\text{Total Net Return } = +981.6\% \approx +982\%)$$
  *Note: The published numbers exhibit internal compounding consistency, confirming the headline figure is a compounded multi-period sequence, not an additive sum.*

### 2.3 Claimed Bootstrap / Monte Carlo Resampling
- **Procedure:** 4,000 bootstrap simulations via reshuffling the sequence of the 1,448 empirical trade outcomes.
- **Claimed Chance of Profit:** $100\%$ under the specific resampling procedure.
- **Claimed Median Return:** $\approx +960\%$ (closely aligned with actual $+982\%$).
- **Claimed 90% Outcome Range:** $+166\%$ to $+4,194\%$.
- **Claimed Typical Max Drawdown:** $35\%$.
- **Claimed 95th Percentile Worst Drawdown:** $54\%$.

### 2.4 Strict Epistemic Labeling
In accordance with `AGENTS.md` and Phase 17 standards:
$$\boxed{\text{All Source Performance Claims} \equiv \mathbf{SELF\text{-}REPORTED} \ / \ \mathbf{UNVERIFIED}}$$
These figures reflect marketing and educational presentations. They hold **zero empirical authority** in the ACASH quantitative framework. Under no circumstances will ACASH adjust parameter boundaries, sample filters, or statistical hurdles to match these reported numbers.

---

## 3. What Is Actually Supported by the Source (Visible Mechanics)

Inspection of the source materials confirms the following qualitative structure:

1. **Market & Timeframe:** NASDAQ-100 M5.
2. **Session Context:** New York Session Open.
3. **Trigger Event Text:** *"After the New-York session open, the first candle to close beyond the fast EMA sets the direction — long or short."*
4. **Initial Stop Loss:** Subtitle and card state: *"8×ATR stop"*, *"The stop is 8×ATR of the signal candle"*.
5. **Position Sizing:** Subtitle states: *"1.5% adaptive risk"*.
6. **Trailing Stop:** Card states: *"Once +0.5R in profit the stop trails the slow EMA, never backwards"*, with subtitle specifying *"EMA120 trail"*.
7. **Take Profit:** No fixed target ($R$-multiple) is stated; the system explicitly relies on letting winners run until stopped out by the trailing EMA.

### Critical Strategic Distinction: "First Candle" vs. "First Qualifying Candle"
An earlier retail video claimed:
$$\text{At close of 09:30–09:35 candle: Close} > \text{EMA}_{12} \implies \text{Long, else Short}$$
In contrast, the QuantLab screenshot explicitly specifies:
$$\text{"first candle to close beyond the fast EMA"}$$
This is a profound structural difference:
- If candle 1 (09:30–09:35) closes inside or does not cross beyond the fast EMA, **no trade is triggered**.
- The algorithm monitors subsequent M5 bars (09:35–09:40, 09:40–09:45, etc.) until the **first bar closes beyond the fast EMA**.
- That specific bar becomes the `signal_candle` that establishes directional commitment for the session.

---

## 4. Reverse-Engineered Mechanics (Conceptual Pseudo-Code)

Based on the visible evidence, the conceptual architecture is reconstructed as follows:

```python
# CONCEPTUAL ARCHITECTURE ONLY — NOT IMPLEMENTATION CODE
for each ny_session in calendar:
    signal = None
    signal_candle = None
    
    for candle in session_m5_candles_after_open:
        fast_ema = compute_fast_ema(candle)  # PERIOD UNKNOWN
        
        if signal is None:
            if candle.close > fast_ema:
                signal = Direction.LONG
                signal_candle = candle
                break
            elif candle.close < fast_ema:
                signal = Direction.SHORT
                signal_candle = candle
                break
                
    if signal is not None:
        atr_val = compute_atr(signal_candle)  # PERIOD & TIMING UNKNOWN
        stop_distance = 8.0 * atr_val
        
        # Adaptive risk: 1.5% account equity
        risk_budget = current_equity * Decimal("0.015")
        position_size = risk_budget / (stop_distance * point_value)
        
        # Entry execution (PRICE CONVENTION UNKNOWN: close vs next open)
        entry_price = execute_entry(signal, position_size)
        initial_stop = (entry_price - stop_distance) if signal == Direction.LONG else (entry_price + stop_distance)
        one_r = stop_distance
        trailing_active = False
        current_stop = initial_stop
        
        while in_position:
            # Trailing activation check: profit >= +0.5R
            current_profit = compute_open_pnl_in_r(entry_price, candle, signal, one_r)
            if not trailing_active and current_profit >= Decimal("0.5"):
                trailing_active = True
                
            if trailing_active:
                slow_ema_val = compute_ema_120(candle)  # EXECUTION SEMANTICS UNKNOWN
                if signal == Direction.LONG:
                    current_stop = max(current_stop, slow_ema_val)
                elif signal == Direction.SHORT:
                    current_stop = min(current_stop, slow_ema_val)
                    
            if check_stop_breach(candle, current_stop, signal):
                execute_exit(current_stop)
                break
```

---

## 5. Critical Unknown Parameters (Researcher Degrees of Freedom)

The source material leaves critical operational gaps unstated. ACASH strictly refuses to invent or default these parameters:

| Parameter / Gap | Description of Ambiguity | Epistemic Status |
|---|---|---|
| **1. `FAST_EMA_PERIOD`** | Period of the fast EMA trigger is absent from the screenshot (video mentioned 12, but screenshot does not verify this). | **NOT PROVEN** |
| **2. `ATR_PERIOD`** | Lookback period for ATR (e.g. 14, 20, 50) is completely unstated. | **NOT PROVEN** |
| **3. ATR Calculation Timing** | Whether ATR is evaluated on the completed `signal_candle` or as-of the bar prior ($t-1$). | **NOT PROVEN** |
| **4. Entry Execution Convention** | Whether fill occurs at the exact close of the signal candle or the open of the subsequent M5 candle. | **NOT PROVEN** |
| **5. Session Open Anchor** | Exact time definition of "New York session open" (09:30:00 ET cash equity open vs Globex futures open) and DST handling. | **NOT PROVEN** |
| **6. Session End / Forced Exit** | Whether open trades are mandatorily closed before session end (e.g. 15:55 or 16:00 ET) or held overnight across multiple sessions. | **NOT PROVEN** |
| **7. Trailing Stop Timing Semantics** | Whether the EMA120 trailing stop is evaluated on bar close or dynamically intrabar against real-time bid/ask. | **NOT PROVEN** |
| **8. Instrument & Contract Form** | CME E-mini NQ vs Micro MNQ vs Cash NDX vs Broker CFD (US100 / NAS100). | **NOT PROVEN** |
| **9. Futures Roll Handling** | Roll schedule, volume/open-interest threshold, and back-adjustment method (Panama canal vs ratio). | **NOT PROVEN** |
| **10. Sizing Precision & Limits** | Contract rounding rules (floor, round, ceiling), maximum allowable leverage, and minimum contract steps. | **NOT PROVEN** |
| **11. Frictions & Spread Model** | Commission per contract ($4.50/turn on NQ?), exchange fees, and realistic slippage model during the high-volatility 09:35 open window. | **NOT PROVEN** |
| **12. Historical Date Range** | Exact start and end dates of the claimed 2019–2026 backtest and exact data vendor. | **NOT PROVEN** |
| **13. Holiday / Early Close Rules** | Handling of half-day sessions, market halts, and high-impact macro releases (e.g. NFP, CPI at 08:30 or FOMC at 14:00 ET). | **NOT PROVEN** |

---

## 6. Evidence Classification Matrix

| Dimension | Visible Evidence | ACASH Formal Classification | Rationale |
|---|---|---|---|
| **Core Candidate Concept** | Screenshot & Transcript | `REPORTED` | Idea documented in external public domain. |
| **Visible Strategy Mechanics** | 8 ATR, 1.5% risk, EMA120 trail | `REPORTED` | Explicitly stated in the source image. |
| **Claimed Net Return (+982%)** | Graphic headline | `SELF-REPORTED` | Unverified marketing claim; zero audit trail. |
| **Claimed Profit Factor (1.29)** | Graphic headline | `SELF-REPORTED` | Single reported metric without raw trade logs. |
| **Claimed Sharpe Ratio (1.85)** | Graphic headline | `SELF-REPORTED` | Annualization method and risk-free rate undefined. |
| **Claimed OOS Net Return (+316%)**| OOS summary table | `SELF-REPORTED` | No cryptographic proof of genuine untouched OOS. |
| **4,000 Bootstrap Simulations** | Resampling chart | `SELF-REPORTED` | Reshuffles backtest sequence only; unverified data. |
| **Fast EMA Period** | Absent in screenshot | `NOT PROVEN` | Must be independently hypothesized, not assumed. |
| **ATR Lookback Period** | Absent in screenshot | `NOT PROVEN` | Must be independently hypothesized, not assumed. |
| **Execution Price Semantics** | Absent in screenshot | `NOT PROVEN` | Close vs next open not established. |
| **Session Exit Semantics** | Absent in screenshot | `NOT PROVEN` | Holding period boundary not established. |
| **Transaction Cost Model** | Absent in screenshot | `NOT PROVEN` | Gross vs net PnL impact completely unstated. |
| **Independent Reproducibility** | Not attempted | `NOT PROVEN` | Cannot be validated until exact spec is authored. |
| **Live Trading Authority** | Disconnected | `BLOCKED` | Capital authority locked at $0.00. |

---

## 7. Economic & Behavioral Mechanism Hypotheses

An institutional research candidate cannot exist on indicators alone; it requires an economic rationale:

1. **Opening Cross Price Discovery & Institutional Directional Flow:**
   - At 09:30 ET, the New York equity open unleashes massive liquidity as opening cross-auctions execute and institutional algorithmic programs (VWAP/TWAP) commence.
   - The first decisive directional move closing beyond a fast moving average may capture the prevailing institutional net order imbalance for the morning session.
2. **Volumetric Asymmetry & Volatility Buffering (8×ATR Stop):**
   - Intraday equity index trading frequently fails due to tight stops being hunted during opening chop.
   - An exceptionally wide stop ($8 \times \text{ATR}$) gives the trade immense breathing room, preventing premature shakeouts during the initial 30-minute auction digestion.
3. **Asymmetric Payoff Engine (Delayed Trailing Stop + Letting Winners Run):**
   - Activating the trailing stop only after $+0.5\text{R}$ in profit prevents tightening the stop prematurely during early noise.
   - Once activated, ratcheting against the slow EMA120 transforms the trade into a pure trend-following ride, truncating left-tail losses while capturing fat right-tail momentum drifts.
4. **Counter-Hypotheses (Failure Modes to Test):**
   - *Friction Erasure:* Entering volatile M5 breakouts on NQ can incur 2–4 ticks of slippage. In choppy sessions, repeated whipsaws across the fast EMA could bleed capital through friction.
   - *Overnight Mean Reversion:* Breakouts in the first 15 minutes frequently trap retail momentum traders before reversing into overnight balance areas.
   - *Tail Risk of Wide Stops:* In rare liquidation events, an $8 \times \text{ATR}$ stop represents a massive nominal loss that could severely impair compounding.

---

## 8. Reproducibility & Data Governance Requirements

If this candidate is ever formally promoted to research design:
1. **Independent CME NQ Dataset:** High-precision M1 or tick-level continuous futures with volume-based roll rules and explicit bid/ask quotes.
2. **Strict Timezone Normalization:** Canonical UTC timestamps with deterministic US DST handling.
3. **Rigorous Friction Model:** Round-turn commission ($4.50/contract), exchange fees, and dynamic slippage model ($\ge 1\text{ tick}$ entry, $\ge 1\text{ tick}$ exit).
4. **Data Quarantine Hard Invariant:**
   - `HYP_001` 2026 M5 Holdout (`6060..9999`): **FORBIDDEN / QUARANTINED**
   - `HYP_002` H4 Validation (`3751..4996`) & OOS (`5009..6230`): **FORBIDDEN / QUARANTINED**
   - This candidate must utilize an entirely disjoint, independently registered dataset window.

---

## 9. Researcher Degrees of Freedom Audit (Anti-Overfitting Contract)

The high number of unspecified parameters presents severe data-snooping risks:
- Testing $\text{Fast EMA} \in [8, 9, 10, 12, 14, 20, 21]$
- Testing $\text{ATR Period} \in [10, 14, 20]$
- Testing $\text{Stop Multiplier} \in [4, 6, 8, 10] \times \text{ATR}$
- Testing $\text{Trail Activation} \in [0.25, 0.50, 0.75, 1.00]\text{R}$
- Testing $\text{Slow Trail EMA} \in [50, 100, 120, 144, 200]$

If a researcher iterates across this grid until matching the $+982\%$ headline, the result will be a pure statistical artifact of multiple testing ($K \ge 1,000$).

> [!CAUTION]
> **ANTI-COPY RULE:**  
> ACASH will NEVER reverse-engineer or optimize parameters to reproduce the source screenshot. If a future hypothesis is registered, its parameter space must be small, theoretically justified, and deflated using the White (2000) Reality Check or Bailey & López de Prado (2014) Deflated Sharpe Ratio.

---

## 10. Methodological Interpretations: Monte Carlo & IS/OOS

### 10.1 Monte Carlo Trade-Sequence Resampling
The screenshot demonstrates 4,000 bootstrap resamplings of the 1,448 historical trade outcomes.
- **Scientific Value:** It validates that the strategy's historical performance was not merely a lucky sequence of consecutive wins (sequence risk / path dependency analysis).
- **Epistemic Limitation:** It assumes the underlying trade return distribution is stationary and perfectly known. It provides **zero evidence** regarding parameter stability, future regime shifts, liquidity deterioration, or structural breaks. The claimed "100% chance of profit" applies strictly to the permutation model of past trades, **NOT to future market reality**.

### 10.2 IS / OOS Split Claim
The source claims parameters were selected on IS and evaluated on untouched OOS.
- While the OOS metrics (PF 1.33, $t = +2.6$) appear stronger than IS, this remains a **self-reported methodology claim**. Without cryptographic hashes of the pre-registered split and immutable code commits prior to OOS exposure, it cannot be verified whether OOS data inadvertently informed parameter selection.

---

## 11. Relationship to Existing Hypotheses (`HYP_001` & `HYP_002`)

- `HYP_001` (EURUSD M5) & `HYP_002` (EURUSD H4): Both examined *univariate unconditional rolling price momentum* on spot FX and were **TERMINALLY FALSIFIED** ($0/9$ and $0/12$ qualified).
- `NY_OPEN_EMA_MOMENTUM_NASDAQ_M5`: Represents an entirely distinct research family:
  $$\text{Asset: US Equity Index (NQ)} \ne \text{Spot FX (EURUSD)}$$
  $$\text{Conditioning: Opening Cross Event} \ne \text{Unconditional Rolling Lookback}$$
  $$\text{Exit Engine: Delayed Trailing Engine} \ne \text{Fixed Bar Horizon}$$
- **Epistemic Boundary:** Being methodologically different **does NOT mean it is superior or more likely to work**. It simply means the econometric falsification of `HYP_001` and `HYP_002` does not mathematically rule out opening-session index momentum.

---

## 12. Candidate Research Question (Objective Scientific Form)

> *"Does the directional state established by the first qualifying 5-minute bar closing beyond a pre-registered fast EMA following the New York equity session open contain statistically significant, exploitable predictive information regarding subsequent intraday NASDAQ-100 returns, after incorporating realistic execution slippage, exchange fees, dynamic volatility stops, and multiple-testing deflation?"*

---

## 13. Conditions Required Before Any Future Step R1 Consideration

This candidate **CANNOT** advance to Step R1 (Pre-Registration) until:
1. [ ] **Human Authorization of Phase 14 Architecture:** Formal sign-off on `docs/phase14/phase14_master_research_architecture_plan.md`.
2. [ ] **Resolution of Primary Specification Gaps:** Explicit mathematical declaration of `FAST_EMA_PERIOD`, `ATR_PERIOD`, entry execution convention, and session flat time without data snooping.
3. [ ] **Independent Data Pipeline:** Verified CME NQ data ingested into canonical Arrow format outside quarantined partitions.
4. [ ] **Pre-Registration of Multiple-Testing Grid:** Exact declaration of trial space $K$ with Deflated Sharpe Ratio (DSR) and Family-Wise Error Rate (FWER) controls.
5. [ ] **Formal ResearchReInceptionGate Submission:** Complete gate evaluation in `src/acash/research/reinception.py`.

---

## 14. Human Decision Checkpoint & Recommendation

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    RESEARCH CANDIDATE EVALUATION VERDICT                  │
├───────────────────────────────────┬───────────────────────────────────────┤
│ Candidate Identifier              │ NY_OPEN_EMA_MOMENTUM_NASDAQ_M5        │
│ Evaluated Candidate Family        │ SESSION-EVENT MOMENTUM                │
│ Target Asset                      │ NASDAQ-100 (M5)                       │
│ Source Claims Credibility         │ SELF-REPORTED / UNVERIFIED            │
│ Mechanical Completeness           │ INCOMPLETE (13 gaps unproven)         │
│ Epistemic State                   │ UNVALIDATED PROPOSAL                  │
│ HYP_003 Creation                  │ STRICTLY PROHIBITED                   │
│ Recommendation                    │ WORTH FURTHER PHASE 14 INVESTIGATION  │
│                                   │ (SUBJECT TO GAP RESOLUTION)           │
└───────────────────────────────────┴───────────────────────────────────────┘
```

### Recommendation Rationale
- **Classification:** **`WORTH FURTHER PHASE 14 INVESTIGATION`**
- **Justification:** The conceptual architecture (combining opening price discovery, wide volatility buffering, adaptive sizing, and delayed trailing) presents a plausible economic mechanism that is fundamentally distinct from the failed unconditional FX momentum models (`HYP_001` / `HYP_002`).
- **Critical Mandate:** It is **NOT READY** for R1 hypothesis pre-registration. It must remain an `UNVALIDATED PROPOSAL` within Phase 14 until the 13 critical specification gaps (especially fast EMA period, ATR period, and session exit rules) are formally resolved from primary principles rather than curve-fitting.
