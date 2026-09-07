# ACASH Phase 14 Research Doctrine

**Status:** METHODOLOGY REFERENCE — research guidance only. Not a trading rule, not an alpha
qualification rule, not a execution policy, not a hypothesis registration.

**Canonical authority:** This document is the single Phase 14 research-methodology reference. It
does NOT define numeric gates, backtest results, or strategy specifications. It does not create
HYP_003.

---

## 1. Purpose

Phase 14 already governs *proposal intake* (Slices 1–2), *deterministic feature discovery* (Slice 3),
and *evidence-grounded reporting* (Slice 4). This doctrine adds the missing layer sitting **above**
hypothesis intake: a durable reference for **how to think** about candidate research — what makes a
mechanism worth testing, when complexity is justified, how edge must be evaluated after friction, and
how candidates must be falsified before they are qualified.

The central idea:

```text
SOURCE CLAIM
    ↓
RESEARCH PRINCIPLE
    ↓
TESTABLE HYPOTHESIS
    ↓
EVIDENCE
    ↓
VALIDATION / FALSIFICATION
```

This doctrine exists to make the research process

```text
SOURCE CLAIM
    ↓
RESEARCH PRINCIPLE
    ↓
TESTABLE HYPOTHESIS
    ↓
EVIDENCE
    ↓
VALIDATION / FALSIFICATION
```

and never

```text
SOURCE CLAIM
    ↓
ASSUMED TRUTH
    ↓
TRADING RULE
```

---

## 2. Source and Epistemic Status

This doctrine was derived from reviewed external video summaries:

- **"Secrets of the MEDALLION FUND"**
- **"Give me 26 minutes to save you 6 years of useless financial misinformation"**
- **"I think i found the best trading strategy... (150 years of data)"**

All claims originating from these materials are classified:

> **REPORTED / EXTERNAL SOURCE**

The following types of claims from those materials are **NOT** promoted to ACASH VERIFIED facts:

- Medallion return figures
- p-value < 0.01 usage assertions
- 51–55% win-rate claims
- MA200 reducing volatility by ~60%
- specific historical performance claims
- statements about which ML architecture is superior

Where any such claim is referenced, it is explicitly labeled:

> **REPORTED** — source video states X.
> **NOT INDEPENDENTLY VERIFIED** — ACASH has not reproduced or validated the claim.
> **REQUIRES OPERATIONALIZATION / TESTING** — the claim is a research direction, not a finding.

---

## 3. Core Doctrine (Summary)

1. **Mechanism before model** — start from an economic/behavioral/structural mechanism.
2. **Simple before complex** — complexity must earn its existence incrementally.
3. **Edge after friction** — gross edge is not net edge.
4. **Falsification before qualification** — every candidate must answer "what would kill this?".
5. **Structural flow is researchable** — forced flows are legitimate candidate families, not proof.
6. **Time horizon is empirical** — horizon is a research variable, not a doctrine.
7. **Alpha decays** — edge existence does not imply edge permanence.
8. **AI proposes, deterministic system verifies** — AI never self-authorizes evidence, alpha,
   arbitrage, execution, or capital.

Each principle is developed below.

---

## 4. Mechanism Before Model

Candidate research should begin with a plausible economic, behavioral, or structural mechanism before
selecting a sophisticated model.

Candidate mechanism families (examples, NOT established alpha):

- forced / rebalance flows
- liquidity shocks
- block-trade effects
- temporary relative-value dislocations
- short-horizon continuation / momentum

Required research questions for any candidate mechanism:

1. Who is forced to trade?
2. Why are they forced?
3. What price distortion should result?
4. How long should the distortion persist?
5. What observable variable should detect it?
6. What evidence would falsify the mechanism?

---

## 5. Simple Before Complex

Complexity must earn its existence.

Preferred progression:

```text
simple feature
    ↓
simple interaction
    ↓
nonlinear model
    ↓
complex model
```

Simple candidate primitives (examples):

- returns
- moving averages
- volatility
- spread
- volume
- z-scores

This doctrine does **not** claim simple models are always better. The principle is **incremental
evidence**:

> Complexity requires incremental evidence.

Optional future research metadata (NOT implemented; requires separate authorization):

- expression depth
- operator count
- parameter count
- transformation count
- economic rationale
- out-of-sample stability

---

## 6. Edge After Friction

Gross edge is not sufficient.

Conceptual identity:

```text
Expected Value
=
P(win) × average win
-
P(loss) × average loss
-
cost
```

Candidates must be examined across:

- gross edge
- spread
- fees
- slippage
- turnover
- variance
- drawdown
- serial dependence
- stability
- multiple-testing effects

Core rule:

> **GROSS EDGE != NET EDGE**

Win rate alone is **never** a qualification criterion.

---

## 7. Falsification Before Qualification

Every candidate must have an explicit answer to:

> "What evidence would kill this hypothesis?"

Preferred flow:

```text
Interesting pattern
    ↓
Candidate
    ↓
Pre-registration
    ↓
Search / experiment
    ↓
Falsification attempts
    ↓
Validation
    ↓
Qualification
```

Never:

```text
AI sees pattern
    ↓
AI declares edge
    ↓
Strategy qualification
```

This doctrine maps onto ACASH's existing lifecycle:

```text
Hypothesis → R1 → R2 → R3 → Validation → Qualification
```

where R1 is hypothesis pre-registration, R2 is search/experiment, and R3 is validation, all guarded
by ACASH gates (e.g. `ResearchReInceptionGate`) and sealed, falsifiable pre-registration. Phase 14
proposals remain `UNVALIDATED_PROPOSAL` unless and until they pass the official gates.

---

