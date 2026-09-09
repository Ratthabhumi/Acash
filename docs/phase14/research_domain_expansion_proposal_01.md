# PHASE 14 RESEARCH DOMAIN / RESEARCH FAMILY EXPANSION PROPOSAL — SOLID MARKET-STRUCTURE RESEARCH TAXONOMY

**Document ID:** `docs/phase14/research_domain_expansion_proposal_01.md`
**Type:** [PROPOSAL] — documentation artifact only. No code, no hypothesis, no candidate.
**Status:** PROPOSAL
**Date:** 2026-09-08
**Authority:** `./AGENTS.md`, `./research_doctrine.md`, `./research_candidates.md`,
`./phase14_master_research_architecture_plan.md`, `./phase14_architecture_and_governance_plan.md`,
`../phase13/phase13_step7_paper_readiness_review.md`
**Companion artifacts (NOT modified by this document):** `./research_candidates.md`,
`./reviews/proposal_cand_flow_calendar_rebalance_001.md` (F-1),
`./phase14_ratification_record_D1_D4.md`, `./phase14_ratification_record_E1_E9.md`.

> [!CAUTION]
> ### HARD GOVERNANCE & SAFETY INVARIANTS
> - **THIS DOCUMENT AUTHORIZES NOTHING.** Status is **[PROPOSAL]**.
> - **NO HYPOTHESIS AUTHORIZED.** HYP_003 REMAINS ABSENT. No hypothesis registration.
> - **NO R1. NO Gate invocation.** `ResearchReInceptionGate` / `ValidationGate` /
>   `AlphaQualificationGate` are NOT invoked.
> - **NO TRADING AUTHORIZATION. NO CAPITAL AUTHORIZATION.** Capital = **$0.00**;
>   Trading = **LOCKED**; Broker = **DISCONNECTED**; Orders = **0**.
> - **NO IMPLEMENTATION AUTHORIZATION.** No source code, no tests, no executable artifact.
> - **NO EMPIRICAL CLAIM IS ESTABLISHED BY THIS DOCUMENT.** All external concepts are
>   **REPORTED / EXTERNAL_SOURCE / NOT INDEPENDENTLY VERIFIED** research leads only.
> - **NO PROMISE OF PROFITABILITY.**
>
> Classification legend: **V**=VERIFIED (canonical source) | **R**=REPORTED | **I**=INFERRED |
> **P**=PROPOSED (proposal-level) | **NP**=NOT PROVEN | **HF**=REQUIRES HUMAN FREEZE.

---

## 1. Objective [P]

Create a governance-safe, market-agnostic Phase 14 **RESEARCH DOMAIN / RESEARCH FAMILY taxonomy**
based on market-research concepts supplied by the human (social-media screenshots and educational
material). The purpose is **NOT** to add trading strategies. The purpose is to define additional
research domains that the future ACASH Research Engine may discover, classify, reproduce, falsify,
and — only through the existing governed research pipeline — potentially transform into
`UNVALIDATED_PROPOSAL` artifacts. [P]

This document deliberately does NOT say "add GEX strategy". A concept, indicator, social-media claim,
chart, or educational explanation is **not** an established trading edge and is not a candidate. [P]

## 2. Core principle: the intended research pipeline [V]

ACASH must not treat a trading concept, indicator, claim, chart, or educational explanation as an
established edge. The intended pipeline is: [V]

```
Claim
  ↓
Source / Provenance
  ↓
Evidence
  ↓
Mechanism
  ↓
Observable Variables
  ↓
Testable Hypothesis
  ↓
Independent Reproduction
  ↓
Falsification
  ↓
UNVALIDATED_PROPOSAL
  ↓
Human / canonical research gates
  ↓
Candidate / eventual strategy admission
```

**Do NOT** skip directly from "interesting concept" to "strategy". The lower stages of the pipeline
are **NOT activated** by this proposal. [V]

## 3. Source / evidence status [R]

The human supplied social-media screenshots and educational material covering concepts including:

- trading-strategy ranking / indicator criticism
- momentum
- mean reversion
- volatility clustering
- return autocorrelation
- absolute-return autocorrelation
- options open interest
- gamma
- delta
- GEX / gamma exposure
- dealer hedging
- 0DTE
- theta decay
- convexity
- order flow
- order book
- liquidity heatmaps
- volume profile
- market microstructure
- price impact
- displayed vs executed liquidity

**Epistemic classification:** These materials are **SOURCE MATERIAL / RESEARCH LEADS ONLY**. [R]

