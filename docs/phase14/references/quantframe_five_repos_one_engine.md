# ACASH Phase 14 — Architecture / Research Reference: QuantFrame "Five Repos, One Engine"

> **Document ID:** `docs/phase14/references/quantframe_five_repos_one_engine.md`
> **Reference Type:** `EXTERNAL ARCHITECTURE / INTEGRATION REFERENCE`
> **Status:** `STORED RESEARCH REFERENCE` | `NOT ADOPTED` | `NOT A CANDIDATE STRATEGY`
> **Epistemic Classification:** `REPORTED / EXTERNAL ARCHITECTURE REFERENCE`
> **Authority:** `AGENTS.md` (Strict Fail-Closed, Zero Unverified Claims, Single Canonical Authority), Phase 14 Master Research Architecture (`docs/phase14/phase14_master_research_architecture_plan.md`)
> **Date:** 2026-09-07

---

> [!CAUTION]
> ### HARD GOVERNANCE & SAFETY INVARIANTS
> - **THIS IS AN ARCHITECTURE / INTEGRATION REFERENCE — NOT A STRATEGY CANDIDATE, NOT HYP_003.**
> - **NO ADOPTION:** The external repositories named in this document are **NOT** adopted, installed, integrated, or added as dependencies.
> - **NO IMPLEMENTATION:** Zero source-code changes. Slice 1 and Slice 2 remain UNCHANGED.
> - **NO MARKET-DATA / BROKER / LLM ACCESS:** No market data, broker, exchange, prediction-market connector, or external trading system accessed.
> - **NO STRATEGY QUALIFICATION CHANGE:** No hypothesis registration, no strategy qualification state change.
> - **NO EXECUTION AUTHORITY CHANGE:** `ExecutionCoordinator` and execution authority are UNCHANGED.
> - **NO CAPITAL / TRADING CHANGE:** Capital authority and trading state remain LOCKED / unchanged.
> - **HYP_003 REMAINS NONEXISTENT.**
> - **NO EXTERNAL REPOSITORY IS DECLARED PRODUCTION-READY FOR ACASH.**

---

## 1. Source

- **Title:** *Five Repos, One Engine: Wiring the Open-Source Quant Stack*
- **Publisher / Author:** QuantFrame (Antonije Mirkovic), 2026-08-30
- **URL:** https://www.quantframe.io/article/five-repos-one-engine
- **Classification:** `REPORTED / EXTERNAL ARCHITECTURE REFERENCE`

> This document records **architectural and integration lessons**, NOT validated trading performance. Any numerical result quoted from the article is classified `REPORTED` and has **not** been independently reproduced, verified, or validated by ACASH.

The article was fetched at documentation time and is preserved here for two reasons:

1. It documents a concrete, currently operative "multiple specialized repositories connected into one engine" composition.
2. Its central demonstration — each component works alone while the *composition* is where failures appear — directly reinforces an ACASH governance principle independently re-derived from the Phase 14, Slice 2 adversarial audit.

---

## 2. Core Idea

The central architectural lesson recorded from the article is:

> Multiple specialized quantitative repositories can each work independently while still failing when connected into one system.

```text
component-level correctness  !=  integrated-system correctness
```

Therefore:

- integration seams
- contracts
- schemas
- provenance
- lifecycle semantics
- authority boundaries

...require **independent validation** that component-level testing cannot provide.

**Reported exemplar from the article** (classified `REPORTED`): the article's "bridge test" re-priced an identical swap in ORE and in a standalone QuantLib rebuild of the same exported curve and reports a 1.08 basis-point difference (1,609,885.84 EUR vs 1,608,800.94 EUR on 10M notional), attributed by the article to interpolation residue between the 240 reported curve pillars. The article also reports its two build failures were **version-skew** seams — a renamed pricing engine and a pandas-3 copy-on-write memory change — where each component "works perfectly alone." These are recorded only as reported illustrations of the `component-correct ≠ composition-correct` lesson, not as verified ACASH evidence.

---

## 3. Relevance to ACASH

