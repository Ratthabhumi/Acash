# RI-01 Provider Feasibility (ZERO-OUTCOME, DOCUMENTATION EVIDENCE ONLY)

**Network posture**: ZERO network requests performed in this pack. No explicit
research-network authority was granted, so per the fail-closed rule this pack
STOPS at documentation/API-contract evidence already present in the
repository. Every provider fact below is therefore either `PROVEN_IN_REPO`
(cryptographic manifest or sealed qualification on record) or `UNKNOWN`
(requires an entitled check under separate authorization).

## 1. Candidate providers

### P1 — Alpaca Markets Historical Stock Data (SIP)
Role: primary candidate (all ACASH qualifications to date use it).

| Dimension | Status | Evidence |
| :--- | :--- | :--- |
| Official source | `PROVEN_IN_REPO` (endpoint shapes) | `docs/research/MEC-0015-provider-qualification-contract.md` §2 |
| Daily coverage (1Day SIP, raw/split) | `PROVEN_IN_REPO` (narrow scope) | HYP_011 qualification: 2016-01-04..07, ACWI/AGG/SPY |
| Minute coverage (1Min SIP raw, SPY) | `PROVEN_IN_REPO` (narrow scope) | MEC-0015 manifest: 6 sessions, 2,340/2,340 bars, 390/390 each |
| Minute coverage (ACWI/AGG, any window) | `UNKNOWN` | Never qualified |
| Minute coverage (SPY, full 2017–2026) | `UNKNOWN` | Only 6 probe sessions on record |
| Historical depth limit | `UNKNOWN` | Never contract-tested for RI-01 scope |
| Adjustment modes (raw vs split) | `PROVEN_IN_REPO` (shapes) | Both fetched by HYP_011 client; semantics per MEC-0015 §7 |
| Corporate-action treatment | `PROVEN_IN_REPO` (partial) | 31 SPY cash dividends, ex-dates ≤2024-03-15; PIT vintage NOT guaranteed |
| Timezone semantics | `PROVEN_IN_REPO` | Left-edge bar timestamps, ET wall time, UTC storage (MEC-0015 §4) |
| Missing-session semantics | `PROVEN_IN_REPO` (policy) | `FAIL_CLOSED_SESSION_EXCLUSION`, no imputation |
| Symbol lifecycle support | `UNKNOWN` | Never contract-tested |
| Request limits / quota | `UNKNOWN` | Never measured for RI-01-shaped workloads |
| Reproducibility (byte-stable re-fetch) | `UNKNOWN` | Never re-fetch-tested |
| Point-in-time retrieval | `UNKNOWN` | Dividend vintage explicitly NOT guaranteed; bar revision behavior untested |
| Current credential entitlement | `UNKNOWN` | Credential mechanism exists (`EnvAlpacaCredentialProvider`); tier/coverage/depth unverified without a call |
| Cost (quota, dollars, latency) | `UNKNOWN` | Never measured |
| Licensing / redistribution | `UNKNOWN` | Never reviewed |

### P2 — Exchange/consolidated-tape archives (e.g. TAQ-style)
Role: literature-grade alternative (Gao et al. used TAQ).

| Dimension | Status | Evidence |
| :--- | :--- | :--- |
| All dimensions | `UNKNOWN` | No ACASH qualification, no entitlement, no cost review on record |

### P3 — Zero/low-cost free sources
Role: rejected for feasibility scope (not evaluated).

| Dimension | Status | Evidence |
| :--- | :--- | :--- |
| Suitability | `REJECTED_OUT_OF_SCOPE` | Free-data feasibility belongs to a different lane (HYP_006/MEC-0016); SIP-qualified lineage is the RI-01 baseline |

## 2. Proven in-repo constraints (bind the next step regardless of provider)

1. **The currently-qualified HYP_011 client is 1Day-only.** `HYP011AlpacaClient`
   hard-rejects any other timeframe (`src/acash/data/qualification/hyp_011_qual_client.py`).
   RI-01 minute access therefore requires a NEW minute-capable qualification;
   it cannot ride the HYP_011 client.
2. **Prior close ≠ 15:59 bar close.** The 16:00 auction cross can diverge 1–5 bps
   (MEC-0014 §10.2). A dedicated close-authority contract test is mandatory
   before any $r_1$-style predictor is defined.
3. **Dividend PIT vintage is NOT guaranteed** by the vendor (MEC-0015 §7.3).
   Acceptable only for publication-exposed historical replication, never
   assumed for prospective use.
4. **OOS boundary discipline holds.** Nothing on/after the sealed holdout may
   be touched without explicit human authorization (MEC-0014 §13).

## 3. Evidence required to flip each UNKNOWN (future authorized probe plan, NOT executed)

- Entitlement probe: credential-tier capability listing (zero market dates).
- Depth probe: earliest retrievable 1Min SIP session per candidate symbol.
- Coverage probe: session×symbol availability census over the feasibility window.
- Stability probe: byte-identical re-fetch of a fixed session (reproducibility).
- Revision probe: first-publication vs delayed re-fetch diff.
- Cost probe: measured quota/latency per 1,000 sessions.
- License review: redistribution terms for derived research artifacts.

Each probe needs its own explicit network authorization with a date-bounded,
symbol-bounded scope. This pack performs NONE of them.
