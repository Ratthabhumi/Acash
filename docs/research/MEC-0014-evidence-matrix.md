# MEC-0014: Authoritative Literature Evidence Matrix

```text
[GOVERNANCE ARTIFACT: EVIDENCE SYNTHESIS]
[INTENDED MECHANISM: MEC-0014 MARKET INTRADAY MOMENTUM]
[ZERO EMPIRICAL STRATEGY EXECUTION]
```

- **Document ID:** `docs/research/MEC-0014-evidence-matrix.md`
- **Target Mechanism:** `MEC-0014`
- **Date:** 2026-09-19
- **Governing Standard:** AGENTS.md (Evidence Lineage & Zero Unverified Claims)

---

## 1. Evidence Quality Tier Taxonomy

Evidence is classified into four objective methodological quality tiers:

| Tier | Definition | Standard of Acceptance | Included Sources |
| :---: | :--- | :--- | :--- |
| **Tier A** | Top-tier peer-reviewed journal articles establishing foundational theoretical and empirical relationships on target or directly adjacent asset classes. | Published in *JFE*, *JF*, or *RFS*; reproducible empirical methods; clear institutional economic mechanisms. | Gao et al. (2018, *JFE*); Baltussen et al. (2021, *JFE*) |
| **Tier B** | Peer-reviewed independent replication studies, cross-market empirical tests, and peer-reviewed related counterevidence. | Published in established peer-reviewed finance journals; independent author teams replicating original specifications or establishing interval-specific properties. | Limkriangkrai, Chai, Zheng (2023, *PBFJ*); Iwanaga & Sakemoto (2026, *NAJEF*) |
| **Tier C** | Recent working papers, SSRN preprints, and institutional whitepapers addressing contemporary market structure, frictions, or related interval anomalies. | Methodologically rigorous; large sample sizes; explicit cost models; serves as contextual evidence or counterpoints. | Fetna (2026, *SSRN*); Zarattini et al. (2024/2025, *SFI*) |
| **Tier D** | Older working papers or specialized university working papers providing regime-conditioning or auxiliary conceptual evidence. | Informative for hypothesis conditioning; not authoritative for baseline primary specification. | Lundström (2017, *Umeå*) |

> [!NOTE]
> Tiering indicates **methodological strength, peer review rigor, and direct relevance**. It is **not** a ranking of expected trading profitability.

---

## 2. Comprehensive Literature Evidence Matrix