- They are **NOT** independently verified ACASH evidence. [NP]
- No claim is upgraded from **REPORTED / EXTERNAL_SOURCE / UNVERIFIED** to **VALIDATED** /
  **CONFIRMED** / **PROFITABLE** / **ALPHA** / **ACASH strategy**. [NP]
- If exact source identity cannot be established from the supplied material, that limitation is
  preserved: **SOURCE IDENTITY = NOT ESTABLISHED FROM SUPPLIED MATERIAL**. [R]
- Any numeric values shown in the supplied screenshots (e.g., reported correlations, returns,
  statistics) must **NOT** be stored as canonical ACASH findings unless independently reproduced. [NP]

## 4. Documentation scope [V]

- ONE new [PROPOSAL] documentation artifact: this file. [V]
- **NOT modified:** `docs/ROADMAP.md`, F-1 proposal (`./reviews/proposal_cand_flow_calendar_rebalance_001.md`),
  G-1/G-2/G-4 ratification records, E9 records, retrieval documentation, source code, tests, Gate
  records, Hypothesis registry, R1 artifacts, `./research_candidates.md`, `./research_doctrine.md`. [V]
- **NO HYP_003**. **NO executable implementation.** [V]

## 5. Proposed research family taxonomy [P]

The following are **PROPOSED RESEARCH FAMILIES — research categories, NOT approved strategies**. [P]
Each is a future area the Research Engine may investigate under the governed pipeline; none is
assumed to be profitable. [P]

### 5.1 PRICE / CROSS-SECTIONAL RESEARCH

Examples: ranking, relative strength, cross-sectional effects, price-based signals. [R]

**Research question:** Can observable cross-sectional structure predict future returns after costs
and appropriate controls? [P]

**Important:** Do not assume ranking or relative strength is profitable. [NP]

### 5.2 MOMENTUM / CONTINUATION

Examples: short-horizon momentum, medium-horizon momentum, trend continuation. [R]

The supplied material contains a claim that momentum may be weak or absent across particular
horizons/samples. Record as a **FALSIFIABLE EXTERNAL CLAIM**, not a universal fact. [R]

The Research Engine should be able to test: sample dependence, horizon dependence, regime
dependence, asset dependence, transaction-cost sensitivity, multiple-testing effects. [P]

### 5.3 MEAN REVERSION / PRICE DISLOCATION

Examples: reversal, temporary dislocation, post-event reversal, price deviation from reference
conditions. [R]

Do not assume mean reversion exists. Require mechanism + evidence + out-of-sample testing. [P]

### 5.4 VOLATILITY / REGIME RESEARCH

Examples: volatility clustering, absolute-return autocorrelation, volatility persistence, regime
transitions, realized volatility forecasting. [R]

**Explicitly distinguish directional predictability from volatility predictability.** [V]
- `Corr(r_t, r_{t+k}) ≈ 0` does **NOT** imply `Corr(|r_t|, |r_{t+k}|) = 0`. [V]
- Volatility persistence does **NOT** imply directional alpha. [V]

Exact empirical values shown in supplied screenshots must **NOT** be stored as canonical findings
unless independently reproduced. [NP]

### 5.5 OPTIONS / DERIVATIVES MICROSTRUCTURE

Examples: option open interest, implied volatility, delta, gamma, theta, convexity, expiration
structure, 0DTE behavior. [R]

Treat these as **observable market-structure variables** whose predictive relationship must be
tested. Do **NOT** interpret `OI → price target` as a valid causal relationship without evidence. [NP]

### 5.6 GAMMA EXPOSURE / DEALER HEDGING

Examples: GEX, gamma concentration, gamma walls, dealer positioning, dynamic hedging,
gamma-induced feedback. [R]

**Potential mechanism (MECHANISM HYPOTHESIS TEMPLATE only):** [I]

```
options positioning
  → dealer delta exposure
  → hedge requirement
  → underlying order flow
  → price / volatility dynamics
```

- Do **NOT** assert dealer positioning from OI alone. [NP]
- Do **NOT** assume dealer side/position. [NP]
- Do **NOT** convert GEX directly into BUY/SELL signals. [NP]

Potential dependent variables (all require independent empirical validation): [P]
realized volatility, intraday variance, return autocorrelation, distance-to-strike behavior, price
pinning/dispersion, liquidity, reversal behavior. [P]

### 5.7 ORDER FLOW / MARKET MICROSTRUCTURE

Examples: order-book imbalance, executed volume, bid/ask behavior, liquidity concentration, volume
profile, price impact, trade intensity, market depth. [R]