The article composes repositories in a conceptual stack of the same shape ACASH uses — but with a decisive difference in where authority lives.

**QuantFrame-style conceptual stack (as described in the article):**

```text
Pricing / Analytics
        ↓
Risk
        ↓
Position Sizing
        ↓
Execution
        ↓
Visualization / Monitoring
```

**ACASH architecture:**

```text
Research / AI
        ↓
Evidence / Provenance
        ↓
Qualification Gates
        ↓
Strategy
        ↓
Risk / Sizing
        ↓
ExecutionCoordinator
        ↓
Broker
        ↓
Reconciliation / Audit
```

**Key distinction:**

> External repositories may provide useful capabilities, but **ACASH governance remains the authority layer.**

External libraries must never silently become:

- execution authority
- capital authority
- strategy qualification authority
- evidence authority
- reconciliation authority
- governance bypasses

---

## 4. Direct Connection to Phase 14 Slice 2

The integration lesson in the article is directly relevant to the current Slice 2 adversarial findings. Current Slice 2 adversarial findings prior to remediation were:

- **F-1 HIGH** — Epistemic escalation through Pydantic `model_copy(update=...)`.
- **F-2 HIGH** — Provenance fields were not fully bound to request/result fields.
- **F-3 MEDIUM** — Provider registry did not verify provenance locator against request locator.
- **F-4 LOW** — `MockTransport` could not prove true bounded lazy streaming because the mock response eagerly buffered.
- **F-5 LOW** — Duplicate import.

These findings are examples of **integration-boundary failures**: individual components may behave correctly in isolation while the composition permits invalid state or inconsistent evidence (e.g., a `VERIFIED` `EvidenceRecord` constructed directly although no layer ever set it, or a forged `provenance.locator` that no single component ever contradicted on its own).

> [!IMPORTANT]
> **QuantFrame did NOT cause or discover these findings.** They are **independently discovered ACASH findings** from the adversarial audit of `src/acash/research/ai/retrieval/`. The article merely reinforces the architectural lesson that confident component-level behavior is insufficient to certify integrated behavior.

---

## 5. Global Arbitrage Relevance

This reference is useful to the existing Global Arbitrage research direction (see `docs/phase14/candidates/candidate_prediction_market_ai_forecasting_kalshi_polymarket.md`).

Global Arbitrage requires multiple layers:

```text
Market A                 Market B
              ↓
Semantic / Economic Equivalence
              ↓
Executable Prices
              ↓
Fees / Spread / Slippage
              ↓
Liquidity / Quantity
              ↓
Both-leg Executability
              ↓
Latency / Timing
              ↓
Settlement / Counterparty
              ↓
Deterministic Referee
              ↓
ARBITRAGE CANDIDATE
```

Emphasized principles:

$$\boxed{\text{price discrepancy} \neq \text{arbitrage}}$$

and:

$$\boxed{\text{AI PROPOSES} \quad \longrightarrow \quad \text{DETERMINISTIC REFEREE VERIFIES}}$$

AI may propose or discover candidate relationships, but a deterministic referee must verify the economic conditions. External repositories can potentially provide specialized analytics, forecasting, portfolio, or execution capabilities, but they **cannot** be allowed to declare an arbitrage opportunity authoritative by themselves.

---

## 6. Candidate External Technology Map

Preserved as **RESEARCH CANDIDATES / REFERENCES only** (identified via the QuantFrame article, classified `REPORTED`):

| Area in the article's stack | Reported library/repo | ACASH note |
|---|---|---|
| Trading / execution infrastructure | **NautilusTrader** | Reported: Rust-core event loop with Python strategy layer; article's adoption rationale is backtest-live strategy parity. |
| Portfolio allocation / optimization | **skfolio** | Reported: portfolio optimization behind the scikit-learn `fit/predict` contract; article demonstrates optimizer fragility, not returns. |
| Pricing / risk engine | **QuantLib + ORE** (Open Source Risk Engine) | Reported: day-count/holiday plumbing (QuantLib) and portfolio XVA/exposure simulation (ORE); ORE input is XML. |
| Visualization / dashboard | **Perspective** | Reported: streaming query engine (WebAssembly in browser + native Python server); article notes the bundled handler ships with no authentication. |

