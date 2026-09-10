# ACASH Market Research Ontology v1

**Status:** `[RESEARCH ONTOLOGY]` · `[NON-NORMATIVE]` · `[NO IMPLEMENTATION AUTHORITY]`

**Document ID:** `docs/phase14/acash_market_research_ontology_v1.md`

This document is a **conceptual research ontology / reference vocabulary** for ACASH. It captures
research *dimensions and framings* that surfaced in an exploratory research discussion. It is
**deliberately not** a doctrine, not a roadmap, not an architecture, not an implementation
specification, and not a governance decision. It grants **no authority** to create or modify any
hypothesis, feature, registry, gate, threshold, or trading capability.

---

## 1. Purpose

Preserve, as durable conceptual context, the research dimensions discussed:

Time · Session · Market State · Liquidity · Microstructure · Event Time · Cross-Asset Information ·
Information Flow · Price Discovery · Multi-Scale Structure · Causality · Non-Stationarity ·
Reflexivity.

The purpose is to ensure ACASH does not *lose* these conceptual research dimensions while they are
still untested. It is a vocabulary and a set of research questions — not a list of alpha sources,
features, or strategies.

---

## 2. Governance Boundary

This document MUST NOT, and MUST NOT be interpreted to:

- create `HYP_003`
- create or modify any `HYP_001` / `HYP_002` registry state
- start `R1`
- invoke `ResearchReInceptionGate`
- invoke `ValidationGate`
- invoke `AlphaQualificationGate`
- authorize any candidate
- authorize backtesting
- authorize paper trading
- authorize live trading
- authorize capital
- modify Phase 13 status
- modify Phase 14 gate status
- modify any `D1`–`D9` decision
- modify `D5` / `D6` / `D8-B` acceptance state
- modify any governance record
- modify `ROADMAP.md`
- modify existing research architecture
- add production source code
- add production features
- add tests
- modify schemas
- modify statistical thresholds
- modify gate mathematics
- modify existing candidate definitions

No approval may be inferred from the existence of this document.

---

## 3. Market Generating Process

The ontology does not model ACASH merely as:

```text
Price → Indicators → Signal → Trade
```

A broader, more faithful conceptual framing is:

```text
TIME + EVENTS + MARKET STATE
        ↓
    PARTICIPATION
        ↓
     LIQUIDITY
        ↓
 PRICE FORMATION
        ↓
 MULTI-SCALE BEHAVIOR
        ↓
     HYPOTHESIS
        ↓
   FALSIFICATION
```

This is an ontology / conceptual research framing. It is **NOT** an implementation architecture
mandate and **NOT** a pipeline specification.

---

## 4. Time as Context

Time must not be treated merely as a timestamp. The ontology distinguishes:

- **time as context** — conditioning information for interpreting market behavior
- **time as a predictive feature** — an input fed to a model

These are different; a research investigation may begin with the former without committing to the
latter, and vice versa.

Potential temporal dimensions (conceptual, not features):

- calendar time
- trading / session time
- event time
- volume time
- tick time
- holding time
- time since event
- time-of-day
- session phase
- session transition
- market open / close state
- overlap state

None of the above are encoded as trading rules.

### 4.1 Calendar Time
Wall-clock / UTC alignment of observations. For cross-market reasoning, calendar alignment across
venues and holidays matters conceptually.

### 4.2 Session Time
Session-anchored time. Session examples that were discussed (illustrative, not normative):

- Asian
- London
- New York AM
- New York PM

Advertising these sessions is descriptive of a research discussion, not a trading rule and not a
feature/bucket specification.

### 4.3 Event Time
Event-anchored time — see §8 Event Time.

### 4.4 Holding Time
The conceptual holding/view horizon a hypothesis would be framed against. One notion of "time" as a
research axis orthogonal to calendar time.

### 4.5 Time Since Event
Elapsed time measured from a discrete event (`T_event`, `T+1m`, `T+5m`, `T+30m`, `T+1h`). These are
research representations only, not a scheduling or execution construct.

---

## 5. Market State / Regime

Market State is a first-class conceptual dimension. Illustrative examples (not a taxonomy, not a
classifier):

- trending / mean-reverting
- high volatility / low volatility
- risk-on / risk-off
- liquid / illiquid
- pre-event / post-event

Key idea preserved: **the same strategy relationship may behave differently conditional on market
state.** No regime classifier or production code is created here.

---

## 6. Liquidity

Liquidity is a first-class research dimension. Concepts:

- spread
- depth
- volume
- turnover
- market impact
- liquidity drought
- bid/ask asymmetry
- opening liquidity
- closing liquidity

Conceptual distinction preserved: **observed price ≠ necessarily tradable price.** Price observation
and executable price can diverge under thin conditions; this is a research consideration, not an
execution implementation.

---

## 7. Market Microstructure

Concepts:

- bid / ask
- spread
- queue
- depth
- trade direction
- order imbalance
- price impact
- execution

Relevance noted especially for short-horizon research. No microstructure feature implementation is
added.

---

## 8. Event Time

Event Time is a first-class concept. Illustrative event classes:

- macro releases
- earnings
- index rebalances
- expirations
- dividends
- corporate actions
- index inclusion / exclusion
- auctions
- fixings

Temporal framing:

```text
event → elapsed time since event → liquidity / participation → price behavior
```

