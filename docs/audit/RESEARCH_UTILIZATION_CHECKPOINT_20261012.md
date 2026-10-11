# Research Utilization & Sample Contamination Audit Checkpoint — 2026-10-12

**Document ID:** `DOC-ACASH-RESEARCH-UTILIZATION-20261012`  
**Base Commit:** `386941c0cc10c7cc1839ae428250776cf74c505a` (Post-PR #22 merge)  
**Classification:** Additive Governance Checkpoint & Sample Isolation Audit  
**Status:** `[ADDITIVE_CHECKPOINT]` · `[SEALS_PRESERVED]` · `[ZERO_OUTCOME_TESTING]`  

---

## 1. Preservation of Historical Hypothesis Classifications

In accordance with `AGENTS.md` core principles, all historical hypotheses remain permanently sealed and unmutated:

| Hypothesis / Asset | Canonical Standing | Sealed Scope & Invariants Preserved | Research Note / Contamination Constraint |
| :--- | :--- | :--- | :--- |
| **HYP_001** | `TERMINALLY_FALSIFIED` | Phase 8.5 EUR/USD sample | Quarantined samples preserved. |
| **HYP_002** | `TERMINALLY_FALSIFIED` | Phase 8.5 EUR/USD sample | Quarantined samples preserved. |
| **HYP_003** | `TERMINALLY_FALSIFIED` | Intraday momentum registered sample | Verified negative reference baseline. Not reopened. |
| **HYP_004** | `TERMINALLY_UNSUPPORTED` | Registered 2017–2022 sample; sealed 2023+ holdout | Predictive regression itself lacked statistical significance (not merely fee drag). Sealed holdout preserved intact. |
| **HYP_005** | `DATA_ENTITLEMENT_BLOCKED` | Non-falsifying entitlement block | Preserved without mutation. |
| **HYP_006** | `QUOTE_PROVENANCE_UNRESOLVED` | Quote provenance open | Preserved without mutation. |
| **HYP_007** | `HISTORICAL_SUPPORTED_CURRENT_UNSUPPORTED` | Registered M1 supported; M2 current edge unsupported | Historical replication intact; prospective M3 sealed. Not universally disproven, but closed for live deployment. |
| **HYP_008** | `RETIRED_PRIORITY` | Pre-R1 administrative retirement | Administrative priority decision; not an empirical falsification. |
| **HYP_009** | `TERMINALLY_CLOSED` | Terminal M2 lifecycle | Preserved. |
| **HYP_010** | `PARKED_NON_FALSIFIED` | Blocked by VEU data authority | Parked cleanly; not an empirical strategy falsification. |
| **HYP_011** | `RETIRED_OPERATIONAL` | V1/V2 operational evidence preserved; V3 offline proposal | Zero market observations created. |
| **RI-01 / Canary 1** | `DATA_FEASIBILITY_PASS` | 2021-06-01 SIP 1Min raw, 390 RTH grid verified on disk | Single-session opening state data feasibility established; NOT strategy validated. Canary 2 unissued. |
| **MEC-0014** | `DATA_FEASIBILITY_PASS` | 1,498 NYSE auction sessions verified on disk | Formalized in PR #22. Feasibility verified for auction mechanics. |

---

## 2. Sample Contamination & Independence Protocol for Personal Track

The Personal Quantitative Investment Track (Global Multi-Asset ETF Universe: VOO, BND, GLD, BIL) must adhere to strict trial accounting:
1. **Instrument Independence**: Prior active research focused primarily on single-stock/ETF intraday minute bars (SPY, EUR/USD). The Personal Track focuses on daily/monthly multi-asset rebalancing across distinct asset classes.
2. **Holdout Protection**: Sealed out-of-sample data (2023–2026) reserved for HYP_004 remains strictly locked and must never be accessed or blended into multi-asset ETF training panels.
3. **Trial Budget Pre-registration**: Any future empirical evaluation of Multi-Asset Trend Following must preregister candidate hyperparameter trials ($K$) to maintain valid Deflated Sharpe Ratio (DSR) provenance.