Constraints:

- ACASH does **not** claim all five repositories are required.
- ACASH does **not** install, integrate, or depend on any of them.
- The purpose is to evaluate whether individual capabilities could later be connected through **explicit ACASH adapters** — and only if governance review authorizes such an evaluation.

---

## 7. Proposed Future Adapter Architecture

Conceptual architecture preserved for future evaluation (NOT implemented):

```text
                    ACASH Governance
                           │
              ┌────────────┴────────────┐
              │                         │
        Research Layer             Strategy Layer
              │                         │
      External libraries        ACASH canonical model
              │                         │
              └────────────┬────────────┘
                           │
                  Deterministic Gates
                           │
                    Risk / Sizing
                           │
                  ExecutionCoordinator
                           │
                        Broker
                           │
                    Reconciliation
```

**Principle:**

> External technology = capability provider. ACASH = governance and authority boundary.

---

## 8. Integration Review Principles

Future evaluation criteria for ANY external capability under consideration for ACASH:

- explicit input/output contracts
- immutable evidence where appropriate
- provenance preservation
- deterministic serialization
- hash semantics
- epistemic classification boundaries
- fail-closed behavior
- authority separation
- timeout/recovery semantics
- execution lifecycle integrity
- reconciliation integrity
- dependency isolation
- clean-clone reproducibility
- deterministic testing
- adversarial integration testing

**Explicit statement:**

> A repository passing its own tests is **insufficient evidence** for ACASH integration.

Required future sequence:

```text
component validation
→ adapter validation
→ contract validation
→ adversarial integration audit
→ system-level validation
→ governance review
```

---

## 9. ACASH Adoption Policy

$$\boxed{\text{DO NOT ADOPT NOW.}}$$

Current priority remains:

```text
Slice 2 F-1 through F-5 remediation
→ full validation
→ repeat adversarial audit
→ Slice 2 closure
→ only then consider Slice 3
```

This reference does **not** expand current implementation scope.

---

## 10. Epistemic Boundary

| Classification | Applies to |
|---|---|
| **VERIFIED** | ACASH's own currently audited architecture/governance findings (e.g., the Slice 2 adversarial findings and their remediation). |
| **REPORTED** | Claims and architecture described by QuantFrame. |
| **INFERRED** | Potential usefulness of individual external repositories as future ACASH adapters. |
| **NOT PROVEN** | That QuantFrame's combined engine is superior for ACASH; that any external repository improves ACASH profitability; that integration would be safe without adapter-level governance; that the external stack is compatible with ACASH's frozen architecture; that any claimed performance results are independently reproducible. |

---

## 11. Final Governance Statement

> "QuantFrame Five Repos, One Engine is retained as an architectural integration reference, not as an implementation mandate."

And:

> "ACASH must treat external quantitative repositories as untrusted capability providers until their interfaces, provenance, authority boundaries, deterministic behavior, and adversarial integration properties are independently verified."

---

## 12. Change Scope / Audit

- **Change type:** Documentation only.
- **Files:** `docs/phase14/references/quantframe_five_repos_one_engine.md` (new).
- **No source code changed.**
- **No dependencies changed.**
- **HYP_003 does not exist and was not created.**
- **Trading / capital state unchanged and LOCKED.**
- **Slice 2 implementation unchanged** (commit `6e995e7` intact).
- **Global Arbitrage candidate document untouched.**

**Recorded Result:**
- **Reference:** QuantFrame "Five Repos, One Engine" — `EXTERNAL ARCHITECTURE / INTEGRATION REFERENCE`
- **Status:** STORED RESEARCH REFERENCE / NOT ADOPTED
- **Epistemic:** REPORTED / EXTERNAL ARCHITECTURE REFERENCE
- **Implementation:** NONE
- **Trading:** LOCKED
- **HYP_003:** NOT CREATED
- **Next action:** HUMAN REVIEW

**STOP.**