**Explicitly distinguish DISPLAYED LIQUIDITY from EXECUTED LIQUIDITY.** [V]

Displayed orders can be cancelled, moved, refreshed, or otherwise fail to represent executed
demand/supply. **Visible liquidity wall ≠ guaranteed support/resistance.** [V]

Potential research variables: depth, imbalance, spread, executed volume, aggressor flow, queue
dynamics, cancellation rate, price impact. [P] Research candidates only. [P]

### 5.8 STATISTICAL MARKET-PROPERTY RESEARCH

Examples: autocorrelation, partial autocorrelation, return distribution, volatility distribution,
tail behavior, heteroskedasticity, regime persistence, dependence structure. [R]

Purpose: identify statistical properties of the market **before** attempting to construct a trading
strategy. This family is allowed to produce a **NEGATIVE result** — e.g., "no statistically robust
predictive relationship under the tested conditions" is a **valid research output**. [P]

### 5.9 EXECUTION / LIQUIDITY-AWARE RESEARCH

Examples: transaction costs, spread, slippage, market impact, liquidity constraints, execution
timing. [R]

**Must remain separate from trading authority.** The Research Engine may study execution effects.
It must **NOT** create orders or connect to a broker. [V]

### 5.10 EVENT / EXPIRATION / FLOW RESEARCH

Examples: options expiration, 0DTE expiration, index rebalance, scheduled flows, event-day
microstructure. [R]

**Keep distinct from F-1.** Do **NOT** modify or reinterpret `CAND-FLOW-CALENDAR-REBALANCE-001`. [V]
Purpose here is only to establish a broader research family. **No new candidate is created.** [V]

## 6. Research family → claim handling [P]

For every external claim, the future Research Engine should capture: [P]

- claim
- source
- source type
- provenance
- date/context if available
- instrument/universe
- timeframe
- methodology
- reported result
- reported limitations
- independent verification status

Use statuses such as: `REPORTED` / `EXTERNAL_SOURCE` / `NOT_INDEPENDENTLY_VERIFIED` /
`REPRODUCED` / `FALSIFIED`. [P]

**Do not invent evidence.** [V]

## 7. Mechanism-first requirement [P]

Every serious research lead should attempt to answer: **WHY WOULD THIS EFFECT EXIST?** [P]

- Momentum: information diffusion / behavioral persistence / institutional flow. [I]
- Mean reversion: temporary liquidity imbalance / overreaction / inventory effects. [I]
- Volatility clustering: time-varying risk / volatility regime persistence. [I]
- GEX: option convexity / delta adjustment / dealer hedging flow. [I]
- Order flow: inventory / liquidity / information asymmetry / market impact. [I]

These are **MECHANISM HYPOTHESES, NOT established explanations**. Inferred mechanisms are
explicitly labeled **[INFERENCE]** unless supported by a cited source. [V]

## 8. Falsification-first design [P]

For each research family, define how ACASH should attempt to **disprove** the claim. At minimum
consider: [P]

- independent sample
- out-of-sample window
- multiple horizons
- multiple assets where appropriate
- transaction costs
- spread
- slippage
- liquidity
- regime dependence
- survivorship bias
- lookahead bias
- multiple testing
- parameter sensitivity
- source/data quality
- clustering/dependence
- economic mechanism consistency

**Do not promise profitability.** **Do not optimize until the research protocol permits it.** [V]

## 9. Negative results are first-class research outputs [V]

Examples of valid negative outputs:

- momentum absent
- GEX relationship unstable
- order-book signal disappears after costs
- OI relationship non-predictive
- volatility property exists but is not tradable
- effect only exists in one sample
- effect disappears out-of-sample

**A falsified claim is valuable research information.** [V]

## 10. Relationship to Phase 14 [V]

This proposal reinforces the existing Phase 14 Research Engine concept: Phase 14 is not merely an
indicator generator. It is intended to support: [V]

- external literature intake
- known-mechanism research
- claim reproduction
- anomaly investigation
- feature discovery
- hypothesis formulation
- falsification
- candidate generation

**No new Phase number. No redefinition of canonical slice numbering. No change to the existing
Phase 14 architecture contract.** [V]

## 11. Relationship to Phase 13 [V]

Preserve **Research Runtime ≠ Trading Authority**. The Research Engine may research futures,
equities, options, crypto, and other supported market data **without granting execution
authority**. [V]

