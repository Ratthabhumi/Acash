# ACASH Phase 14 — Research Execution & Timing Clarification Note

**STATUS:** NON-GOVERNING PLANNING NOTE  
**AUTHORITY:** NONE  
**PURPOSE:** Research execution and timing clarification  
**IMPLEMENTATION AUTHORIZATION:** NONE  
**BACKTEST AUTHORIZATION:** NONE  
**PAPER AUTHORIZATION:** NONE  
**LIVE AUTHORIZATION:** NONE  
**DATE:** 2026-09-13  
**DOCUMENT:** `docs/phase14/research_execution_timing_note.md`  

---

## 1. Executive Summary & Epistemic Boundary

This note provides operational and planning clarifications regarding quantitative research execution following Gate G7 / Stage S11 infrastructure validation. 

### Non-Negotiable Invariants:
- **Zero Governance Mutation:** This note does NOT alter, amend, or supersede [`docs/ROADMAP.md`](../ROADMAP.md), [`AGENTS.md`](../../AGENTS.md), or ratified governance records.
- **Zero Hypothesis Creation:** `HYP_003` is **NOT CREATED**. No trading hypothesis is registered or authorized by this document.
- **Phase 13 Step 9 Preserved:** Phase 13 Step 9 (the 90-day continuous paper-forward run) remains **LOCKED / NOT AUTHORIZED**. Nothing in this document shortens, replaces, or reinterprets that requirement.
- **Capital & Order Invariants:** Canonical capital remains **$0.00**; `NO_REAL_ORDERS=true` remains strictly enforced.
- **Active Soak Safety:** This document does NOT modify, restart, or interact with the active homelab G7 soak (`E3.5-20260913-025117-de2762`).

---

## 2. Infrastructure Validation vs. Alpha Qualification: What Gate G7 Proves

The canonical Gate G7 / Stage S11 6-hour continuous soak is strictly an **infrastructure, pipeline, and runtime validation exercise**.

For the Binance M1 stream (`BTCUSDT`), 6 continuous hours yields approximately 360 one-minute bars:
$$6.00 \text{ hours} \times 60 \text{ bars/hour} = 360 \text{ bars}$$

### What Gate G7 Proves:
- M1 feed stream continuity and socket/polling stability.
- Bar ingestion, sequence numbering, and payload parsing integrity.
- Duplicate timestamp rejection and in-memory deduplication.
- Journal persistence under chained SHA-256 cryptographic hashing.
- Disconnect and network-error observability and logging.
- Container runtime stability with zero unexpected restarts (`RestartCount == 0`).
- Memory RSS bounded below the 512 MiB operational threshold.
- VictoriaMetrics and Prometheus telemetry scrape continuity.
- Strict fail-closed boundary enforcement upon terminal disconnect.

### What Gate G7 Does NOT Prove:
- It does **NOT** prove trading strategy profitability or positive expectancy.
- It does **NOT** establish or indicate alpha persistence.
- It does **NOT** provide a statistically valid Sharpe ratio or return distribution.
- It does **NOT** evaluate market regime robustness or drawdowns across varied macro cycles.
- It does **NOT** select an approved strategy or candidate model.
- It does **NOT** establish live production trading readiness.

$$\begin{aligned}
\text{Gate G7 answers:} &\quad \mathbf{\text{"Can we trust the experimental and runtime execution infrastructure?"}} \\
\text{Gate G7 does NOT answer:} &\quad \mathbf{\text{"Which strategy has a durable, statistically significant trading edge?"}}
\end{aligned}$$

The ~360-bar observation must **never** be treated as a statistical sample for trading strategy validation.

---

## 3. Historical Lookback vs. Real-Time Waiting

A critical distinction must be maintained between **historical data lookback** and **real-time calendar waiting**:

> **"1 to 4 years of historical data" refers to HISTORICAL LOOKBACK COVERAGE.**  
> **It does NOT mean ACASH must wait 1 to 4 calendar years in real time before conducting research.**

Once experimental infrastructure is validated, historical market datasets may be acquired retrospectively where data authority, provenance, licensing, and governance permit. A 4-year historical dataset of 1-minute bars can be ingested, validated, and analyzed computationally in hours or days, not years.

### Post-G7 Research Lifecycle Pipeline:

```text
Gate G7 Infrastructure Validation
              ↓
Historical Dataset Acquisition (Retrospective)
              ↓
Data Qualification & Stationarity Audit
              ↓
Specific Research Question & Mechanism
              ↓
Human-Authorized Hypothesis (e.g. HYP_XXX)
              ↓
Registered Empirical Search / Trial Census
              ↓
In-Sample Backtest Execution (Gate G1 / R1)
              ↓
Out-of-Sample, Walk-Forward & Cost Sensitivity Validation
              ↓
Strategy Qualification Candidate
              ↓
Separate Human Paper-Trading Authorization (Gate G4)
              ↓
Canonical Forward Paper Validation (Phase 13 Step 9)
```