## 8. Structural Flow Is Researchable

Forced flows / rebalancing / liquidity shocks are legitimate candidate research families because
participants may trade for reasons other than fundamental valuation.

Candidate example mechanisms:

- weekend inventory constraints
- month-end / quarter-end rebalancing
- large order / block-trade effects
- temporary spread dislocations
- liquidity-driven deviations

Important boundary:

> behavioral explanation != proof of profitability

Every mechanism must become a testable hypothesis and survive validation.

---

## 9. Time Horizon Is Empirical

This doctrine does not favor a horizon:

- NOT: "HFT is bad"
- NOT: "intraday is good"
- NOT: "swing is superior"
- NOT: "daily is superior"

Horizon is a **research variable**.

Potential horizons to evaluate:

```text
M1  M5  M15  H1  H4  Daily  Weekly
```

Candidate evaluation dimensions:

- signal quality
- noise
- transaction cost
- turnover
- net edge
- stability
- drawdown
- execution sensitivity

Possible conceptual diagnostics (research concepts only — NOT existing ACASH metrics unless they are
formally introduced):

- net edge / unit of noise
- net edge / unit of turnover

---

## 10. Alpha Decays / Crowding

Every candidate edge should eventually face questions about:

- temporal stability
- regime dependency
- decay
- crowding
- changing transaction costs
- execution delay sensitivity

Possible future diagnostics (NOT implemented):

- signal-strength decay
- decay half-life
- regime stability
- crowding proxies
- cost sensitivity
- latency sensitivity

Core rule:

> **EDGE EXISTENCE != EDGE PERMANENCE**

This doctrine does not claim any specific decay magnitude without evidence.

---

## 11. AI Proposes, Deterministic System Verifies

AI may:

- discover candidate mechanisms
- propose features
- propose hypotheses
- summarize evidence
- identify possible relationships

AI must **NOT** independently authorize:

- VERIFIED evidence
- qualified alpha
- arbitrage
- execution
- capital allocation
- paper readiness
- live readiness

Deterministic ACASH components (validation gates, qualification, execution, capital) remain the sole
authoritative actors. This doctrine aligns with the Slice 1–4 architecture (`./phase14_architecture_and_governance_plan.md`,
`./phase14_master_research_architecture_plan.md`).

---

## 12. Global Arbitrage Connection

The same methodology applies to future Global Arbitrage research:

```text
Observed divergence
    ↓
Semantic / economic equivalence
    ↓
Executable prices
    ↓
Fees / spread / slippage
    ↓
Liquidity / quantity
    ↓
Both-leg executability
    ↓
Latency / timing
    ↓
Settlement / counterparty
    ↓
Deterministic referee
    ↓
ARBITRAGE CANDIDATE
```

Explicit rule:

> **PRICE DISCREPANCY != ARBITRAGE**

AI may propose equivalence/candidate relationships. A **deterministic referee** must verify the
economic conditions before anything is called an arbitrage candidate. No arbitrage engine is
implemented by this document or authorized by it.

---

## 13. Example Future Hypothesis Families

These are **hypothesis families**, not strategies and not HYP_003.

### MA / Regime Filtering

Example framing:

- **H0:** MA-based regime filtering provides no economically meaningful risk-adjusted improvement
  after costs.
- **H1:** MA-based filtering reduces downside/tail exposure without destroying excessive upside
  participation.

Boundaries:

- MA200 is **REPORTED** to reduce volatility by ~60% in the reviewed materials. This is
  **NOT INDEPENDENTLY VERIFIED** and is **NOT** stated here as an ACASH fact.
- No strategy is created from this family by this document.
- No specific magnitude of performance improvement is claimed.

### Structural Flow Candidates

Example families from Section 8 (rebalancing, liquidity shocks, weekend/month-end effects) are
forward research directions requiring operationalization and pre-registered testing before they may
ever be evaluated by ACASH gates.

---

## 14. What This Doctrine Explicitly Does NOT Authorize

This doctrine does not authorize, define, or create:

- trading rules
- alpha qualification rules
- live execution policy
- numeric gates
- backtest results
- strategy specifications
- HYP_003
- market-data connectors
- broker / MT5 access
- AI self-authorization of evidence, alpha, arbitrage, or capital
- deterministic referee bypass
- changes to frozen core or governance gates

---

## 15. Relationship to Phase 14 Architecture

This doctrine is research guidance feeding the existing pipeline conceptually:

```text
Slice 1      Evidence / epistemic governance            (ai/schema.py)
    ↓
Slice 2      Source / retrieval / provenance            (hypothesis intake, UNVALIDATED_PROPOSAL)
    ↓
Slice 3      Deterministic feature discovery            (search anchors, manifests)
    ↓
Slice 4      Evidence-grounded reporting                (reporting/, EvidenceGroundingVerifier)
    ↓
Future       Mechanism-driven + falsification-first + friction-aware research
```

Slices 1–4 are **not modified** by this document.

---

## 16. Epistemic Classification

For every external claim, maintain explicit labeling:

**REPORTED**
- source/video says X

**INFERRED**
- this suggests a useful research direction

**NOT PROVEN**
- profitability / predictive power / persistence has not been demonstrated

**VERIFIED**
- only ACASH evidence that has actually passed its own validation process

> No source claim becomes VERIFIED merely because it is cited repeatedly.

---

## 17. Governance Conclusion

This document is a methodology reference. It binds no state, opens no capital, qualifies no alpha,
and registers no hypothesis. Governance semantics, numeric thresholds, and qualification rules are
unchanged.

---

"These principles are research guidance, not proof of alpha."

"Evidence must determine whether a principle, mechanism, feature, or strategy survives empirical
validation."