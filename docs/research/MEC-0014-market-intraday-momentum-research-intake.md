# Research Intake — Mechanism Family MEC-0014: Market Intraday Momentum

```text
[RESEARCH INTAKE / KNOWLEDGE SYNTHESIS ONLY]
[GOVERNANCE STATE: CANDIDATE MECHANISM INTAKE]
[HYP_004: NOT CREATED / NOT AUTHORIZED]
[RESEARCH RE-INCEPTION GATE: NOT INVOKED]
[MARKET DATA: ZERO LOADED / ZERO QUERIED]
[BACKTESTING: STRICTLY LOCKED]
[CAPITAL AUTHORITY: $0.00 / NO_REAL_ORDERS=true]
[RESEARCH READINESS VERDICT: YELLOW]
```

- **Document ID:** `docs/research/MEC-0014-market-intraday-momentum-research-intake.md`
- **Mechanism ID:** `MEC-0014`
- **Mechanism Name:** Market Intraday Momentum (Late-Day Following Early-Day Trend)
- **Target Asset / Universe:** US Equity Market Index (`SPY` ETF / S&P 500)
- **Document Version:** 1.0 (Post-HYP_003 Literature Intake)
- **Date:** 2026-09-19
- **Governing Standard:** ACASH Quantitative Research & Verification Operating System (AGENTS.md)
- **Authoritative Predecessor Status:** `HYP_003` (MEC-0013 Price-Only ORB) is permanently `TERMINALLY_FALSIFIED_REJECTED` and sealed.

---

## 1. Executive Summary & Purpose

This document establishes a formal, literature-grounded research intake for candidate mechanism family **MEC-0014 (Market Intraday Momentum)**.

Following the terminal empirical falsification of `HYP_003` (naive price-only Opening Range Breakout on SPY), ACASH governance mandates that new hypothesis candidates must **originate from rigorous external academic literature**, rather than from post-hoc curve-fitting or parameter mining of historical ACASH backtest runs.

> [!IMPORTANT]
> **Strict Non-Authorization Boundary:**
> This intake is an evidence evaluation and architectural scoping document only. It does **NOT** create `HYP_004`, does **NOT** invoke `ResearchReInceptionGate`, does **NOT** authorize any historical market data loading or querying, does **NOT** calculate any statistical returns, and does **NOT** authorize backtesting or capital allocation.

---

## 2. Distinction from MEC-0013 (Opening Range Breakout)

MEC-0014 represents a distinct economic mechanism from MEC-0013:

| Dimension | MEC-0013 (HYP_003 — Disconfirmed) | MEC-0014 (Market Intraday Momentum — Proposed Intake) |
| :--- | :--- | :--- |
| **Core Economic Theory** | Volatility breakout / local intraday liquidity hole resolution | Inventory rebalancing, late-informed trading, and derivative hedging flows |
| **Predictor Interval** | Local opening range (09:30–09:34 or 09:30–09:44 ET) | Full early session + overnight ($r_1$: Prior close 16:00 through 10:00 ET) |
| **Holding Horizon** | Path-dependent intraday trailing / opposite-boundary stop / 15:59 exit | Bounded terminal half-hour interval ($r_{13}$: 15:30 through 16:00 ET) |
| **Execution Style** | Fast stop-out trading with 50%+ turnover stops | Fixed-interval time-series predictive positioning |
| **Literature Origin** | Practitioner folklore / heuristic breakout models | Peer-reviewed academic finance (Gao et al. 2018 JFE; Baltussen et al. 2021 JFE) |

---

## 3. Literature Foundation (Source A: Primary Baseline)