---

## 4. Non-Binding Research Planning Heuristics (BTC M1)

To aid in computational capacity planning, the following bar counts illustrate approximate sample sizes for 1-minute bars in continuous 24/7 markets:

- **1 Day:** $\approx 1,440$ bars
- **7 Days:** $\approx 10,080$ bars
- **30 Days:** $\approx 43,200$ bars
- **90 Days:** $\approx 129,600$ bars
- **6 Months:** $\approx 262,800$ bars
- **1 Year:** $\approx 525,600$ bars
- **2 Years:** $\approx 1,051,200$ bars
- **4 Years:** $\approx 2,102,400$ bars

### Non-Binding Research Scale Heuristics:
- **$< 1,000$ bars:** Sanity check, pipeline verification, harness integration, and software prototyping only.
- **$5,000 - 10,000$ bars:** Exploratory territory for basic feature engineering and descriptive data inspection.
- **$20,000 - 50,000+$ bars:** Potentially useful scale for initial hypothesis exploration across limited regimes.
- **$100,000+$ bars:** Useful scale for richer intraday regime segmentation and parameter sensitivity investigation.
- **$\sim 6 - 12$ months M1 ($\approx 260\text{k} - 525\text{k}$ bars):** Reasonable baseline historical research target for initial model formulation.
- **$\sim 2 - 4$ years M1 ($\approx 1\text{M} - 2\text{M}$ bars):** Desirable historical lookback coverage for multi-regime robustness and out-of-sample validation.

```text
================================================================================
                    CRITICAL EPISTEMIC GOVERNANCE NOTICE
- THE ABOVE FIGURES ARE NON-BINDING PLANNING HEURISTICS ONLY.
- THEY DO NOT CONSTITUTE A GOVERNANCE GATE.
- THEY DO NOT CONSTITUTE A STRATEGY ADMISSION THRESHOLD.
- "500,000 BARS" DOES NOT EQUAL A VALIDATED STRATEGY.
================================================================================
```

### Canonical Statistical Authority:
Strategy admission in ACASH is governed exclusively by [`docs/architecture/strategy_admission_standard.md`](../architecture/strategy_admission_standard.md) and Phase 6 statistical doctrine. Data volume alone is meaningless without rigorous multiple-testing adjustments:
- **Effective Sample Size ($N_{\text{eff}}$):** Adjusting for serial correlation and volatility clustering.
- **Signal Count:** Independent trades/bets executed, not merely raw bar ticks.
- **Regime Diversity:** Performance evaluated across distinct macro and volatility environments.
- **Trial Census & Multiplicity Controls:** Accounting for all tested parameter variants via the Search Trial Ledger (`acash.validation.schema`).
- **Probability of Backtest Overfitting (PBO):** Combinatorially Symmetric Cross-Validation (CSCV).
- **Deflated Sharpe Ratio (DSR):** Correcting for sample variance, skewness, kurtosis, and candidate selection bias.
- **Minimum Track Record Length (MinTRL):** Calculating the minimum statistical history required to reject the null hypothesis of zero skill at a specified confidence level.
- **Slippage & Cost Drag:** Testing strategy survival under conservative fee and liquidity penalty models.

---

## 5. Research Discipline: Hypothesis-First vs. P-Hacking

ACASH explicitly prohibits data-mining exploration that fits indicators to noise:

$$\begin{aligned}
\textbf{PROHIBITED (P-Hacking):} &\quad \text{Generate 500 indicators} \to \text{Run automated grid search} \to \text{Select highest PnL} \\
\textbf{REQUIRED (Scientific):} &\quad \text{Market Mechanism} \to \text{Pre-Data Falsification Criteria} \to \text{Human-Authorized Hypothesis} \to \text{OOS Validation}
\end{aligned}$$

Every research trial must be registered in the canonical `SearchTrialLedger` to ensure the true multiplicity penalty $K$ is tracked by single authoritative cryptographic provenance.

---

## 6. Meaning of "4–10 Weeks / ~3 Months": Scoped to Paper-Ready Candidate

When development and research roadmaps cite "4–10 weeks" or "~3 months", this refers strictly to the **engineering and research sprint duration required to produce a credible Paper-Ready Candidate**.

### Definition of "Paper-Ready Candidate":
> **A Paper-Ready Candidate is a quantitative strategy candidate that has satisfied all pre-paper research gates (mechanistic hypothesis registration, in-sample calibration, out-of-sample statistical qualification, PBO/DSR hurdles, and cost sensitivity tests) such that it can be formally submitted to human governance for a separate paper-trading authorization decision.**

### What "Paper-Ready Candidate" Does NOT Mean:
- It does **NOT** mean paper trading has been authorized.
- It does **NOT** mean paper trading has been completed.
- It does **NOT** mean live trading is authorized.
- It does **NOT** guarantee profitability.
- It does **NOT** mean the system is production-ready.

