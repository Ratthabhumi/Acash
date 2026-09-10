# ACASH — Architecture Direction: Asset/Market-Agnostic Research (PROPOSAL)

**Document:** `docs/architecture/asset_market_agnostic_research_direction.md`  
**Status:** `[PROPOSAL]` — Architecture Direction (Documentation Only)  
**Scope:** Research architecture direction; strategy/market separation concept; conceptual market-domain model; future abstraction outline.  
**Related:** [`docs/DECISIONS.md`](../DECISIONS.md) ADR-020, ADR-021, ADR-023, ADR-024, ADR-025; [`multi_broker_multi_asset_decision.md`](multi_broker_multi_asset_decision.md); [`market_adaptive_strategy_governance.md`](market_adaptive_strategy_governance.md); [`execution_architecture.md`](execution_architecture.md); [`docs/ROADMAP.md`](../ROADMAP.md); Phase 14 master research architecture; Phase 13 execution infrastructure.  
**Date:** 2026-09-08  

---

## 0. Status & Binding Scope

This document records an **architecture direction** that has NOT been ratified as a governance decision.

- `[PROPOSAL]` **Architecture Direction — Asset/Market-Agnostic Research**.
- **NOT** a human-ratified governance decision.
- Does **NOT** authorize implementation.
- Does **NOT** change the current roadmap (`docs/ROADMAP.md`).
- Does **NOT** select ES/NQ as an approved trading universe.
- Does **NOT** remove S&P 500 / S&P 1500 from future scope.
- Does **NOT** change **F-1** (research candidate `proposal_cand_flow_calendar_rebalance_001.md`).
- Does **NOT** create a new hypothesis (`HYP_003` remains absent), invoke any Gate, or start R1.
- Does **NOT** authorize Phase 14 runtime implementation.
- Contains **no** invented asset priorities, performance claims, profitability claims, liquidity thresholds, risk limits, leverage rules, execution assumptions, market-data requirements, broker requirements, or implementation timelines.

**Classification legend used throughout:** `[EXISTING]` = established in current ACASH documentation; `[INFERENCE]` = reasoned implication not yet documented; `[PROPOSAL]` = candidate direction for human ratification; `[UNRESOLVED]` = open human decision.

---

## 1. Purpose (A)

- `[EXISTING]` ADR-021 establishes that ACASH Core is **not** a Forex bot, not a broker client, and not coupled to the first integrated venue or asset class. ADR-024 establishes that ACASH Core is **not** an intraday/swing/scalping bot; trading style, holding period, and entry mechanics are strategy-layer properties, not platform identity.
- `[PROPOSAL]` This direction extends that same decoupling principle to the **research surface**: ACASH should not be architecturally defined as an "S&P 500 trading system" or any single-instrument system.
- `[PROPOSAL]` ACASH should be treated as an **asset/market-agnostic Research + Trading Engine**. The Research Engine studies different market structures and selects the market/instrument appropriate to a given research hypothesis, rather than a hypothesis being fitted to a pre-chosen market.
- `[INFERENCE]` Keeping identity at the engine level (not the market level) preserves the option to research wherever evidence leads and avoids a premature single-market lock-in at the foundational architecture layer.

---

## 2. Architectural Principle (B)

> **"Strategy chooses the appropriate market; architecture does not define ACASH as one market."**

- `[EXISTING]` Foundation: ADR-021 (asset-class agnostic core), ADR-024 (strategy-agnostic core; styles/horizons are strategy-layer), `market_adaptive_strategy_governance.md` §Flexible Asset (conceptually asset-agnostic: FX, Precious Metals, Commodities, Equities, ETFs, Futures, Options, Digital Assets; each asset class requires independent data pipelines, risk models, execution adapters, and formal certification), `execution_architecture.md` (ACASH Core is asset-agnostic and broker-agnostic).
- `[PROPOSAL]` Apply the same principle explicitly at research time: a research candidate declares its compatible market structure, timeframe, session model, costs, and execution constraints; the engine does not presume a single market.
- `[INFERENCE]` This does **NOT** authorize building a dynamic strategy-selection engine. It is an architectural direction only; any such engine remains a deferred decision (see §9).