No provider/hypothesis research output may: connect to broker, place orders, alter capital, bypass
`ValidationGate`, bypass `AlphaQualificationGate`, create R1, create HYP_003, authorize Step 8,
or authorize Step 9. [V]

## 12. Asset / market agnosticism [P]

Do **NOT** hard-code this proposal to S&P 500. Research families are market-agnostic. [P]

Possible research environments (RESEARCH DOMAINS, **not** an approved trading universe): equities,
equity indices, futures, options, crypto. [P]

**Do NOT declare ES/NQ/SPY/BTC/ETH/etc. as approved instruments.** [V]

## 13. ACASH Research Engine target model [P]

Conceptual model only:

```
                EXTERNAL WORLD
                      │
                      ▼
               CLAIM / OBSERVATION
                      │
                      ▼
               SOURCE + PROVENANCE
                      │
                      ▼
                   EVIDENCE
                      │
                      ▼
                  MECHANISM
                      │
                      ▼
              OBSERVABLE VARIABLES
                      │
                      ▼
               TESTABLE HYPOTHESIS
                      │
             ┌────────┴────────┐
             ▼                 ▼
         REPRODUCE          FALSIFY
             │                 │
             └────────┬────────┘
                      ▼
             UNVALIDATED_PROPOSAL
                      │
                      ▼
             HUMAN / GOVERNANCE
                      │
                      ▼
             QUALIFIED STRATEGY
                      │
                      ▼
             EXECUTION PIPELINE
```

The lower stages are **NOT activated** by this proposal. [V]

## 14. Governance status [V]

**STATUS: [PROPOSAL]**. This document explicitly states:

- no hypothesis authorized
- no HYP_003
- no R1
- no Gate invocation
- no trading authorization
- no capital authorization
- no implementation authorization
- no empirical claim established by this document

## 15. Governance invariants [V]

| Invariant | State |
|---|---|
| HYP_003 | ABSENT |
| R1 | NOT STARTED |
| ValidationGate | NOT INVOKED |
| AlphaQualificationGate | NOT INVOKED |
| Step 8 | LOCKED |
| Step 9 | LOCKED |
| Capital | $0.00 |
| Broker | DISCONNECTED |
| Orders | 0 |
| Trading | LOCKED |
| F-1 | UNTOUCHED |
| Retrieval | UNRESOLVED / EXCLUDED |
| E9 | DEFERRED |

## 16. Contradiction policy / open governance items [V]

Existing documentation contradictions are **NOT reconciled** by this document. `docs/ROADMAP.md`
status, master plan approval lines, stale soak PID references, historical slice numbering,
retrieval mapping, and E9 are NOT modified. [V]

Where an existing contradiction could affect this proposal, it is recorded here as an explicit
**LIMITATION / OPEN GOVERNANCE ITEM** rather than being silently fixed: [V]

- ROADMAP/master plan Phase 14 status lines remain in a "HUMAN APPROVAL PENDING" / "ZERO RUNTIME
  CODE" posture even while G-2/G-4 have been ratified by the human — retained as an open governance
  item for a later reconciliation turn. [R]
- The retrieval implementation self-labels as "Slice 2", which differs from the canonical slice
  authority (GoA §9). Retrieval remains CANONICAL POSITION = UNMAPPED / AUTHORIZATION =
  UNRESOLVED. This proposal does not rely on retrieval. [R]
- E9 is DEFERRED with unresolved master contradictions (stale soak PID, slice drift). Not affected
  by, and not affecting, this taxonomy. [R]
- **SOURCE IDENTITY OF THE SUPPLIED MATERIAL = NOT ESTABLISHED**; screenshots/educational material
  are unverified leads only. Any future intake must first resolve provenance. [R]

## 17. Validation checklist (post-write, observed) [V]

- [x] Exactly ONE new file created: `docs/phase14/research_domain_expansion_proposal_01.md`.
- [x] No source code changes.
- [x] No test changes.
- [x] No `docs/ROADMAP.md` changes.
- [x] F-1 proposal unchanged.
- [x] Retrieval documentation unchanged.
- [x] `git diff --check` clean (see report).
- [x] Governance-invariant audit of this document passes (see Section 15).
- [x] No [VALIDATED] / [CONFIRMED] language applied to external claims (all `[R]` / `[NP]` /
      `[I]` / `[P]`).
- [x] No HYP_003 / R1 / Gate / trading authority granted by this document.

## 18. Hard stop [V]

This is a **PROPOSAL ONLY**. After this document:

- STOP. No implementation. No candidates. No hypotheses. No backtests. No gates.
- No canonical governance modification. No commit. No push.