Example conceptual structure (`T_event`, `T+1m`, `T+5m`, `T+30m`, `T+1h`) is a research
representation, not a feature-bucket spec.

---

## 9. Price Discovery

### 9.1 Information Flow

Preserved flow:

```text
Known information → Information arrival → Market reaction → Price discovery → New equilibrium
```

Look-ahead bias is explicitly flagged as a major research risk for anything event- or
information-anchored.

### 9.2 Price Discovery vs Price Movement

Preserved distinction: **price movement does not automatically imply new information.** A price move
may reflect any of:

- information
- liquidity conditions
- order flow
- forced rebalancing
- liquidation
- auction mechanics
- other market mechanics

No mechanism is claimed to be an alpha source.

---

## 10. Cross-Asset / Relative Information

Conceptual domain:

- equity / rates / FX / commodities / volatility
- spreads
- relative strength
- correlation
- lead-lag
- cross-market transmission

Core conceptual statement preserved: **information may exist in relationships *between* assets
rather than within a single asset's price series.** No cross-asset features are created here.

---

## 11. Multi-Scale / Fractal-Like Behavior

Distinctions preserved:

- multi-scale behavior
- scale-dependent behavior
- fractal-like behavior
- perfect mathematical fractality

**Explicit statement: price is not assumed to be a perfect fractal.** A more defensible research
framing is:

> Does price behavior exhibit statistically stable scale-dependent structure across multiple
> horizons?

Potential scales discussed (illustrative):

- 1 minute · 5 minute · 1 hour · 4 hour · 1 day · 1 week

Potential scale-dependent observables (illustrative):

- return distribution · volatility · autocorrelation · volume · drawdown · liquidity

---

## 12. Causality

Preserved distinction:

```text
correlation ≠ predictive relationship ≠ causal mechanism
```

The ontology encourages ACASH to distinguish correlation, prediction, causal hypothesis, and
mechanism in every candidate story. No causal model is introduced here.

---

## 13. Non-Stationarity

Preserved concepts:

- structural breaks
- regime changes
- relationship decay
- half-life
- parameter stability
- temporal robustness
- market adaptation

**Explicit statement: discovered relationships should not be assumed stationary indefinitely.**

---

## 14. Reflexivity / Feedback

Preserved conceptual loop:

```text
Market → Participants observe → Participants adapt → Market changes
       → previously observed relationship may weaken
```

Reflexivity is **not** claimed to be a trading signal.

---

## 15. Research Questions

The following are preserved **as research questions only. They are NOT registered hypotheses.**

### 15.1 Time / Session Research Question

> Does market behavior exhibit statistically significant and economically meaningful conditional
> dependence on time-of-day / session state after controlling for volatility, liquidity, market
> regime, and multiple testing?

### 15.2 Conceptual Null / Alternative Framing

- **H0 (conceptual):** Return distribution is invariant to session / time-of-day.
- **H1 (conceptual):** Return / volatility / liquidity behavior depends systematically on
  session / time state.

These are research-question framings, not registered hypotheses, and carry no admission or
selection authority.

### 15.3 Time vs Price Framing

> Time is at least as fundamental as Price

is a **conceptual framing**, not a universal empirical claim that Time > Price. The ontology states:

- Price is an **observation / output** of market interaction.
- Time provides **contextual conditioning** for interpreting price behavior.
- A useful question is often *"How does price behavior change conditional on WHEN?"* rather than only
  *"Where will price go?"*

This framing is not promoted into an ACASH doctrine.

---

## 16. Falsification Orientation

Three conceptual research principles preserved:

1. Time is context, not merely a feature.
2. Price is an observation of a process, not the process itself.
3. Every apparent pattern requires:
   - mechanism
   - causal / PIT validity
   - statistical validation
   - economic validation

These are conceptual research principles, **not** governance requirements or gate criteria.

The orientation is falsificationist: concepts in this ontology become ACASH-relevant only when they
are turned into falsifiable questions and tested through the existing validation layers.

---

## 17. What This Document Does NOT Authorize

- `HYP_003`, any registry write, `R1`, gate invocations, candidate authorization
- any backtest, paper-trading, live-trading, or capital event
- any `src/` change, schema change, threshold change, or gate-math change
- any `ROADMAP.md` or governance-record modification

Nothing in §15 or elsewhere grants research feature semantics (e.g. `FEATURE_SESSION = true`) or
hypothesis registration (e.g. `HYP_003 = SESSION_MOMENTUM`). Any such step requires a separate,
explicit human decision that flows through the existing governance layers.

---

## 18. Relationship to Existing ACASH Governance

Layered model:

```text
Research Ontology (this document — NON-NORMATIVE, no authority)
        ↓
Research Question
        ↓
Registered Hypothesis
        ↓
Validation
        ↓
Qualification
        ↓
Strategy Admission
```

The discussion captured here lives **only at the top layer**. It does not sit at, and does not
derive any authority from, any governance-bearing layer.

- `./research_doctrine.md` is the Phase 14 **research-methodology doctrine** — governance-bearing.
  This ontology is intentionally separate and must not be merged into it or read as doctrine.
- `./research_candidates.md` and the `candidates/` records are **candidate-bearing**.
- The Phase 13/14 gate records and `D1`–`D9` decision records are **decision-bearing**.

This document is **not** a source of authority for existing governance and is **not** an amendment
to any of the above.