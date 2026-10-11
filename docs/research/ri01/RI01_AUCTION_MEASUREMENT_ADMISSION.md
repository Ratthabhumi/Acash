# RI-01 Auction & Point-in-Time Measurement Admission Specification

**Document ID:** `DOC-RI01-AUCTION-MEASUREMENT-ADMISSION-20261011`  
**Classification:** Quantitative Market Data & Evidence Specification (Pre-Execution / Research Only)  
**Lineage Target:** Follows successful completion of RI-01 Canary 1 (2021-06-01), Canary 2 (2018-06-01), and MEC-0014 Evidence Reconciliation  
**Runtime Boundary:** Read-Only Design / Zero-Outcome / Zero-Order / Zero New Provider HTTP  
**Historical Governance Context:** Incorporates MEC-0014 Coverage Census (1,498 sessions) and Phase 14 HYP_004 Terminal Closure Dossier  

---

## 1. Executive Summary & Measurement Reconciliation

Canary 1 (2021-06-01) and Canary 2 (2018-06-01) empirically proved that the current Alpaca SIP subscription and ACASH infrastructure retrieve raw historical 1-minute SIP bars across two distinct market regimes with 100% NYSE Regular Trading Hours (RTH) completeness (390/390 qualified bars per session) within a strict 1-invocation budget.

Following the independent disk audit of preserved historical research artifacts, **MEC-0014 already provides full empirical proof of Alpaca Historical Auctions availability**:
1. **Raw Evidence Provenance:** `data/raw/research/MEC_0014/close_contract/` contains verified raw auction payloads for all 6 probed sessions (2017–2022). Cryptographic SHA-256 matches manifest `099b6a0b9c7f70a7deb951d803a7ce6e5351ef953f5d33da8f15b7a547590a62` bit-for-bit.
2. **Multi-Year Census:** `data/raw/research/MEC_0014/coverage_census/` preserves 1,498 regular sessions (2017–2022) with 100% closing auction coverage and 1,497/1,498 opening auction coverage on NYSE Arca (`x=P`).
3. **Auction Canary A1 Verdict:** **`NEW_HTTP_NOT_NEEDED`**. Acquiring 2018-06-01 auctions via a new HTTP request is redundant and yields zero new scientific knowledge.

---

## 2. Measurement Taxonomy & Empirical Findings

ACASH strictly separates four distinct market observables:

| Observable | Mechanism & Definition | 2018-06-01 Observed Price | Empirical Relationship to Other Observables |
| :--- | :--- | :---: | :--- |
| **`BAR_0930.open`** | First continuous SIP trade print in $[09:30, 09:31)$ | **`$272.40`** | Trade ID 4614 at `13:30:00.005779Z` on NASDAQ (`x='T'`, condition `T`). Prints 138ms before primary cross. |
| **`AUC_OPEN`** | Official NYSE Arca Core Opening Auction Cross | **`$272.49`** | Trade ID 162079 at `13:30:00.1438Z` on NYSE Arca (`x='P'`, condition `O`, 246,189 shares). Exactly sets `BAR_0930.high`. |
| **`BAR_0930.close`** | Final continuous SIP trade print in $[09:30, 09:31)$ | **`$272.44`** | Minute bar close. |
| **`AUC_CLOSE`** | Official NYSE Arca Closing Auction Cross | **`$273.60`** | Trade ID 269704 at `20:00:00.08774Z` on NYSE Arca (`x='P'`, condition `6`, 2,319,924 shares). Differs from 15:59 close ($273.65) and 16:00 bar close ($273.54). |

> [!CAUTION]
> **Definitional Non-Equivalence Invariant:**
> On 2018-06-01, $\text{BAR\_0930.open} (\$272.40) \neq \text{AUC\_OPEN} (\$272.49)$, exhibiting a difference of **+9 cents (+3.30 bps)**.
> While a two-session sample does not prove market-wide statistical significance, it formally proves that bar open and auction cross are distinct mechanical observables. They must never be treated as interchangeable proxies.

---

## 3. Original Literature Methodology (Gao et al. 2018)

A critical literature audit of Gao, Han, Li & Zhou (2018), *"Market Intraday Momentum"*, Journal of Financial Economics (DOI: 10.1016/j.jfineco.2018.05.009), clarifies the exact return definitions:

$$r_{j,t} = \frac{p_{j,t}}{p_{j-1,t}} - 1 \qquad \text{(Primary Specification: Simple Returns)}$$

- **First-half-hour predictor ($r_{1,t}$):**
  $$r_{1,t} = \frac{P_{10:00,t}}{P_{16:00,t-1}} - 1$$
  Predictor $r_{1,t}$ measures the return from **previous market close ($P_{16:00,t-1}$)** through **10:00 ET ($P_{10:00,t}$)**. It explicitly incorporates the overnight return.
- **Role of Official Opening Cross:**
  The official 09:30 Opening Auction Cross ($P_{\text{auc}}$) is **NOT** the denominator of Gao's $r_{1,t}$. Therefore, the 3.30 bps divergence between bar open and opening auction does not contaminate the canonical Gao $r_1$ predictor.
- **Log Returns:**
  Log returns $\ln(P_{10:00} / P_{16:00,t-1})$ are a secondary robustness specification in the literature, not the baseline.
- **Historical Governance Reality:**
  In Phase 14, `HYP_004` registered and evaluated the exact Gao baseline replication ($r_1 \to r_{13}$) across the 2017–2022 SPY sample ($T=1,489$). It failed to reject the null hypothesis ($\hat{\beta} = +0.0225, p = 0.5235 \gg 0.05; R^2_{OS} = -4.84\%$). `HYP_004` is permanently **`TERMINALLY_CLOSED_NOT_SUPPORTED`**.

---

## 4. Point-in-Time (PIT) Integrity & Telemetry Limitations

1. **Clearing Execution $\neq$ Indicative Order Imbalance (NOII):**
   Alpaca Historical Auctions provides matched clearing results (`p`, `s`, `x`), NOT pre-open indicative imbalances (`paired_shares`, `imbalance_shares`, side). Testing pre-open order book pressure requires proprietary exchange feeds (NYSE Arca TAQ / Order Imbalances).
2. **Event Timestamp $\neq$ Strategy Receipt Timestamp:**
   The timestamp `13:30:00.1438Z` is the matching engine execution instant. Historical batch endpoints do not provide vendor publication receipt latency ($t_{\text{recv}}$) or capture retroactive Form T trade corrections.
3. **Boundary Price Observability at 10:00 ET:**
   Selecting the last qualified trade $T^* \le \text{10:00:00 ET}$ represents a deterministic price-space anchor, but does not prove microsecond live execution feasibility without real-time streaming telemetry.

---

## 5. Governance Timing Invariant (Canary 2 Anomaly Closure)

During the Canary 2 post-execution audit, an authority timestamp anomaly was recorded:
- Operator modal approval: `2026-10-11T13:18:42.87Z`
- Authority file `valid_from_utc`: `2026-10-11T13:17:00Z` (pre-dated by 102 seconds)
- Actual dispatch: `2026-10-11T13:18:56Z` (executed after approval)

**Mandatory Invariant for All Future Authorities:**
$$\text{valid\_from\_utc} \ge \text{approved\_at\_utc}$$
Retroactively effective authority windows are strictly rejected.

---

## 6. Scientific Measurement Decision

```text
                                [RI-01 Measurement Decision]
                                              |
             +--------------------------------+--------------------------------+
             |                                                                 |
    [Descriptive / Econometric]                                     [Tradable Strategy]
    - Historical bars: QUALIFIED                                    - PIT Receipt Latency: UNPROVEN
    - Opening auction: QUALIFIED (MEC-0014)                         - Pre-open NOII: UNLICENSED
    - Closing auction: QUALIFIED (MEC-0014)                         - Slippage / Fees: UNMODELLED
    - Boundary mapping: QUALIFIED (MEC-0014A)                       - HYP_004 Baseline: TERMINALLY CLOSED
             |                                                                 |
    [Sufficient for Offline Study]                                  [PARKED: Requires New Feed & Prereg]
```

1. **Auction Canary A1:** Formally marked **`NEW_HTTP_NOT_NEEDED`**.
2. **RI-01 Status:** Elevated to **`DATA_FEASIBILITY_PASS`** across both bars and auctions via historical evidence integration.
3. **Trading & Orders:** Capital remains strictly **`$0.00`**; **`NO_REAL_ORDERS = true`**.