| Source Key | Quality Tier | Authors & Citation | Universe & Sample Period | Core Empirical Finding | Quantitative Metrics Reported | Identified Economic Mechanism | ACASH Implementation Seams & Risks | Evidence Tag |
| :--- | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **SRC-A** | **Tier A** | Gao, Lei; Han, Yufeng; Li, Sophia Zhengzi; Zhou, Guofu (2018), *Journal of Financial Economics*, Vol. 129, Iss. 2 (August 2018), pp. 394–414 | US S&P 500 ETF (`SPY`), 1993–2013 (21 years, TAQ) | First half-hour return ($r_1$, incl. overnight) positively predicts last half-hour return ($r_{13}$). | $R^2_{IS} \approx 1.60\%$, $t > 3.0$; $R^2_{OOS} \approx 1.40\%$; joint with $r_{12}$: $R^2_{OOS} \approx 2.00\%$; reports positive economic value for $\text{sign}(r_1)$ market-timing rule. | Infrequent institutional portfolio rebalancing; late-informed trading near market close. | Requires prior day 16:00 close print (not in current HYP_003 15:59 dataset). Literature contains both predictive regression and a market-timing strategy translation, but ACASH has not yet audited whether original execution/friction assumptions map cleanly to contemporary Alpaca SIP data. | `EVIDENCE` / `MECHANISM` |
| **SRC-B** | **Tier B** | Limkriangkrai, Chai, Zheng (2023), *Pacific-Basin Finance Journal* | US SPY (1996–2013) + APAC equity ETFs (2000–2018) | Independently confirmed US Gao finding. Found intraday momentum is **heterogeneous** across APAC (strong in China/Japan, zero in Hong Kong/Singapore). | US Rep: $R^2_{IS} \approx 1.70\%$, $R^2_{OOS} \approx 1.70\%$; joint: $R^2_{IS} \approx 2.60\%$, $R^2_{OOS} \approx 2.30\%$ | Local institutional market structure; depth of closing auctions; presence of index rebalancing flows. | The APAC evidence demonstrates material cross-market heterogeneity. China and Japan exhibit stronger evidence, South Korea weaker, and HK/Singapore show no comparable momentum. Market-structure differences are candidate explanations, not established causal facts. | `REPLICATION` / `LIMITATION` |
| **SRC-C** | **Tier A** | Baltussen, Da, Lammers, Martens (2021), *Journal of Financial Economics* | 60+ global futures (Equities, Bonds, Commodities, FX), 1974–2020 | Final 30-min return is positively predicted by cumulative rest-of-day return across all asset classes. | Highly significant across 60+ futures; documented subsequent overnight reversal. | Short-gamma delta hedging by option market makers; mechanical rebalancing of leveraged/inverse ETFs. | ACASH lacks authoritative daily options open interest / GEX feeds. Mechanism is supportive context, not an empirical input. | `EVIDENCE` / `MECHANISM` |
| **SRC-D** | **Tier B** | Iwanaga & Sakemoto (2026), *North American Journal of Economics and Finance*, Vol. 86, Art. 102707 | US Index ETFs (SPY, QQQ, IWM), 2000–2024 (SSRN 5807282 lineage) | Overnight return negatively predicts first half-hour return (09:30 $\to$ 10:00 ET). Reversal weakened after 2010s. | Significant negative slope for overnight $\to$ open; structural decay in recent decade. | Morning retail/sentiment liquidity demand reverses; market makers fade overnight order imbalances. | Peer-reviewed related counterevidence demonstrating that morning and afternoon intervals have opposing directional signatures. Caution regarding post-2015 decay. Not direct replication of Gao. | `COUNTERPOINT` / `LIMITATION` |
| **SRC-E** | **Tier C** | Fetna, Mulham (2026), *SSRN Working Paper 7428398* | 9 US liquid futures, 2010–2026, 1-minute data (16 years) | Pre-registered 225-cell study on Opening Range Breakout (ORB). **Zero of 225 cells survived realistic trading costs.** | 0/225 passed; gross alpha eliminated by fees; 5m OR window performed worst; random anchor matched 09:30. | Fast intraday stops create extreme turnover; microstructure friction consumes edge. | External confirmation that naive price-only ORB is non-viable. Validates ACASH decision to retire `HYP_003` without post-hoc tuning. Contextual external ORB falsification / anti-overfitting evidence; not direct evidence for market intraday momentum; not auction-mechanism evidence. | `EXTERNAL ORB FALSIFICATION / ANTI-OVERFITTING CONTEXT` |
| **SRC-F** | **Tier C** | Zarattini, Barbon, Aziz (2024/2025), *Swiss Finance Institute 24-98* | 7,000+ US single stocks, 2016–2023 | 5-minute ORB only generates positive risk-adjusted returns when conditioned on extreme volume ("Stocks in Play"). | Positive Sharpe achieved only with top volume-ratio and news catalysts. | Idiosyncratic fundamental information arrival creates genuine intraday drift in individual stocks. | Cross-sectional single-stock phenomenon; does not apply to broad macro index ETF (`SPY`). Quarantined as MEC-0015+. | `UNRESOLVED` / `PROPOSAL` |
| **SRC-G** | **Tier D** | Lundström (2017), *Umeå Economic Studies No. 861* | S&P 500 and Crude Oil futures | Breakout returns vary substantially across implied/realized volatility regimes. | Documented regime dependency of intraday momentum/breakout returns. | High-volatility states provide sufficient amplitude to overcome fixed transaction costs. | Requires ex-ante regime definition. Secondary conditioning idea; quarantined from primary replication. | `INFERENCE` / `PROPOSAL` |

---

## 3. Epistemic Synthesis & Research Invariants

### 3.1 What the Literature Authoritatively Establishes:
1. **Empirical Fact:** Between 1993 and 2013, a statistically significant positive linear relationship existed between the early-session SPY return (including overnight) and the final 30-minute SPY return.
2. **Replication Fact:** Independent researchers (Limkriangkrai et al., 2023) replicated this statistical relationship on US data with nearly identical explanatory power ($R^2 \approx 1.7\%$).
3. **Microstructural Grounding:** Institutional order execution (market-on-close rebalancing, geared ETF mechanical hedging, options delta adjustment) concentrates in the final half-hour, providing a plausible non-behavioral economic engine.

### 3.2 What the Literature Does NOT Establish for ACASH:
1. **Tradability Under Contemporary ACASH Execution:** While Gao et al. present a stylized market-timing translation based on $\text{sign}(r_1)$, the literature has not demonstrated that the strategy survives ACASH's institutional friction contract (1.6 bps commission + 1.0 bps adverse slippage) in modern electronic markets.
2. **Execution Mapping:** ACASH has not yet audited whether the original execution, spread, cost, auction, and slippage assumptions map cleanly to the current Alpaca SIP contract.
3. **Modern Market Structure:** Foundational datasets (ending 2013 and 2020) predate recent market-structure developments, including same-day expiring options and shifting closing auction participation.