---

## 3. Market-Domain Model (C)

`[PROPOSAL]` Conceptual / proposed research universe. **This is NOT an approved trading universe.**

```
                        ACASH Research Engine
                                  |
     +----------------------------+----------------------------+
     |                            |                            |
  Futures                       Crypto                     Equities
     +-----+-----+-----+           +-----+-----+              |  +-- S&P 500
     |     |     |     |           |     |     |              +--|  or
     ES    NQ    GC    CL         BTC    ETH  (etc.)             +-- S&P 1500
   (proposed  (future  (future
   candidate  research candidate)
   research   domains —
   environment)  not prioritized)
```

- `[PROPOSAL]` Potential research domains include: Futures (ES, NQ, GC, CL); Crypto (BTC, ETH); Equities (S&P 500 / S&P 1500).
- `[PROPOSAL]` ES/NQ may be useful early research environments because of liquidity and comparatively clean execution characteristics — proposed candidate research environments, **not** a human-approved market priority.
- `[PROPOSAL]` S&P 500 / S&P 1500 equities remain a future research domain — especially cross-sectional, swing, and event-driven research — rather than being removed from ACASH scope. `[EXISTING]` Note: the F-1 research candidate already lists "S&P Composite 1500; S&P 500; S&P MidCap 400; S&P SmallCap 600" as an Index Family under its hypothesis-frozen scope; this direction does not modify that candidate.
- `[EXISTING]` ES/NQ are already referenced as a futures-market-microstructure research reference architecture in ADR-020 and `docs/proposals/phase_3_microstructure.md` (CME ES/NQ reference). This direction consolidates that reference into a broader market-agnostic framing; it does not elevate ES/NQ to an approved universe.

---

## 4. Research-Horizon Neutrality (D)

- `[EXISTING]` ADR-024: holding period and style are strategy-layer properties, not platform identity; "Current system alignment with Swing/Medium horizon is an initial baseline, not an architectural lock-in."
- `[PROPOSAL]` Intraday and swing are both valid research horizons. The architecture must **not** assume swing trading is inherently more profitable than intraday trading.
- `[INFERENCE]` Horizon fit is an empirical, per-hypothesis question evaluated by the existing research pipeline, not a platform-level axiom.

---

## 5. Strategy/Market Separation (E)

- `[PROPOSAL]` A strategy should **declare** its compatible market structure, timeframe (horizon), session model, cost assumptions, and execution constraints. The core architecture should not hard-code one asset class as the identity of ACASH.
- `[EXISTING]` Supporting separation already established: ADR-024 (Strategy ≠ Authority; Signal ≠ Order; Target Position ≠ Execution); Phase 23 (Strategy Layer decoupled from ACASH Core; Execution Infrastructure decoupled from Strategy); Phase 17 (strategy admission/catalog as a distinct layer); Phase 13 (execution/paper-validation infrastructure independent of any particular strategy).
- `[INFERENCE]` A strategy's declared market compatibility is a candidate property to be expressed at research/candidate/admission time; the precise mechanism is a future abstraction (see §6) and is not specified here.

---

## 6. Future Asset/Market Abstraction (F)

`[PROPOSAL]` Future architecture concept only. **No schema, DTO, API, or code is defined or implied by this section.** `[INFERENCE]` An eventual abstraction may need to represent, per research domain:

- asset class
- instrument identity
- venue
- trading/session calendar
- price/volume representation
- tick/contract characteristics (where applicable)
- corporate actions (where applicable)
- funding / borrow / margin concepts (where applicable)
- market-specific execution constraints

`[EXISTING]` Any future design must respect the canonical data domain separation established in ADR-020 (distinct Trades and Order Book domains alongside OHLCV Bars) and the requirement in `market_adaptive_strategy_governance.md` that each asset class carry its own data pipelines, risk models, execution adapters, and formal certification. This section intentionally specifies **what** may need representation later, never **how**.

---

## 7. Research Workflow (G)

`[PROPOSAL]` Conceptual workflow only — **not** a new Phase hierarchy, not Phase 14A/14B/14C, not an approved process:

```
Learn existing knowledge
        ↓
Understand mechanism
        ↓
Reproduce / critically test
        ↓
Extract reusable research knowledge
        ↓
Formulate hypothesis
        ↓
Validate
        ↓
Select/target compatible market/instrument
        ↓
Paper / execution validation
```

- `[PROPOSAL]` Market/instrument selection occurs **after** mechanism understanding and validation, as an output of research — not as a fixed input.
- `[EXISTING]` The validation and paper/execution steps align with the existing governance pipeline (formal hypothesis pipeline → Phase 13 paper/execution). This document does not redefine those phase boundaries.

---

## 8. Relationship to Existing Phases (H)

`[EXISTING]` Compatibility only; no phase boundary is redefined.

| Phase | Role | Relationship to this direction |
|---|---|---|
| Phase 13 | General execution / paper-validation infrastructure (not TSMOM-bound) | `[EXISTING]` Hosts whatever strategy passes admission; independent of any single strategy's fate. `[PROPOSAL]` Execution infrastructure remains market-agnostic in principle. |
| Phase 14 | AI Quantitative Research Layer (plan approved at plan level; runtime locked until Phase 13 Steps 5–9 certified) | `[EXISTING]` Research over existing knowledge, mechanisms, external claims, replication/falsification, anomalies, and hypothesis discovery. `[PROPOSAL]` Research Engine may study different market structures; selecting the market for a hypothesis is a research concern. No change to Phase 14 lock state. |
| Phase 17 | Strategy admission / Sovereign Strategy Catalog | `[EXISTING]` Admission layer consumes research+validation evidence. `[PROPOSAL]` A strategy's declared market/instrument compatibility would be expressed here at admission time. No change to admission rules. |
| Future multi-strategy (Phase 22 direction) | Portfolio / multi-strategy orchestration | `[EXISTING]` Multi-strategy hosting is a future capability; single-market realities do not block it, and this direction does not build it. |
| Phase 18 / 23 | Tournament / strategy-agnostic core | `[EXISTING]` Untouched. This direction does not alter Phase 18 tournament governance or Phase 23 records. |

---

## 9. Deferred Decisions (I)

`[UNRESOLVED]` — Open for human ratification; **none default to a value here**:

1. Initial research market priority (which market, if any, is first).
2. Exact asset universe definition.
3. Whether ES/NQ should actually be the first research environments.
4. Data providers.
5. Venue / broker.
6. Contract specifications (per instrument).
7. Capital / risk policy (per market).
8. Implementation architecture for the abstraction in §6.
9. Multi-market concurrency approach.

---

## 10. Governance Impact (J)

> **"No governance change."**

- F-1: **unchanged**.
- `HYP_003`: **absent**.
- Research Re-Inception Gate: **not invoked**.
- R1: **not started**.
- Trading: **remains LOCKED**.
- Capital: **remains $0.00**.
- No data access, backtest, optimization, execution, commit, or push is authorized or performed by this document.

---

## 11. Next Decision Surface (K)

Short list of decisions a human may ratify later (none are assumed):

1. Ratify or reject the market-agnostic research direction.
2. Approve an initial research market priority (or explicitly "no priority yet").
3. Designate ES/NQ as candidate early research environments (or not).
4. Confirm S&P 500 / S&P 1500 equities remain future research scope.
5. Decide when (if ever) to specify the §6 abstraction and where it lives.
6. Decide when (if ever) to run the §7 workflow in a pilot form.

---

## 12. Contradiction & Source Discipline

- `[EXISTING]` Where this document makes an affirmative statement about existing ACASH architecture, the source is cited (ADR-020/021/023/024/025, `market_adaptive_strategy_governance.md`, `execution_architecture.md`, `ROADMAP.md`, F-1 candidate).
- `[PROPOSAL]` / `[INFERENCE]` / `[UNRESOLVED]` labels are applied to every statement that is not already established.
- No statement in this document converts a discussion or recommendation into an `[EXISTING]` fact.
- This document does not modify `ROADMAP.md`, F-1, Phase 13 certification status, Phase 14 governance freezes, or Phase 17/18/22 decisions.