### Gao, Lei; Han, Yufeng; Li, Sophia Zhengzi; Zhou, Guofu (2018)
- **Title:** "Market Intraday Momentum"
- **Journal:** *Journal of Financial Economics*, Volume 129, Issue 2, August 2018, Pages 394–414.
- **DOI:** [10.1016/j.jfineco.2018.05.009](https://doi.org/10.1016/j.jfineco.2018.05.009)
- **Data Examined:** Trade and Quote (TAQ) high-frequency data for the S&P 500 index ETF (`SPY`) from 1993 through 2013 (21 years).

#### Core Findings:
1. **First-to-Last Half-Hour Predictability:** The market return during the first half-hour of trading ($r_1$) positively and statistically significantly predicts the market return during the final half-hour of the trading day ($r_{13}$).
2. **Exact Published Timing Semantics:**
   - $r_1$: Return from previous trading day's market close (16:00 ET) through 10:00 ET on day $t$. **CRITICAL:** $r_1$ explicitly incorporates overnight return from the previous regular-session close; it is *not* merely 09:30 $\to$ 10:00 ET.
   - $r_{12}$: Return from 15:00 ET through 15:30 ET on day $t$.
   - $r_{13}$: Return from 15:30 ET through 16:00 ET on day $t$.
3. **Predictive Explanatory Power:**
   - In-sample regression $R^2 \approx 1.6\%$ for $r_1$-only specification ($t$-statistic $> 3.0$).
   - Out-of-sample Campbell-Thompson $R^2_{OOS} \approx 1.4\%$ for $r_1$-only, and $\approx 2.0\%$ when combining $r_1 + r_{12}$.
4. **Reported Cross-Sectional & Regime Variations:**
   - Intraday momentum is significantly stronger on high-volatility days (top VIX quintiles).
   - Stronger on high-volume days, NBER recession months, and major macroeconomic news announcement days (FOMC, CPI, Employment Situation).
5. **Proposed Economic Rationale:**
   - **Infrequent Portfolio Rebalancing:** Institutional asset allocators, mutual funds, and pension managers aggregate net inflow/outflow orders and execute rebalancing trades concentrated in the final half-hour to minimize market impact and benchmark against the official closing print.
   - **Late-Informed Trading:** Institutional traders possessing private information or analyzing morning macro signals postpone directional execution until late afternoon to exploit peak market depth and closing liquidity.

---

## 4. Independent Replication Evidence (Source B)

### Limkriangkrai, Manapon; Chai, Daniel; Zheng, Gaoping (2023)
- **Title:** "Market intraday momentum: APAC evidence"
- **Journal:** *Pacific-Basin Finance Journal*, Vol. 80, Article 102086.
- **DOI:** [10.1016/j.pacfin.2023.102086](https://doi.org/10.1016/j.pacfin.2023.102086)

#### Independent US Replication:
- Authors replicated the exact Gao et al. setup on SPY from January 1996 through December 2013 using 30-minute intervals.
- **US Results:**
  - $r_1 \to r_{13}$ in-sample $R^2 \approx 1.7\%$ ($t$-statistic 3.65).
  - Out-of-sample $R^2_{OOS} \approx 1.7\%$ for $r_1$-only.
  - Joint specification ($r_1 + r_{12}$) achieved in-sample $R^2 \approx 2.6\%$, $R^2_{OOS} \approx 2.3\%$.
- **Conclusion:** Independent academic replication verified the empirical existence and statistical robustness of the US SPY market intraday momentum effect over the historical sample.

#### Cross-Market Heterogeneity (Critical Governance Finding):
- The APAC evidence demonstrates material cross-market heterogeneity. China and Japan exhibit stronger evidence, South Korea weaker evidence, and Hong Kong/Singapore do not exhibit comparable intraday momentum.
- Market-structure differences may be candidate explanations, but no single closing-auction mechanism is treated here as an established causal fact.

---

## 5. Mechanism & Cross-Asset Evidence (Source C)

### Baltussen, Guido; Da, Zhi; Lammers, Sten; Martens, Martin (2021)
- **Title:** "Hedging Demand and Market Intraday Momentum"
- **Journal:** *Journal of Financial Economics*, Vol. 142, Iss. 1, pp. 377–403.
- **DOI:** [10.1016/j.jfineco.2021.04.029](https://doi.org/10.1016/j.jfineco.2021.04.029)

#### Findings:
1. **Cross-Asset Scope:** Evaluated over 60 futures contracts spanning equities, government bonds, commodities, and currencies over 1974–2020.
2. **Core Relation:** The final 30-minute return of the trading day is positively predicted by the cumulative return of the "rest of the day" (from previous market close to 30 minutes prior to close).
3. **Identified Economic Mechanism (Gamma Hedging & Rebalancing):**
   - **Options Market Maker Delta Hedging:** Structured products, retail call buying, and institutional option selling frequently leave market makers structurally short gamma. As underlying index prices rise during the day, market makers must buy underlying delta into the close; as prices fall, they must sell delta.
   - **Leveraged and Inverse ETF Rebalancing:** Geared ETFs (e.g., $2\times$, $3\times$) are mechanically mandated to rebalance their leverage profiles at the end of every trading session. On up days, they must purchase additional exposure at the close; on down days, they must sell exposure.
4. **Subsequent Reversal:** The authors report that the late-day momentum partially reverses over overnight and multi-day horizons, consistent with liquidity-demand price pressure rather than permanent information assimilation.

> [!WARNING]
> **Data Authority Boundary:** While Baltussen et al. provide compelling microstructural rationale, ACASH does *not* possess authoritative Options Clearing Corporation (OCC) open-interest or daily GEX (Gamma Exposure) data feeds. Gamma hedging must remain an **untested explanatory hypothesis**, not an empirical conditioning input for primary replication.

---

## 6. Counterevidence & Intraday Interval Sign Reversal (Source D)

### Iwanaga, Yasuhiro; Sakemoto, Ryuta (2026)
- **Title:** "Does overnight return predict the first half-hour return for U.S. market indices?"
- **Journal:** *North American Journal of Economics and Finance*, Vol. 86, September 2026, Article 102707.
- **DOI:** [10.1016/j.najef.2026.102707](https://doi.org/10.1016/j.najef.2026.102707)
- **Working Paper Lineage:** SSRN Abstract ID 5807282.
- **Evidence Classification:** **Tier B — Recent Peer-Reviewed Related / Counterevidence** (not direct replication of Gao et al.).

#### Findings:
1. High overnight returns negatively predict the first half-hour return (09:30 $\to$ 10:00 ET) for US market indices (overnight reversal).
2. The reversal effect was prominent during high-volatility periods but exhibited structural weakening after the 2010s.
3. **Relevance to MEC-0014:** Illustrates that different intraday intervals exhibit different directional dependencies. While the morning open often exhibits mean-reversion of overnight retail/sentiment noise, the afternoon close exhibits continuation of accumulated daily institutional flow.

---

## 7. Contextual ORB Falsification Literature (Sources E, F, G)

### 7.1 Fetna, Mulham (September 2026, SSRN 7428398)
- **Title:** "Opening-Range Breakout Does Not Survive Trading Costs: A Pre-Registered 225-Cell Study on Sixteen Years of Futures Data"
- **Classification:** **Recent Pre-Registered ORB Falsification / Transaction-Cost Robustness Evidence**
- **Functional Role in MEC-0014:** `EXTERNAL ORB FALSIFICATION / ANTI-OVERFITTING CONTEXT` (strictly contextual; *not* direct evidence for market intraday momentum; *not* auction-mechanism evidence).
- **Evidence Scope:**
  - Pre-registered 225-cell study on 9 liquid US futures (2010–2026, 1-minute data).
  - Explicit realistic trading costs and commissions.
  - **Zero of 225 cells met the preregistered positive bar.** Gross alpha was eliminated by fees.
  - 5-minute opening range window performed worst.
  - Random-anchor control challenged session-open uniqueness (09:30 possessed no unique breakout edge over arbitrary times).
- **ACASH Relevance:** Independently confirms the validity of ACASH's terminal falsification of `HYP_003` and provides peer evidence against attempting post-hoc ORB parameter tuning.

### 7.2 Zarattini, Barbon, Aziz (2024/2025, SSRN 4729284) & Lundström (2017)
- Show that ORB only exhibits residual profitability when conditioned on extreme company-specific catalyst volume ("Stocks in Play") or extreme volatility regimes.
- **Classification:** Categorized as **MEC-0015+ (Separate Future Mechanism Families)**. They cannot be used to rescue simple index-level breakout strategies.

---

## 8. Exact Published Timing Definitions

To avoid semantic drift, MEC-0014 adopts the canonical mathematical intervals of Gao et al. (2018):

```text
Session t - 1                          Session t
[16:00 Close] ---------- Overnight ---------- [09:30 Open] === [10:00 ET] ........... [15:30 ET] === [16:00 Close]
      |                                              |              |                      |                |
      +--------------------- r1 ---------------------+--------------+                      +------ r13 -----+
                                                                                           (Target Window)
```

$$\begin{aligned}
r_{1,t} &\equiv \ln\left(\frac{P_{10:00, t}}{P_{16:00, t-1}}\right) \quad \text{(Predictor 1: Previous Close through 10:00 ET)} \\
r_{12,t} &\equiv \ln\left(\frac{P_{15:30, t}}{P_{15:00, t}}\right) \quad \text{(Predictor 2: Twelfth Half-Hour, Optional)} \\
r_{13,t} &\equiv \ln\left(\frac{P_{16:00, t}}{P_{15:30, t}}\right) \quad \text{(Target: Thirteenth Half-Hour, 15:30 to 16:00 ET)}
\end{aligned}$$

---

## 9. Critical Distinction: Statistical Predictability vs. Tradable Edge

The source literature (Gao et al. 2018) contains **both**:
1. **Predictive Regressions:** Continuous linear specification ($r_{13,t} = \alpha + \beta r_{1,t} + \epsilon_t$) establishing statistical association ($R^2 \approx 1.6\%$, $t > 3.0$);
2. **Explicit Market-Timing Strategy Translation:** A directional rule based on the sign of $r_1$:
   - If $r_{1,t} > 0 \implies \text{Long final half-hour } (15:30 \to 16:00)$;
   - If $r_{1,t} < 0 \implies \text{Short final half-hour } (15:30 \to 16:00)$;
   - Gao et al. report economic value metrics for this stylized market-timing strategy.

However, the literature contains both predictive-regression evidence and an explicit market-timing translation. **ACASH has not yet audited whether the original execution, spread, cost, auction, and slippage assumptions map cleanly to the current Alpaca SIP data contract and contemporary execution environment.**

$$\text{Status: } \mathbf{EXECUTION\_MAPPING = PARTIALLY\_RESOLVED\ /\ ACASH\ CONTRACT\ OPEN}$$

---

## 10. Data Requirements & ACASH Infrastructure Audit

### 10.1 What ACASH Already Possesses:
- Consolidated SIP 1-minute historical bars for SPY covering In-Sample 2017–2022 (581,880 regular-session bars, $1,492 \times 390$ minutes).
- NYSE CA-1 trading calendar authority (defining 09:30–16:00 regular sessions, early closes, holidays).

### 10.2 What ACASH Does NOT Authoritatively Possess / Data Seams:
1. **Previous-Day Regular Close ($P_{16:00, t-1}$):**
   - The Step R2 canonical dataset (`HYP_003_SPY_1Min_IS_canonical.parquet`) spans 09:30:00 through 15:59:00 ET (closing bar 15:59).
   - In regular equity trading, the 16:00 NYSE closing auction cross print often diverges from the 15:59 continuous-trading bar close by 1–5 basis points.
   - **MANDATE:** The 15:59 minute close **MUST NOT** be treated as exact previous official close.
   - **Provider Discovery:** Alpaca provides dedicated historical stock auction endpoints (`/v2/stocks/{symbol}/auctions` and `/v2/stocks/auctions`) that provide historical auction prices for stocks. Alpaca documentation also explicitly distinguishes minute-bar close, daily-bar close, and market-center closing/auction trades, noting that the official daily close can differ from the final continuous minute bar.
   - **Resolution State:** $\mathbf{PREVIOUS\_CLOSE\_AUTHORITY = PROVISIONALLY\_RESOLVABLE\_PENDING\_CONTRACT\_TEST}$.
   - **Preferred Authority Candidate:** Alpaca historical closing-auction / official-close record under SIP semantics.
   - **Fallback Candidate:** Alpaca SIP daily bar close. Equivalence between auction cross price and daily close must be verified empirically and contractually before HYP_004 pre-registration.
   - **Future Contract Test Requirement:** A small authorized historical sample must retrieve auction closes vs. SIP daily bar closes, inspect closing trade condition semantics, and compare exact differences. No market data is fetched in this intake.
2. **16:00 Closing Auction Print for $r_{13}$ Target:**
   - Target return requires an unambiguous definition: Does $P_{16:00}$ represent the 15:59:00 bar close, the 16:00:00 closing minute bar, or the official NYSE closing auction cross?

---

## 11. Lookahead & Non-Anticipation Invariants

Any future empirical implementation must enforce strict time-stamped information boundaries:

$$\mathcal{I}_{15:29:59} \equiv \sigma\left(\{P_\tau : \tau \le 15:29:59\}\right)$$

- The predictor $r_{1,t}$ is fully determined at 10:00:00 ET ($t_0 + 30\text{m}$).
- If optional predictor $r_{12,t}$ is used, it is determined at 15:29:59 ET.
- Entry execution at 15:30:00 ET must be evaluated at the opening price of the 15:30 bar, **never** at the 15:30 close.
- Target return $r_{13,t}$ must strictly commence *after* position establishment.

---

## 12. Contemporary Decay & Market Structure Risks

The primary literature sample (Gao et al.: 1993–2013; Baltussen et al.: 1974–2020) largely predates major structural shifts:
1. **Evolution of Options-Market Structure & Same-Day Expiring Contracts:**
   - Options-market structure has evolved materially since 2013.
   - Same-day expiring contract (0DTE) activity represents a contemporary mechanism-risk candidate that may disperse or alter intraday gamma hedging flows across the day rather than concentrating them solely at 15:30.
   - *Classification:* `RESEARCH QUESTION / UNVERIFIED IN THIS INTAKE`.
2. **Closing-Auction Market Share Dynamics:**
   - Closing-auction participation and closing cross volumes on primary exchanges have changed substantially over time.
   - Greater concentration of volume into official closing auctions affects continuous-trading liquidity dynamics between 15:30 and 15:59.
   - *Classification:* `RESEARCH QUESTION / UNVERIFIED IN THIS INTAKE`.
3. **Algorithmic Crowding & Arbitrage:**
   - Post-publication diffusion of Gao et al. (2018) may have compressed the gross premium in modern markets.

---

## 13. Data Contamination & Partition Governance

To maintain integrity before proposing date partitions for any hypothetical HYP_004:

```text
+-------------------------------------------------------------------------------+
| HISTORICAL SPY DATA INVENTORY CLASSIFICATION                                  |
+-------------------------------------------------------------------------------+
| Partition 1: 2017-01-01 to 2022-12-31                                        |
|   - Status: Consumed as In-Sample in HYP_003 (ORB).                           |
|   - Contamination Assessment: Evaluated for breakout mechanics; NOT evaluated |
|     for market intraday momentum (10:00 -> 15:30).                            |
+-------------------------------------------------------------------------------+
| Partition 2: Isolated Dates in 2023                                          |
|   - Status: Touched during technical infrastructure probes (data pipeline).    |
|   - Contamination Assessment: Technical format checks; no strategy evaluation.|
+-------------------------------------------------------------------------------+
| Partition 3: 2023-01-01 to 2026-12-31 (Holdout)                              |
|   - Status: CERTIFIED UNEXPOSED_PRISTINE under HYP_003 terminal dossier.     |
|   - Preservation Mandate: Must remain strictly sealed until explicit Human    |
|     governance authorization approves holdout evaluation.                     |
+-------------------------------------------------------------------------------+
```

---

## 14. Primary Research Architecture (Recommended Sequencing)

Rather than jumping directly to an unverified trading strategy, the recommended research sequencing separates statistical replication from discrete execution:

```text
================================================================================
PRIMARY RESEARCH SEQUENCING ARCHITECTURE
================================================================================
MEC-0014A: Exact Predictive-Relation Econometric Replication
           - Model: r13(t) = alpha + beta * r1(t) + epsilon(t)
           - Estimator: OLS with Newey-West (1987) HAC standard errors
           - Benchmark: Campbell-Thompson (2008) Out-of-Sample R^2

MEC-0014B: Exact Literature Market-Timing Strategy Replication
           - Signal: sign(r1(t)) -> Long / Short final half-hour (15:30 -> 16:00)
           - Performance: Gross Sharpe, net Sharpe under ACASH friction model
================================================================================
```

Only after both contracts are understood should the Human Operator decide whether `HYP_004` should bind to:
1. Statistical replication,
2. Trading replication, or
3. A separate pair of hypotheses.

---

## 15. Quarantined Secondary Research Directions

The following concepts must **NOT** enter any primary replication specification:
1. **$r_{12}$ (15:00–15:30) Predictor Addition:** Quarantined as secondary model specification.
2. **High-Volatility (VIX) Conditioning:** Quarantined until baseline unconditional relation is measured.
3. **Volume-Expansion Filters:** Quarantined to prevent parameter optimization.
4. **Macroeconomic News Calendars (FOMC/CPI/NFP):** Quarantined as secondary regime analysis.
5. **Options Gamma / GEX Indicators:** Quarantined due to lack of authoritative historical data contract.
6. **Overnight Reversal Mechanisms (Iwanaga & Sakemoto):** Quarantined as a distinct morning phenomenon.
7. **Conditioned Stock Selection ("Stocks in Play"):** Quarantined to future cross-sectional equity mechanisms (MEC-0015+).

---

## 16. Research Readiness Verdict: **YELLOW**

```markdown
### Readiness Verdict: YELLOW (PROMISING BUT PENDING DATA/GOVERNANCE AUTHORITIES)
- Literature Strength: TIER A (Peer-reviewed in JFE 2018, JFE 2021; replicated in PBFJ 2023).
- Theoretical Grounding: STRONG (Institutional rebalancing, late-informed trading, gamma hedging).
- Empirical Clarity: HIGH (Exact published 30-minute intervals).
- Fatal Blockers Before HYP_004 Can Be Incepted:
  1. Previous-close / auction data contract test (Alpaca /v2/stocks/auctions vs. daily bar).
  2. Exact 15:30-to-close execution and target return semantics.
  3. Replication-vs-trading hypothesis architecture (MEC-0014A vs. MEC-0014B).
  4. HYP_004 partition policy (preserving pristine 2023-2026 holdout).
  5. Explicit Human pre-registration decision.
  6. Formal invocation of ResearchReInceptionGate after all above are resolved.
```

---

## 17. Authoritative References

1. **Gao, Lei; Han, Yufeng; Li, Sophia Zhengzi; Zhou, Guofu (2018).** Market intraday momentum. *Journal of Financial Economics*, Volume 129, Issue 2, August 2018, Pages 394–414. DOI: [10.1016/j.jfineco.2018.05.009](https://doi.org/10.1016/j.jfineco.2018.05.009)
2. **Limkriangkrai, M., Chai, D., & Zheng, G. (2023).** Market intraday momentum: APAC evidence. *Pacific-Basin Finance Journal*, 80, 102086. DOI: [10.1016/j.pacfin.2023.102086](https://doi.org/10.1016/j.pacfin.2023.102086)
3. **Baltussen, G., Da, Z., Lammers, S., & Martens, M. (2021).** Hedging Demand and Market Intraday Momentum. *Journal of Financial Economics*, 142(1), 377–403. DOI: [10.1016/j.jfineco.2021.04.029](https://doi.org/10.1016/j.jfineco.2021.04.029)
4. **Iwanaga, Y., & Sakemoto, R. (2026).** Does overnight return predict the first half-hour return for U.S. market indices? *North American Journal of Economics and Finance*, 86, 102707. DOI: [10.1016/j.najef.2026.102707](https://doi.org/10.1016/j.najef.2026.102707) (SSRN Abstract ID 5807282).
5. **Fetna, M. (2026).** Opening-Range Breakout Does Not Survive Trading Costs: A Pre-Registered 225-Cell Study on Sixteen Years of Futures Data. *SSRN Working Paper*, Abstract ID 7428398. DOI: [10.2139/ssrn.7428398](https://doi.org/10.2139/ssrn.7428398)
6. **Zarattini, C., Barbon, A., & Aziz, A. (2024/2025).** A Profitable Day Trading Strategy For The U.S. Equity Market. *Swiss Finance Institute Research Paper No. 24-98*. SSRN Abstract ID 4729284.
7. **Lundström, C. (2017).** Day trading returns across volatility states. *Umeå Economic Studies No. 861*.
8. **Alpaca Markets (2026).** Market Data API v2 Documentation: Historical Stock Auctions Endpoint (`/v2/stocks/{symbol}/auctions`) & Market Data FAQ (Daily vs. Minute Close Semantics).