### Estimated Delivery Scenarios (Planning Targets Only):
- **Best-Case Engineering Path ($\sim 4 - 6$ weeks):** Rapid completion of dataset qualification, hypothesis formulation, registered backtesting, and successful out-of-sample validation yielding a candidate for paper review.
- **Realistic Path ($\sim 6 - 10$ weeks):** Standard cycle incorporating data cleaning, regime-shift analysis, parameter stability audits, and cost-drag calibration before reaching a candidate review.
- **Conservative Path ($\sim 3$ months or more):** Extended iteration required when initial candidates fail falsification tests, data anomalies require remediation, or market regimes fail stationarity checks.

```text
================================================================================
                    CRITICAL ROADMAP DISTINCTION
- 4 TO 10 WEEKS IS THE TIME TO REACH A "PAPER-READY CANDIDATE" FOR HUMAN REVIEW.
- IT DOES NOT MEAN 4 TO 10 WEEKS OF PAPER TRADING IS SUFFICIENT.
- IT DOES NOT SHORTEN, REPLACE, OR BYPASS THE 90-DAY CONTINUOUS PAPER FORWARD RUN.
- IT DOES NOT PROMISE LIVE TRADING IN 90 DAYS.
================================================================================
```

---

## 7. The 90-Day ACASH Research Goal

The strategic 90-day objective for ACASH is framed as a scientific milestone, not a financial promise:

$$\boxed{\begin{aligned}
&\textbf{90-Day ACASH Research Objective:} \\
&\text{Transition from \textbf{validated infrastructure} (Gate G7)} \\
&\quad \to \text{Research-grade multi-asset data foundation} \\
&\quad \to \text{Reproducible, hypothesis-governed empirical research pipeline} \\
&\quad \to \text{Governed statistical validation under strict multiplicity controls} \\
&\quad \to \text{One or more credible candidates evaluated for paper-ready submission}
\end{aligned}}$$

### Essential Scientific Principle:
> **Failure to identify an admitted strategy candidate within 90 days is a completely valid and acceptable scientific outcome.**

ACASH will never force an unproven candidate into paper trading simply to meet an arbitrary calendar deadline. The discovery that a proposed market inefficiency has decayed or does not survive transaction costs is an institutional success that prevents live capital destruction.

---

## 8. Preservation of Phase 13 Step 9: 90-Day Continuous Paper Forward Run

[`docs/ROADMAP.md`](../ROADMAP.md) establishes the canonical lifecycle for trading authorization. Under Phase 13:
- **Phase 13 Step 8:** `Human GO (Executive Ratification)` — **LOCKED**
- **Phase 13 Step 9:** `90-Day Continuous Paper Forward Run` — **LOCKED / NOT AUTHORIZED**

### Sequential Relationship:
The research timeline and the paper execution timeline are strictly sequential, not concurrent or interchangeable:

```text
[ Phase 14 Research & Discovery ] (~4–10 Weeks)
              ↓
Produces: Qualified "Paper-Ready Candidate"
              ↓
[ Formal Human Review & Step 8 Ratification ]
              ↓
[ Phase 13 Step 9: 90-Day Continuous Paper Forward Run ] (Full 90 Calendar Days)
              ↓
Must run for 90 continuous days without restart/drift
              ↓
[ Live Capital Consideration Gate ] (Phase 13 Step 10 / Phase 17)
```

The 90-day continuous paper run requires forward out-of-sample execution in real calendar time to prove live telemetry, order reconciliation, fill simulation, and operational resilience. **It cannot be compressed by historical backtesting.**

---

## 9. Cross-Asset Research Scope (Non-Approved Universes)

In accordance with [`docs/architecture/asset_market_agnostic_research_direction.md`](../architecture/asset_market_agnostic_research_direction.md), future research directions may explore multiple liquid electronic markets:
- **Crypto:** BTC, ETH
- **Equity Index Futures:** ES (E-mini S&P 500)
- **Foreign Exchange:** EURUSD, USDJPY
- **Metals & Commodities:** XAU (Gold), WTI Crude
- **Equities & ETFs:** S&P 500 components, SPY, QQQ
- **Sovereign Rates:** US 10-Year Treasury yield proxies

**Governance Boundary:** These markets represent candidate research universes only. None of these instruments are approved as an active trading universe, and no market-data adapter authorizes strategy deployment.

---

## 10. Binding Legal & Governance Statement

This document records research execution and timing clarification only.

It does not create a trading hypothesis.  
It does not authorize backtesting.  
It does not authorize paper trading.  
It does not authorize live trading.  
It does not change canonical capital.  
It does not modify G7/S11 acceptance criteria.  
All implementation and governance transitions require separate explicit human authorization.  
