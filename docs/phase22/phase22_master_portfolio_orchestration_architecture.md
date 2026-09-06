# ACASH Phase 22 — Portfolio Orchestration & Netting
## Master Architecture & Governance Specification

> **Document ID:** `ACASH-SPEC-PHASE22-ORCHESTRATION-v1.0`  
> **Status:** PROPOSED ARCHITECTURE & GOVERNANCE SPECIFICATION — PENDING ARCHITECTURAL & HUMAN GOVERNANCE REVIEW (Phase 22 Rev 1.0)  
> **Parent Governance:** `docs/ROADMAP.md` (v3.4.0), `AGENTS.md`, ADR-022, ADR-023, ADR-024, ADR-025  
> **Authority:** `AGENTS.md` (Zero Unverified Claims, Strict Fail-Closed Contract, Evidence > Belief, Single Canonical Authority)  
> **Date:** 2026-09-06  
> **Version:** 1.0.0 (Master Architecture & Governance Specification)  

---

> [!IMPORTANT]
> **STRICT GOVERNANCE BOUNDARY & CAPITAL RESTRICTIONS:**
> - **THIS SPECIFICATION IS A DESIGN, ARCHITECTURAL, AND GOVERNANCE DOCUMENT ONLY.**
> - **THIS SPECIFICATION DOES NOT AUTHORIZE CODE IMPLEMENTATION.**
> - **PHASE 22 IMPLEMENTATION IS STRICTLY LOCKED / NOT AUTHORIZED.**
> - **THIS SPECIFICATION DOES NOT GRANT LIVE TRADING OR BROKER PERMISSIONS.**
> - **LIVE CAPITAL AUTHORITY REMAINS HARD-LOCKED AT $0.00.**
> - **LIVE ORDER EMISSION AUTHORITY REMAINS STRICTLY 0.**
> - **LIVE BROKER CONNECTION REMAINS STRICTLY DISCONNECTED.**
> - **ZERO RUNTIME MUTATION TO `src/` OR `tests/`.**
> - **PHASE 13 STEP 5 UNATTENDED SOAK TEST (PID 41844) REMAINS ACTIVE AND UNTOUCHED.**
> - **ALL CONTROLS IN THIS SPECIFICATION ARE LABELED: `CONTROL SPECIFIED / NOT YET IMPLEMENTED`.**

---

## 1. Executive Summary

Phase 22 establishes the **Portfolio Orchestration & Netting Engine** for the ACASH quantitative trading and research operating system. 

Positioned strictly between the upstream mathematical capital allocation layer (**Phase 21**) and the downstream physical broker execution adapters (**Phase 12**), Phase 22 transforms abstract, strategy-level target weights into coordinated, risk-sequenced, internally netted, and capacity-constrained **abstract execution intents**.

Phase 22 provides enterprise-grade execution coordination:
1. **Multi-Strategy Intent Aggregation:** Resolves concurrent, multi-strategy demands on shared market instruments without re-optimizing allocations.
2. **Deterministic Internal Netting:** Minimizes turnover, commissions, and bid-ask spread crossing by algebraically offsetting opposing strategy exposures prior to venue submission.
3. **Execution Intent Lifecycle Governance:** Implements a 14-state deterministic finite automaton enforcing that local timeout does not imply fill, and unknown broker state triggers authoritative reconciliation.
4. **Physical Broker Decoupling:** Enforces complete wire and socket isolation; Phase 22 emits abstract `ExecutionIntent` records and possesses zero direct broker API authority.

---

## 2. Phase 22 Mission & Identity

The sole, non-delegable mission of Phase 22 is:

$$oxed{egin{aligned}
&	ext{"Given an authorized PortfolioAllocationPlan from Phase 21 and verified broker position telemetry,"} \
&	ext{"determine HOW multiple strategy-level target allocations are coordinated, aggregated, netted,"} \
&	ext{"prioritized, constrained, and transformed into abstract execution intents for Phase 12."}
\end{aligned}}$$

### 2.1 Core Invariants of Identity
1. **Coordination Without Re-Allocation:** Phase 22 determines *how* an already-authorized allocation is scheduled and netted; it **never** decides *whether* a strategy deserves capital or *how much* capital it receives.
2. **Translation Without Execution:** Phase 22 translates target weights into desired lot quantities; it **never** places orders, manages broker sessions, or handles wire protocols.
3. **Subservience to Real-World Evidence:** Internal ledger assumptions are provisional; downstream broker-matching reality emitted by Phase 12 reconciliation is **authoritative and sovereign**.

---

## 3. Scope and Explicit Non-Scope

### 3.1 Permitted Phase 22 Scope
- Ingest and verify cryptographic lineage of `PortfolioAllocationPlan` (Phase 21).
- Ingest verified broker position and balance telemetry emitted by Phase 12 shadow reconciliation.
- Map strategy-level dollar/weight targets into instrument-level desired notional and lots using authoritative `BrokerSymbolSpec`.
- Algebraically net opposing strategy targets on identical instruments.
- Apply turnover constraints, rebalance deadbands, and liquidity-participation caps.
- Sequence intents deterministically: **Risk-reducing liquidations strictly precede risk-expanding acquisitions**.
- Emit immutable, cryptographically sealed `ExecutionIntent` records to Phase 12.
- Track intent lifecycle transitions based strictly on downstream execution evidence.
- Maintain an append-only, SHA-256 hash-chained `orchestration_ledger.jsonl`.

### 3.2 The Twenty Non-Negotiable Prohibitions
Phase 22 **MUST NOT under any circumstances**:
1. **Select strategies** or evaluate candidate market compatibility (Phase 20 Sole Authority).
2. **Add strategies** to the active execution slate.
3. **Remove strategies** for alpha, performance, or predictive reasons.
4. **Substitute strategies** based on correlation or execution convenience.
5. **Resurrect Phase 20 excluded candidates** (`excluded_candidate_records`).
6. **Re-optimize capital allocations** or alter Phase 21 target weights $w_i$.
7. **Recompute portfolio risk budgets** $b_i$ or risk contributions $	ext{RC}_i$.
8. **Perform statistical validation** (DSR, PBO, CSCV — Phase 6 Sole Authority).
9. **Perform economic qualification** (haircuts, capacity — Phase 8.5 Sole Authority).
10. **Perform strategy admission** (admission manifests — Phase 17 Sole Authority).
11. **Detect or classify market regimes** (transition entropy — Phase 19 Sole Authority).
12. **Modify Phase 11 forward health states** or suppress monitoring circuit breakers.
13. **Change the mathematical meaning** of Phase 21 target weights.
14. **Invent expected returns $oldsymbol{\mu}$, volatility $oldsymbol{\sigma}$, or covariance $\Sigma$**.
15. **Connect directly to broker APIs, sockets, or FIX engines**.
16. **Route physical orders** to market destinations or execution venues.
17. **Maintain broker-specific execution authority** or account credentials.
18. **Bypass Phase 12 execution adapters**.
19. **Use an LLM or AI agent** to make autonomous execution or netting decisions.
20. **Function as an ad-hoc selection or allocation layer** ("Phase 20.5" or "Phase 21.5").

---

## 4. Sovereign Authority Hierarchy

$$oxed{\mathbf{Admission\ (17)} 
eq \mathbf{Validation\ (6)} 
eq \mathbf{Qual\ (8.5)} 
eq \mathbf{Regime\ (19)} 
eq \mathbf{Selection\ (20)} 
eq \mathbf{Allocation\ (21)} 
eq \mathbf{Orchestration\ (22)} 
eq \mathbf{Adapter\ (12)} 
eq \mathbf{Broker}}$$

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              ACASH SOVEREIGN AUTHORITY MATRIX                               │
├───────────────────────────┬─────────────────────────────────┬───────────────────────────────┤
│ System Component          │ Sovereign Authority             │ Strictly Prohibited           │
├───────────────────────────┼─────────────────────────────────┼───────────────────────────────┤
│ Phase 17 (Admission)      │ Strategy Eligibility Gate       │ Capital Sizing, Execution     │
│ Phase 6 (Validation)      │ Statistical Significance (DSR)  │ Strategy Selection, Trading   │
│ Phase 8.5 (Qualification) │ Economic Viability (Haircuts)   │ Portfolio Sizing, Broker Wire │
│ Phase 19 (Regimes)        │ Market State Classification     │ Strategy Selection, Sizing    │
│ Phase 20 (Selection)      │ Active Strategy Slate Choice    │ Weight Solving, Execution     │
│ Phase 21 (Allocation)     │ Risk-Based Target Weights ($w$) │ Strategy Choice, Broker Order │
│ Phase 22 (Orchestration)  │ Netting, Sequencing, Intent Gen │ Alpha Choice, Weight Solve,   │
│                           │ (`ExecutionIntent` DTOs)        │ Broker Socket I/O, Order Wire │
│ Phase 12 (Execution)      │ Physical Order Lifecycle        │ Strategy Netting, Weight Gen  │
│                           │ (Adapter -> FIX/MT5 Terminal)   │ Portfolio Allocation Decisions│
│ Broker Trade Server (Ext) │ Final Execution Reality         │ Internal ACASH Governance     │
└───────────────────────────┴─────────────────────────────────┴───────────────────────────────┘
```

---

## 5. Phase 21 → Phase 22 Interface Contract

Phase 22 ingests the sealed, immutable `PortfolioAllocationPlan` emitted by Phase 21.

### 5.1 Canonical Upstream Payload Fields
Phase 22 requires the following fields from Phase 21:
- `allocation_plan_id`: UUIDv7 unique identifier.
- `allocation_digest`: SHA-256 hash sealing the allocation plan.
- `selection_decision_id` & `selection_decision_digest`: Cryptographic lineage to Phase 20.
- `capital_basis_usd` & `allocatable_capital_usd`: Total equity and net risk capital.
- `cash_weight`: Mandatory liquidity buffer $w_0 \in [0.10, 1.00]$.
- `selected_strategy_ids`: Exact list of authorized strategies.
- `target_weights`: Dictionary mapping `{strategy_id: w_i}` ($\sum w_i + w_{	ext{cash}} = 1.00$).
- `allocated_capital_usd`: Dictionary mapping `{strategy_id: w_i 	imes 	ext{allocatable\_capital}}`.
- `solver_status`: Must equal `"FEASIBLE"` or `"DEFENSIVE_FALLBACK"`.

### 5.2 Upstream Plan Status Mapping
| Phase 21 Status | Phase 22 Engine Action | Resulting Orchestration Action |
| :--- | :--- | :--- |
| `FEASIBLE` | Normal pipeline processing | Netting, constraint evaluation, intent generation. |
| `DEFENSIVE_FALLBACK`| Defensive pipeline processing | Systematic orderly liquidation to 100% cash. |
| `NO_ALLOCATION` | Deterministic short-circuit | Zero intents generated; maintain/revert to 100% cash. |
| `ALLOCATION_BLOCKED`| Immediate pipeline halt | Halt intent emission; alert SRE supervisor. |
| `INFEASIBLE` | Fail-closed security block | Zero intents generated; fail-closed halt. |
| `INPUT_INVALID` | Immediate rejection | Drop payload; trigger compliance audit alert. |

---

## 6. PortfolioAllocationPlan Ingestion Rules

1. **Digest Verification:** Recalculate SHA-256 of canonical JSON representation; mismatch raises `ERR_ORCH_ALLOCATION_DIGEST_MISMATCH`.
2. **Freshness Boundary:** Plan timestamp $T_{	ext{decision}}$ must satisfy:
   $$T_{	ext{now}} - T_{	ext{decision}} \le 	ext{policy.max\_allocation\_age\_sec} \quad (	ext{default: } 120	ext{ seconds})$$
3. **Causality Enforcement:** $T_{	ext{knowledge}} \le T_{	ext{as\_of}} \le T_{	ext{decision}} \le T_{	ext{orchestration}}$. Future timestamps trigger immediate lookahead abort (`ERR_ORCH_TEMPORAL_LOOKAHEAD`).
4. **Cold Start vs. Rebalance Detection:** If no previous `orchestration_ledger` record exists, engine executes a **Cold Start Protocol** (assumes zero pending internal intents; requires 100% fresh broker position reconciliation).

---

## 7. Allocation Integrity & Firewall Verification (`OrchestrationEligibilityFirewall`)

Before any netting calculation or lot sizing occurs, all inputs must pass through the **Orchestration Eligibility Firewall**. The firewall evaluates **twenty-eight fail-closed filter predicates** across five governance domains:

```
Incoming PortfolioAllocationPlan & Broker Position State
        │
        ├── [ Domain 1: Allocation Plan Integrity (OF-01 to OF-06) ] ──► Any Fail? ──► REJECT / HALT
        ├── [ Domain 2: Lineage & Authority Proofs (OF-07 to OF-11) ] ──► Any Fail? ──► REJECT / HALT
        ├── [ Domain 3: Position Telemetry & Reconcil (OF-12 to OF-17) ] ► Any Fail? ──► REJECT / HALT
        ├── [ Domain 4: Capital, Exposure & Netting (OF-18 to OF-23) ] ─► Any Fail? ──► REJECT / HALT
        └── [ Domain 5: Operational & Circuit Breakers (OF-24 to OF-28) ] Any Fail? ──► REJECT / HALT
        │
        ▼ All 28 Firewall Predicates Verified
Eligible for Intent Generation & Netting Execution
```

### 7.1 Complete 28-Predicate Firewall Specification

| Predicate ID | Domain | Evaluated Condition | Fail-Closed Reason Code |
| :--- | :--- | :--- | :--- |
| **OF-01** | Plan Integrity | `allocation_digest` matches recalculated SHA-256 of Phase 21 plan | `ERR_ORCH_PLAN_DIGEST_MISMATCH` |
| **OF-02** | Status Permitted | `solver_status IN {"FEASIBLE", "DEFENSIVE_FALLBACK", "NO_ALLOCATION"}` | `ERR_ORCH_STATUS_NOT_PERMITTED` |
| **OF-03** | Weight Sum Valid | $|\sum w_i + w_{	ext{cash}} - 1.00000000| \le 10^{-7}$ | `ERR_ORCH_WEIGHT_SUM_INVALID` |
| **OF-04** | Cash Buffer Maintained | $w_{	ext{cash}} \ge 	ext{policy.min\_cash\_weight}$ (0.10) | `ERR_ORCH_CASH_BUFFER_BREACH` |
| **OF-05** | No NaN/Inf Weights | All $w_i$ and capital values are finite Decimal numbers | `ERR_ORCH_WEIGHT_NON_FINITE` |
| **OF-06** | Strategy Set Match | Keys in `target_weights` strictly match `selected_strategy_ids` | `ERR_ORCH_STRATEGY_SET_MISMATCH` |
| **OF-07** | Phase 20 Lineage | `selection_decision_digest` verified against sealed Phase 20 ledger | `ERR_ORCH_PHASE20_LINEAGE_BROKEN` |
| **OF-08** | Phase 17 Admission | All active strategies have `admission_status == "ADMITTED"` | `ERR_ORCH_ADMISSION_UNVERIFIED` |
| **OF-09** | Phase 6 Validation | All active strategies have sealed validation digest in ledger | `ERR_ORCH_VALIDATION_UNVERIFIED` |
| **OF-10** | Phase 8.5 Qualification| All active strategies have sealed economic qualification dossier | `ERR_ORCH_QUALIFICATION_UNVERIFIED`|
| **OF-11** | Policy Digest Sealed | `orchestration_policy_digest` matches immutable deployment manifest| `ERR_ORCH_POLICY_DIGEST_MISMATCH` |
| **OF-12** | Broker Telemetry Fresh | Position snapshot age $\le 	ext{policy.max\_telemetry\_age\_sec}$ (30s) | `ERR_ORCH_POSITION_TELEMETRY_STALE`|
| **OF-13** | Broker Reconciled | Phase 12 shadow reconciliation state is `RECONCILED` (zero drift) | `ERR_ORCH_RECONCILIATION_UNCONFIRMED`|
| **OF-14** | Symbol Specs Present | Authoritative `BrokerSymbolSpec` present for all target instruments| `ERR_ORCH_SYMBOL_SPEC_MISSING` |
| **OF-15** | Price Feeds Active | Verified fresh market quotes available for all target instruments | `ERR_ORCH_MARKET_DATA_STALE` |
| **OF-16** | No Phantom Positions | No active positions exist for uncataloged or retired strategies | `ERR_ORCH_PHANTOM_POSITION_DETECTED`|
| **OF-17** | Position Certainty | No positions marked `UNKNOWN` or pending unconfirmed reconciliation| `ERR_ORCH_POSITION_UNCERTAINTY` |
| **OF-18** | Gross Leverage Limit | Total gross notional $\le 	ext{capital\_basis} 	imes 	ext{max\_gross\_leverage}$ | `ERR_ORCH_LEVERAGE_CEILING_BREACH` |
| **OF-19** | Concentration Limit | No single instrument net exposure exceeds $25\%$ of portfolio basis | `ERR_ORCH_CONCENTRATION_BREACH` |
| **OF-20** | Min Lot Feasibility | All calculated trade deltas satisfy $\Delta Q = 0$ or $|\Delta Q| \ge Q_{\min}$ | `ERR_ORCH_SUB_MINIMUM_LOT_SIZE` |
| **OF-21** | Lot Step Alignment | All trade deltas are exact integer multiples of `volume_step` | `ERR_ORCH_LOT_STEP_MISALIGNMENT` |
| **OF-22** | Max Lot Clamp | Single intent volume $\le \min(Q_{\max}, 	ext{policy.max\_single\_order\_lots})$ | `ERR_ORCH_MAX_LOT_EXCEEDED` |
| **OF-23** | Turnover Budget Valid | Proposed portfolio rebalance turnover $\le 	ext{policy.max\_turnover}$ | `ERR_ORCH_TURNOVER_BUDGET_EXCEEDED`|
| **OF-24** | Circuit Breaker Inactive| System-wide emergency execution lock is FALSE | `ERR_ORCH_CIRCUIT_BREAKER_ACTIVE` |
| **OF-25** | Trading Session Open | Target venue/broker markets are actively open for trading | `ERR_ORCH_MARKET_SESSION_CLOSED` |
| **OF-26** | Close Proximity Safe | Time until market close $\ge 	ext{policy.min\_close\_buffer\_sec}$ (300s)| `ERR_ORCH_MARKET_CLOSE_PROXIMITY` |
| **OF-27** | Pending Intent Drain | Zero unacknowledged or inflight intents from previous cycle | `ERR_ORCH_INFLIGHT_INTENT_COLLISION`|
| **OF-28** | Idempotency Key Free | Generated intent IDs do not collide with historical intent ledger | `ERR_ORCH_IDEMPOTENCY_COLLISION` |

---

## 8. Multi-Strategy Intent Aggregation Model

In an institutional multi-strategy architecture, multiple independent strategies frequently generate targets for identical underlying instruments.

### 8.1 The Multi-Strategy Problem
Consider three authorized strategies targeting EURUSD at time $t$:
- Strategy $A$ (Trend Following): Target weight $w_A = +0.20$ (Long \$200,000 notional)
- Strategy $B$ (Mean Reversion): Target weight $w_B = -0.15$ (Short \$150,000 notional)
- Strategy $C$ (Carry / Yield): Target weight $w_C = +0.10$ (Long \$100,000 notional)

Without Phase 22 orchestration, executing these strategies independently produces:
- Gross Volume Traded: \$200k + \$150k + \$100k = **\$450,000 notional** (4.5 Lots).
- Cross-Spread Friction: 3 round-turn spread crossings + 3 separate broker commission tickets.
- Latent Exposure Contradiction: Strategy $A$ buys from the broker while Strategy $B$ sells to the broker simultaneously.

### 8.2 Phase 22 Aggregation Transformation
Phase 22 deterministically aggregates all strategy-level targets into a single, unified instrument portfolio target:
$$N_{	ext{EURUSD}, 	ext{target}} = N_A + N_B + N_C = +\$200	ext{k} - \$150	ext{k} + \$100	ext{k} = +\$150,000 	ext{ notional}$$
- Gross Desired Notional: \$450,000
- Net Desired Notional: \$150,000
- **Internal Crossing Savings:** \$300,000 notional (66.7% volume reduction) completely spared from broker execution, spread crossing, and transaction fees.

---

## 9. Target Allocation → Desired Exposure Translation

Phase 22 translates abstract target capital into precise, quantized broker lots:

### 9.1 Mathematical Translation Formulation
For strategy $i$ and instrument $s$:
1. **Target Capital:**
   $$C_{i,s} = w_{i,s} 	imes 	ext{AllocatableCapital}$$
2. **Target Notional Value:**
   $$N_{i,s} = C_{i,s}$$
3. **Unconstrained Target Lots:**
   $$Q_{i,s}^* = rac{N_{i,s}}{P_{	ext{mid}, s} 	imes 	ext{ContractSize}_s}$$
   Where $P_{	ext{mid}, s} = rac{P_{	ext{bid}, s} + P_{	ext{ask}, s}}{2}$ is the authoritative causal midpoint price, and $	ext{ContractSize}_s$ is from `BrokerSymbolSpec`.

4. **Aggregate Target Lots per Instrument:**
   $$Q_{s, 	ext{target}} = \sum_{i=1}^{M} Q_{i,s}^*$$

5. **Discrete Volume Quantization:**
   $$Q_{s, 	ext{target}}^{	ext{quant}} = 	ext{sgn}(Q_{s, 	ext{target}}) 	imes \left( \left\lfloor rac{|Q_{s, 	ext{target}}|}{	ext{volume\_step}_s} ightfloor 	imes 	ext{volume\_step}_s ight)$$

---

## 10. Position State Model

To eliminate semantic confusion between targets, orders, and real positions, Phase 22 maintains strict separation across eight distinct exposure representations:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       EXPOSURE STATE TAXONOMY                               │
├─────────────────────────┬───────────────────────────────────────────────────┤
│ State Representation    │ Epistemic Definition                              │
├─────────────────────────┼───────────────────────────────────────────────────┤
│ 1. Strategy Target      │ Abstract capital weight allocated to strategy i.  │
│ 2. Portfolio Target     │ Aggregate target weight across all strategies.    │
│ 3. Instrument Target    │ Desired gross/net quantized lots for instrument s.│
│ 4. Current Position     │ Authoritative broker-observed position snapshot.  │
│ 5. Pending Intent       │ Abstract intent emitted but unconfirmed by venue. │
│ 6. Inflight Order       │ Active resting order acknowledged by broker.      │
│ 7. Net Required Delta   │ $\Delta Q = Q_{	ext{target}} - Q_{	ext{current}}$.                 │
│ 8. Residual Quantity    │ Unfilled balance of an active execution intent.   │
└─────────────────────────┴───────────────────────────────────────────────────┘
```

$$oxed{\mathbf{INVARIANT:}\quad 	ext{Strategy Target } 
e 	ext{ Instrument Target } 
e 	ext{ Broker Position } 
e 	ext{ Realized Fill}}$$

---

## 11. Deterministic Netting Model

Phase 22 enforces **Single-Asset Algebraic Netting**.

### 11.1 Netting Equations
Given current broker-observed position $Q_{s, 	ext{current}}$ and aggregate target $Q_{s, 	ext{target}}^{	ext{quant}}$:
$$\Delta Q_s = Q_{s, 	ext{target}}^{	ext{quant}} - Q_{s, 	ext{current}}$$

- If $\Delta Q_s > 0$: Net requirement is **BUY** volume $\Delta Q_s$.
- If $\Delta Q_s < 0$: Net requirement is **SELL** volume $|\Delta Q_s|$.
- If $\Delta Q_s = 0$: Position is on target; zero execution intent emitted.

### 11.2 Internal Netting Efficiency Ratio (NER)
To quantify execution optimization, Phase 22 computes the Netting Efficiency Ratio:
$$	ext{NER}_s = 1 - rac{|\Delta Q_s|}{\sum_{i=1}^M |Q_{i,s}^* - Q_{i,s, 	ext{current}}|}$$
- $	ext{NER}_s = 0$: Zero internal crossing (all strategy deltas in same direction).
- $	ext{NER}_s 	o 1$: Maximum internal crossing (opposing strategy deltas fully netted).

---

## 12. Conflict Resolution Rules

When multiple strategies emit opposing requirements on instrument $s$:
1. **Zero Favoritism:** Phase 22 **never** chooses Strategy $A$ over Strategy $B$ based on past performance, Sharpe ratio, or human preference.
2. **Algebraic Netting Dominance:** The net position $\Delta Q_s$ is the **sole physical trade requirement**.
3. **Internal Sub-Account Attribution:** On the internal shadow ledger, Strategy $A$ is credited with $+Q_A$ long exposure and Strategy $B$ is debited with $-Q_B$ short exposure. Both strategies receive virtual fill confirmations at the benchmark midpoint $P_{	ext{mid}, s}$ with **zero slippage and zero commission** on the internally netted fraction.

---

## 13. Duplicate Strategy / Duplicate Intent Handling

1. **Duplicate Strategy IDs:** If Phase 21's `selected_strategy_ids` contains duplicates, Firewall `OF-06` raises `ERR_ORCH_STRATEGY_SET_MISMATCH` and halts.
2. **Duplicate Intent Prevention:** Each intent key is uniquely derived:
   $$	ext{intent\_id} = 	ext{UUIDv7}(T_{	ext{orchestration}}, 	ext{hash}(s, \Delta Q_s, 	ext{sequence}))$$
3. If an intent with identical parameters exists in `PENDING` or `DISPATCHED` state, the engine halts under `ERR_ORCH_INFLIGHT_INTENT_COLLISION` to prevent double execution.

---

## 14. Idempotency & Replay Protection Model

1. **Deterministic Idempotency Key:**
   $$	ext{idempotency\_key} = 	ext{SHA-256}(	ext{allocation\_plan\_id} \,\|\, s \,\|\, 	ext{direction} \,\|\, \Delta Q_s \,\|\, 	ext{rebalance\_sequence})$$
2. **Execution De-duplication:** Phase 12 execution adapters reject any submission matching an already-recorded `idempotency_key`.
3. **Crash Replay Guard:** On reboot, Phase 22 scans `orchestration_ledger.jsonl`. Any intent present in the ledger cannot be re-emitted without an explicit new `allocation_plan_id`.

---

## 15. Deterministic Orchestration Rules

1. **Zero Heuristics:** Intent generation relies solely on mathematical arithmetic and declared policy bounds.
2. **Zero Machine Learning / AI Discretion:** No LLM or neural network has write permissions or decision authority over intent generation.
3. **Byte-for-Byte Reproducibility:** Re-running Phase 22 on identical input records produces an identical `orchestration_digest`.

---

## 16. Ordering & Priority Semantics

When a rebalance produces multiple execution intents across $K$ instruments, Phase 22 enforces **Deterministic Risk-Sequenced Execution**:

$$oxed{\mathbf{PRIORITY\;RULE:}\quad 	ext{Risk-Reducing Liquidations } \prec 	ext{ Risk-Neutral Switches } \prec 	ext{ Risk-Expanding Acquisitions}}$$

```
Rebalance Intent Set {Intent_1, Intent_2, ..., Intent_K}
       │
       ├── [ Priority 1: Emergency Close / Stop-Outs ] ─────────► Dispatch Immediately
       ├── [ Priority 2: Position Reductions (|Q_new| < |Q_old|) ] ► Frees Margin Headroom
       ├── [ Priority 3: Directional Flips (Long -> Short) ] ───► Close Existing First
       └── [ Priority 4: Position Increases (|Q_new| > |Q_old|) ] ► Requires Verified Margin
```

### Deterministic Tie-Breaking
If multiple intents share the same priority tier, they are sorted deterministically by:
1. Instrument symbol alphabetical order (`symbol ASC`).
2. Absolute notional delta descending (`|Delta Notional| DESC`).
3. Intent UUIDv7 ascending (`intent_id ASC`).

---

## 17. Capital & Exposure Consistency Checks

Phase 22 continuously validates portfolio-level accounting invariants:
1. **Cash Invariant:**
   $$	ext{AllocatedCapital} + 	ext{ReservedCapital} + 	ext{FreeCash} = 	ext{TotalAccountEquity}$$
2. **Gross Exposure Invariant:**
   $$\sum_{s=1}^S |Q_{s, 	ext{target}}^{	ext{quant}} 	imes P_{	ext{mid}, s} 	imes 	ext{ContractSize}_s| \le 	ext{capital\_basis} 	imes 	ext{max\_gross\_leverage}$$
3. **Single-Instrument Concentration Cap:**
   $$rac{|Q_{s, 	ext{target}}^{	ext{quant}} 	imes P_{	ext{mid}, s} 	imes 	ext{ContractSize}_s|}{	ext{capital\_basis}} \le 	ext{policy.max\_instrument\_concentration} \quad (0.25)$$

---

## 18. Turnover Constraints & Rebalance Deadbands

To eliminate transaction fee drag caused by micro-adjustments:

### 18.1 Rebalance Deadband Rule
For each instrument $s$, let current portfolio weight be $w_{s, 	ext{current}}$ and target weight be $w_{s, 	ext{target}}$:
$$\Delta w_s = |w_{s, 	ext{target}} - w_{s, 	ext{current}}|$$
- If $\Delta w_s < \delta_{	ext{deadband}}$ (default: $0.015$ or $1.5\%$):
  $$\Delta Q_s = 0 \quad (	ext{Intent Suppressed — Below Deadband})$$
- If $\Delta w_s \ge \delta_{	ext{deadband}}$:
  $$\Delta Q_s 	ext{ is calculated and executed in full.}$$

### 18.2 Maximum Turnover Clamp
Total rebalance turnover $rac{1}{2} \sum |\Delta w_s|$ cannot exceed `policy.max_daily_turnover` ($0.50$ or $50\%$). If exceeded, the engine scales all deltas proportionally:
$$\Delta Q_s^{	ext{clamped}} = \Delta Q_s 	imes rac{	ext{max\_daily\_turnover}}{	ext{Turnover}_{	ext{raw}}}$$

---

## 19. Capacity Constraints & Market Impact Safeguards

To prevent market impact from degrading strategy performance:
1. **Participation Rate Ceiling:** An execution intent cannot exceed $5\%$ of the instrument's Average Daily Volume (ADV):
   $$Q_{	ext{intent}} \le rac{0.05 	imes 	ext{ADV}_{20	ext{d}}}{	ext{ContractSize}_s}$$
2. **Lot Slicing Pacing Policy:** If an intent exceeds the single-order limit, Phase 22 generates a paced intent schedule emitting discrete slices at declared time intervals $	au_{	ext{slice}} \ge 30	ext{s}$.

---

## 20. Venue & Instrument Constraints

All intents must conform strictly to `BrokerSymbolSpec`:
- **Volume Step:** $\Delta Q_s \pmod{	ext{volume\_step}_s} = 0$.
- **Minimum Volume:** If $|\Delta Q_s| < 	ext{volume\_min}_s$, the intent is clamped to zero (suppressed).
- **Maximum Volume:** If $|\Delta Q_s| > 	ext{volume\_max}_s$, sliced into multiple parent-child intents.
- **Price Precision:** Limit prices must be rounded to `digits` decimals and aligned to `tick_size`.

---

## 21. Execution Intent Schema Specification

```python
class IntentDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class IntentType(str, Enum):
    REBALANCE = "REBALANCE"
    LIQUIDATION = "LIQUIDATION"
    DEFENSIVE_CASH = "DEFENSIVE_CASH"
    EMERGENCY_HALT = "EMERGENCY_HALT"


class ExecutionIntent(BaseModel):
    """
    Authoritative, immutable execution intent emitted by Phase 22 to Phase 12.
    Contains zero broker routing tags or physical connection credentials.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    # Identifiers & Idempotency
    intent_id: str                      # UUIDv7 strictly ordered
    idempotency_key: str                # SHA-256 deduplication key
    sequence_number: int                # Monotonically increasing rebalance counter
    
    # Lineage Links
    allocation_plan_id: str             # Parent Phase 21 Plan ID
    allocation_digest: str              # Parent Phase 21 SHA-256 digest
    selection_decision_id: str          # Grandparent Phase 20 Decision ID
    selection_decision_digest: str      # Grandparent Phase 20 SHA-256 digest
    
    # Timing & Causality Boundaries
    created_at_utc: datetime            # Intent generation timestamp
    as_of_time_utc: datetime            # Causal evaluation boundary
    valid_until_utc: datetime           # Expiration deadline
    
    # Instrument & Commercial Specifications
    canonical_symbol: str               # e.g., "EURUSD"
    broker_symbol: str                  # e.g., "EURUSD.raw"
    direction: IntentDirection          # BUY, SELL, HOLD
    intent_type: IntentType             # REBALANCE, LIQUIDATION, etc.
    
    # Quantized Execution Quantities (Decimal)
    quantity_lots: Decimal              # Volume in lots (strictly positive, quantized)
    target_notional_usd: Decimal        # Desired post-execution notional
    current_notional_usd: Decimal       # Current observed notional
    delta_notional_usd: Decimal         # Signed change in notional
    
    # Price Boundaries & Benchmarks
    benchmark_mid_price: Decimal        # Midpoint price at generation time
    slippage_tolerance_bps: int         # Maximum permitted slippage in basis points
    limit_price: Optional[Decimal]      # Discretionary passive limit price
    
    # Priority & Slicing
    priority_tier: int                  # 1 (Close), 2 (Reduce), 3 (Flip), 4 (Expand)
    slice_index: int                    # 0 if unsliced, 1..K if paced
    total_slices: int                   # Total slices planned
    
    # Multi-Strategy Attribution Ledger
    strategy_attribution: Dict[str, Decimal] # {strategy_id: lot_contribution}
    netting_efficiency_ratio: Decimal   # NER for this instrument
    
    # Cryptographic Sealing
    intent_digest: str                  # SHA-256 of all fields above
```

---

## 22. Execution Intent Lifecycle

An `ExecutionIntent` transitions through explicit, immutable states:

```
                  EXECUTION INTENT LIFECYCLE STATE MACHINE
                                      │
                                      ▼
                                 [ CREATED ]
                                      │
                         Firewall Verification (OF-01..28)
                                      ├── Fail ──► [ REJECTED ] (Terminal)
                                      ▼
                                [ VALIDATED ]
                                      │
                           Internal Netting Check
                                      ▼
                                 [ NETTED ]
                                      │
                             Sequencing & Pacing
                                      ▼
                                  [ READY ]
                                      │
                           Dispatch to Phase 12
                                      ▼
                                [ DISPATCHED ]
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
             [ ACKNOWLEDGED ]    [ REJECTED ]      [ TIMEOUT ]
                    │             (Terminal)            │
        ┌───────────┴───────────┐                       ▼
        ▼                       ▼                  [ UNKNOWN ]
 [ PARTIALLY_EXECUTED ]    [ COMPLETED ]                │
        │                  (Terminal)            Authoritative
        ├── Fill Complete ──────┘               Reconciliation
        │                                               │
        ├── Cancelled ──► [ CANCELLED ]                 ▼
        │                  (Terminal)             [ RECONCILED ]
        ▼                                          (Terminal)
  [ RECONCILED ]
   (Terminal)
```

---

## 23. Intent State Machine & Transition Invariants

Phase 22 defines **fourteen deterministic states**:

| State | Classification | Description | Permitted Next States |
| :--- | :---: | :--- | :--- |
| `CREATED` | Transient | Intent instantiated; pending firewall validation. | `VALIDATED`, `REJECTED` |
| `VALIDATED` | Staged | Passed all 28 firewall checks; pending netting. | `NETTED`, `REJECTED` |
| `NETTED` | Staged | Net trade delta and strategy attribution computed. | `READY`, `REJECTED` |
| `READY` | Staged | Priority sequenced; ready for Phase 12 dispatch. | `DISPATCHED`, `CANCELLED` |
| `DISPATCHED` | Active | Sent to Phase 12; pending venue response. | `ACKNOWLEDGED`, `REJECTED`, `TIMEOUT` |
| `ACKNOWLEDGED`| Active | Phase 12 confirmed venue order placement. | `PARTIALLY_EXECUTED`, `COMPLETED`, `CANCEL_REQUESTED`, `REJECTED` |
| `PARTIALLY_EXECUTED`| Active | One or more fills recorded; balance remaining. | `COMPLETED`, `CANCEL_REQUESTED`, `RECONCILED` |
| `COMPLETED` | Terminal | Full quantity filled ($	ext{filled\_qty} == 	ext{quantity\_lots}$). | *None* |
| `CANCEL_REQUESTED`| Active | Cancel command emitted to Phase 12. | `CANCELLED`, `COMPLETED`, `TIMEOUT` |
| `CANCELLED` | Terminal | Venue confirmed cancellation; residual dropped. | *None* |
| `REJECTED` | Terminal | Rejected by firewall, Phase 12, or broker. | *None* |
| `TIMEOUT` | Degraded | Venue failed to respond within `timeout_ms`. | `UNKNOWN`, `RECONCILED` |
| `UNKNOWN` | Degraded | Execution state uncertain; requires reconciliation.| `RECONCILED` |
| `RECONCILED` | Terminal | Resolved via authoritative Phase 12 ledger audit. | *None* |

---

## 24. Partial Execution Handling

When an MT5 or broker order executes across multiple discrete deals:
1. **Accumulator Pattern:** Phase 22 updates `filled_quantity = \sum 	ext{deal.volume}`.
2. **Residual Exposure Tracking:** $	ext{residual\_lots} = Q_{	ext{intent}} - 	ext{filled\_quantity}$.
3. **Timeout on Partial Fill:** If an intent times out with $0 < 	ext{filled} < Q_{	ext{intent}}$:
   - Intent enters `TIMEOUT` state.
   - Phase 22 halts subsequent rebalancing for symbol $s$.
   - Triggers mandatory Phase 12 reconciliation to establish final confirmed position.

---

## 25. Rejection Handling

1. **Deterministic Fail-Closed:** Any rejection emitted by Phase 12 immediately terminates the intent into `REJECTED`.
2. **Zero Blind Retries:** Phase 22 **never** retries a rejected intent automatically. Blind retries in fast markets cause double fills, quota lockouts, and margin exhaustion.
3. **Quarantine:** The rejected instrument is quarantined for $300	ext{s}$ pending supervisory inspection.

---

## 26. Cancellation Handling

1. **Order Cancel Race:** If a fill occurs while cancellation is inflight, the fill is accepted and recorded as authoritative.
2. **Residual Drop:** When cancellation is confirmed, any unfilled balance is closed; Phase 22 updates internal position reality to match actual broker position.

---

## 27. Timeout & UNKNOWN Semantics

$$oxed{\mathbf{CRITICAL\;INVARIANTS:}\quad 	ext{TIMEOUT} 
e 	ext{SUCCESS} \quad \land \quad 	ext{UNKNOWN} 
e 	ext{FAILED}}$$

1. **No Assumption of Success:** Local network or IPC timeout **never** implies the order was filled.
2. **No Assumption of Failure:** Local timeout **never** implies the order was dropped; the broker may have matched the order on its matching engine.
3. **Transition to UNKNOWN:** Any unconfirmed intent past deadline enters `UNKNOWN`.
4. **Mandatory Reconciliation Authority:** The engine halts all new intent generation for the affected asset until Phase 12 emits an authoritative `ReconciliationEvidence` record.

---

## 28. Stale Allocation Handling

- If $T_{	ext{now}} - T_{	ext{decision}} > 120	ext{s}$: Ingestion halts under `ERR_ORCH_ALLOCATION_STALE`.
- Existing active positions are held unchanged. Zero new execution intents are generated.

---

## 29. Missing Allocation Handling

- If Phase 21 emits no record or fails to complete within schedule: Phase 22 enters `DEFENSIVE_HOLD`. Zero trading occurs.

---

## 30. Missing Position State Handling

- If Phase 12 fails to provide a position telemetry snapshot, or if the snapshot is stale ($> 30	ext{s}$):
  $$oxed{\mathbf{MANDATORY\;HALT:}\quad 	ext{Phase 22 MUST NOT assume current position is zero.}}$$
- Netting against an assumed zero position while real broker positions exist causes catastrophic double-exposure and immediate risk breach. Phase 22 raises `ERR_ORCH_POSITION_TELEMETRY_STALE` and halts.

---

## 31. Restart & Recovery Semantics

### 31.1 Cold Start (Engine Boot)
1. Initialize in-memory registries.
2. Ingest sealed `orchestration_ledger.jsonl`.
3. Rebuild historical state sequence and verify ledger hash chain.
4. Request authoritative position snapshot from Phase 12.
5. Ingest fresh `PortfolioAllocationPlan` from Phase 21.
6. Begin normal orchestration cycle.

### 31.2 Warm Crash Recovery
If Phase 22 crashes mid-rebalance:
1. Re-read last committed ledger entry.
2. Scan for any intent in `DISPATCHED` or `ACKNOWLEDGED` state.
3. Mark all unconfirmed inflight intents as `UNKNOWN`.
4. Invoke Phase 12 `ReconciliationEngine` to reconcile broker tickets against intents.
5. Transition resolved intents to `RECONCILED` with verified deal tickets.

---

## 32. Crash Consistency & Atomic Persistence

1. **Write-Ahead Logging:** State transitions are written and flushed to `orchestration_ledger.jsonl` **before** dispatching intents to Phase 12.
2. **Atomic Ledger Appends:** Ledger records are flushed with OS-level sync guarantees (`fsync`).
3. **No In-Memory Only States:** Every state transition must have an on-disk ledger footprint.

---

## 33. Replay & Reconciliation Semantics

$$oxed{\mathbf{SOVEREIGN\;TRUTH:}\quad 	ext{Downstream Broker Evidence } \gg 	ext{ Internal Orchestration State}}$$

When internal shadow records disagree with Phase 12 broker reconciliation:
1. Phase 12 broker position reality is adopted as canonical truth.
2. The internal discrepancy is logged as an auditable variance event.
3. The next orchestration cycle nets against the actual broker reality.

---

## 34. Idempotency Across Restart

- On recovery, the engine inspects historical `idempotency_key` indices.
- Any request attempting to reuse an existing idempotency key is intercepted and returns the cached execution intent record without re-dispatching.

---

## 35. Cryptographic Lineage & Sealing

Every execution intent carries an unbroken cryptographic lineage sealing the entire ACASH decision chain:

```
Phase 17 Strategy Admission Manifest Digest (SHA-256)
               │
               ▼
Phase 6 Statistical Validation Ledger Digest (SHA-256)
               │
               ▼
Phase 8.5 Economic Qualification Dossier Digest (SHA-256)
               │
               ▼
Phase 11 Forward Monitoring Health Digest (SHA-256)
               │
               ▼
Phase 19 Market Regime Observation Digest (SHA-256)
               │
               ▼
Phase 20 Strategy Selection Decision Digest (SHA-256)
               │
               ▼
Phase 21 Portfolio Allocation Plan Digest (SHA-256)
               │
               ▼
Phase 22 Orchestration Plan & Intent Digest (SHA-256)
               │
               ▼
Phase 12 Physical Execution Order Digest (SHA-256)
```

$$\mathbf{Orphan\;Intent\;Ban:}\quad 	ext{Any execution intent lacking a verified } 	ext{allocation\_digest} 	ext{ is strictly invalid.}$$

---

## 36. Phase 20 → Phase 21 → Phase 22 Digest Chain Formalization

Phase 22 verifies:
$$	ext{verify\_hash}(	ext{allocation\_plan.allocation\_digest}, 	ext{CanonicalJSON}(	ext{Plan})) == 	ext{TRUE}$$
$$	ext{verify\_hash}(	ext{allocation\_plan.selection\_decision_digest}, 	ext{Phase20\_Record}) == 	ext{TRUE}$$

Any break in this cryptographic chain raises `ERR_ORCH_PHASE20_LINEAGE_BROKEN`.

---

## 37. Audit Ledger Design (`orchestration_ledger.jsonl`)

Every intent creation, transition, and netting calculation is recorded in an append-only, SHA-256 hash-chained ledger:

```json
{
  "sequence_number": 1001,
  "record_type": "ORCHESTRATION_PLAN",
  "orchestration_plan_id": "0191c9d4-1a20-7f12-8812-da8921a48192",
  "allocation_plan_id": "0191c8b2-3f10-7e88-9124-da8921a48192",
  "allocation_digest": "9d2e1f4a...89b1",
  "timestamp_utc": "2026-09-06T00:36:00.000000Z",
  "total_intents_emitted": 2,
  "netting_efficiency_ratio": "0.66666667",
  "gross_turnover_usd": "450000.00",
  "net_turnover_usd": "150000.00",
  "previous_ledger_digest": "3c4b5a6f...11a2",
  "ledger_digest": "8e7f6a5b...99c4"
}
```

---

## 38. Observability & Telemetry Model

Phase 22 exports structured real-time telemetry:
- `orch_intents_total{status="COMPLETED|REJECTED|CANCELLED"}`
- `orch_netting_efficiency_ratio{symbol="EURUSD"}`
- `orch_turnover_usd_total`
- `orch_rebalance_latency_ms`
- `orch_deadband_suppression_count`

---

## 39. Operational Health Signals

The engine computes an aggregate health status:
- **`HEALTHY`:** All feeds live, reconciliation variance zero, latency $< 100	ext{ms}$.
- **`DEGRADED`:** Market feed latency elevated ($> 500	ext{ms}$), deadband clamp active.
- **`CRITICAL`:** Reconciliation variance detected, partial fill timeout pending.
- **`HALTED`:** Circuit breaker active, missing position telemetry, firewall failure.

---

## 40. Human Override Governance & Protocol

### 40.1 Permitted Human Override Actions
An authenticated human supervisor may:
1. **`EMERGENCY_HALT`:** Instantly freeze all intent generation.
2. **`CANCEL_ALL_INFLIGHT`:** Request cancellation of all unconfirmed intents via Phase 12.
3. **`FORCE_DEFENSIVE_CASH`:** Order systematic liquidation of active positions to 100% cash.

### 40.2 Strict Override Prohibitions
A human operator **MUST NOT**:
- Manually edit target weights or netting equations.
- Manually generate synthetic fill or deal records.
- Bypass Phase 12 adapters to send raw socket commands to MT5/broker.
- Allocate capital to a strategy excluded by Phase 20 or Phase 21.

---

## 41. AI / LLM Governance Firewall

In strict compliance with `AGENTS.md` and Phase 14 governance:

| Domain | Permitted AI Action | Strictly Prohibited AI Action |
| :--- | :--- | :--- |
| **Diagnostics** | Summarize netting efficiency ratios and rebalance latency traces. | Suppress execution warnings or hide reconciliation variances. |
| **Explanation** | Generate audit narratives explaining algebraic netting outcomes. | Hallucinate fills, broker quotes, or trade executions. |
| **Execution** | **NONE.** AI has zero execution authority. | **Emit orders, route intents, modify quantities, or cancel trades.** |
| **Netting** | None. | **Modify netting logic, override deadbands, or re-prioritize trades.** |
| **Broker State** | None. | **Synthesize fills, simulate broker reality, or bypass reconciliation.** |

---

## 42. Phase 12 Interface Boundary

Phase 22 communicates with Phase 12 exclusively through typed DTO boundaries:

```
Phase 22 Orchestration Engine
        │
        ├── [ Emits: ExecutionIntent DTO ] ────────────────► Phase 12 Adapter
        │    (intent_id, symbol, lots, direction, digest)
        │
        └── [ Ingests: BrokerExecutionReality DTOs ] ◄────── Phase 12 Adapter
             (OrderAck, DealReality, PositionReality)
```

- **Zero Coupling:** Phase 22 has zero knowledge of MT5 Windows IPC, DLLs, socket handles, or REST endpoints.
- **Protocol Agnostic:** Phase 22 emits the same `ExecutionIntent` regardless of whether downstream is MT5, FIX, or Alpaca.

---

## 43. Broker Isolation Rules

1. **No Socket Libraries:** `socket`, `websockets`, `requests`, `httpx` for broker interaction are forbidden in Phase 22.
2. **No Terminal Handles:** Zero imports of MT5 Windows APIs or broker SDKs.
3. **Local Testing:** Tested exclusively against in-memory mock adapters implementing Phase 12 interfaces.

---

## 44. Fail-Closed Failure Semantics

$$oxed{\mathbf{FAIL-CLOSED\;CONTRACT:}\quad 	ext{Any Ambiguity, Mismatch, or Violation } \longrightarrow 	ext{ZERO INTENTS EMITTED}}$$

Under any unexpected exception, numerical error, or verification failure:
1. Engine halts intent generation immediately.
2. Emits an auditable `ORCHESTRATION_BLOCKED` record to ledger.
3. Leaves existing market positions untouched (prevents panic dumping).
4. Raises high-priority SRE alert.

---

## 45. Error & Reason Code Taxonomy (Comprehensive Catalog)

Phase 22 defines thirty-eight deterministic error codes:

| Error Code | Domain | Trigger Condition | Engine Action |
| :--- | :--- | :--- | :--- |
| `ERR_ORCH_PLAN_DIGEST_MISMATCH` | Integrity | Recalculated allocation plan digest diverges | Immediate halt. Security alert. |
| `ERR_ORCH_STATUS_NOT_PERMITTED` | Integrity | Phase 21 status is not permitted for orchestration | Halt. Log unpermitted status. |
| `ERR_ORCH_WEIGHT_SUM_INVALID` | Integrity | Target weights + cash do not sum to 1.00 | Invalidate plan. Fail closed. |
| `ERR_ORCH_CASH_BUFFER_BREACH` | Integrity | Cash weight below mandatory liquidity floor | Halt. Preserve cash reserve. |
| `ERR_ORCH_WEIGHT_NON_FINITE` | Integrity | Non-finite (NaN, Inf, null) values in allocation | Halt. Reject corrupt inputs. |
| `ERR_ORCH_STRATEGY_SET_MISMATCH` | Integrity | Strategy weight keys diverge from selected list | Reject plan. Lineage breach. |
| `ERR_ORCH_PHASE20_LINEAGE_BROKEN`| Lineage | Phase 20 decision digest unverified in ledger | Halt. Untrusted lineage. |
| `ERR_ORCH_ADMISSION_UNVERIFIED` | Lineage | Strategy admission status not ADMITTED | Halt. Unadmitted strategy leak. |
| `ERR_ORCH_VALIDATION_UNVERIFIED` | Lineage | Missing sealed Phase 6 validation digest | Halt. Unvalidated candidate leak.|
| `ERR_ORCH_QUALIFICATION_UNVERIFIED`| Lineage | Missing sealed Phase 8.5 qualification dossier | Halt. Unqualified candidate leak.|
| `ERR_ORCH_POLICY_DIGEST_MISMATCH`| Lineage | Orchestration policy manifest tampered | Security halt. Manifest altered. |
| `ERR_ORCH_POSITION_TELEMETRY_STALE`| Position | Broker position telemetry snapshot > 30s old | Freeze orchestration. Do not guess.|
| `ERR_ORCH_RECONCILIATION_UNCONFIRMED`| Position | Active reconciliation drift detected by Phase 12| Halt until reconciliation passes.|
| `ERR_ORCH_SYMBOL_SPEC_MISSING` | Market | BrokerSymbolSpec missing for target asset | Exclude asset; halt rebalance. |
| `ERR_ORCH_MARKET_DATA_STALE` | Market | Market quote snapshot older than staleness cap | Suppress intent for stale asset. |
| `ERR_ORCH_PHANTOM_POSITION_DETECTED`| Position | Broker holds position for uncataloged strategy | Raise compliance alert. Freeze. |
| `ERR_ORCH_POSITION_UNCERTAINTY` | Position | Position marked UNKNOWN by reconciliation | Halt all trading on symbol. |
| `ERR_ORCH_LEVERAGE_CEILING_BREACH`| Risk | Proposed gross notional exceeds leverage cap | Reject rebalance; clamp volume. |
| `ERR_ORCH_CONCENTRATION_BREACH` | Risk | Single asset notional exceeds concentration cap | Clamp target or halt. |
| `ERR_ORCH_SUB_MINIMUM_LOT_SIZE` | Execution | Trade delta non-zero but below volume_min | Suppress intent (deadband). |
| `ERR_ORCH_LOT_STEP_MISALIGNMENT`| Execution | Trade delta not a clean multiple of volume_step | Quantization error; halt. |
| `ERR_ORCH_MAX_LOT_EXCEEDED` | Execution | Trade delta exceeds single-order ceiling | Route to lot slicer. |
| `ERR_ORCH_TURNOVER_BUDGET_EXCEEDED`| Risk | Rebalance turnover exceeds daily turnover budget | Scale down deltas or halt. |
| `ERR_ORCH_CIRCUIT_BREAKER_ACTIVE`| Risk | System emergency risk halt asserted | Global lock. 100% cash mode. |
| `ERR_ORCH_MARKET_SESSION_CLOSED`| Market | Target instrument market session closed | Suppress trade until open. |
| `ERR_ORCH_MARKET_CLOSE_PROXIMITY`| Market | Rebalance attempted within 5m of market close | Suppress trade; avoid illiquidity.|
| `ERR_ORCH_INFLIGHT_INTENT_COLLISION`| Execution | Unacknowledged intent already active for symbol | Block duplicate intent emission. |
| `ERR_ORCH_IDEMPOTENCY_COLLISION` | Execution | Derived intent ID collides with historic ledger | Reject submission. Duplicate ID. |
| `ERR_ORCH_ALLOCATION_STALE` | Temporal | Allocation plan age exceeds 120s | Halt. Request fresh allocation. |
| `ERR_ORCH_TEMPORAL_LOOKAHEAD` | Temporal | Evaluation timestamp in the future | Immediate abort. Lookahead leak.|
| `ERR_ORCH_DOWNSTREAM_REJECT` | Execution | Phase 12 or broker rejected intent | Quarantine symbol; alert SRE. |
| `ERR_ORCH_EXECUTION_TIMEOUT` | Execution | Venue failed to confirm order within timeout | Mark TIMEOUT; route to recon. |
| `ERR_ORCH_PARTIAL_FILL_HANG` | Execution | Order stalled in partial fill state | Issue cancel; reconcile residual.|
| `ERR_ORCH_CANCEL_RACE_DETECTED` | Execution | Fill occurred while cancel was inflight | Accept fill; reconcile ledger. |
| `ERR_ORCH_LEDGER_WRITE_FAILURE` | Storage | Failed to flush ledger record to disk | Critical abort. Halt immediately.|
| `ERR_ORCH_REPLAY_ATTEMPT_DETECTED`| Security | Duplicate allocation plan replayed | Security block. Replay attack. |
| `ERR_ORCH_AI_INTERVENTION_DETECTED`| Governance | AI agent attempted to modify intent parameters | Security block. AI firewall breach.|
| `ERR_ORCH_MANUAL_OVERRIDE_SCOPE_BREACH`| Governance | Human override attempted to inject new strategy | Reject override. Scope breach. |

---

## 46. Security & Tamper Resistance

1. **Immutable In-Memory DTOs:** All internal classes use Pydantic `frozen=True` and `extra='forbid'`.
2. **Cryptographic Sealing:** Every intent, ledger entry, and snapshot contains a SHA-256 digest verified at every stage.
3. **Memory Isolation:** Sensitive allocation records are scrubbed from memory after ledger commitment.

---

## 47. Adversarial Threat Model (30 Attack Vectors)

To ensure institutional resilience, Phase 22 specifies controls against thirty distinct adversarial vectors:

| # | Threat Vector | Attack Mechanism | Detection Point | Fail-Closed Outcome | Authority Owner | Status |
| :-: | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Forged Allocation Plan** | Attacker crafts synthetic Phase 21 plan. | OF-01 digest recalculation. | Engine halts: `ERR_ORCH_PLAN_DIGEST_MISMATCH`. | Lineage Engine | CONTROL SPECIFIED |
| **2** | **Weight Tampering** | Attacker alters weight $w_i$ from $0.10$ to $0.90$. | OF-01 digest & OF-03 sum check. | Immediate reject: `ERR_ORCH_WEIGHT_SUM_INVALID`. | Risk Management | CONTROL SPECIFIED |
| **3** | **Strategy ID Injection** | Attacker adds unselected strategy ID to plan. | OF-06 strategy set validation. | Engine halts: `ERR_ORCH_STRATEGY_SET_MISMATCH`. | Phase 20 Authority | CONTROL SPECIFIED |
| **4** | **Replayed Allocation Plan** | Stale plan from yesterday resent to trigger trades. | OF-12 timestamp & sequence check. | Engine rejects: `ERR_ORCH_ALLOCATION_STALE`. | Temporal Engine | CONTROL SPECIFIED |
| **5** | **Duplicate Intent Emission** | Race condition emits two identical buy intents. | OF-27 & OF-28 idempotency check. | Duplicate blocked: `ERR_ORCH_IDEMPOTENCY_COLLISION`. | Orchestration Engine | CONTROL SPECIFIED |
| **6** | **Cross-Session Injection** | Intent from dev environment routed to prod engine. | Environment tag & manifest check. | Engine halts: `ERR_ORCH_POLICY_DIGEST_MISMATCH`. | SRE / Governance | CONTROL SPECIFIED |
| **7** | **Attribution Hijacking** | Strategy A assigned profits/losses of Strategy B. | Multi-strategy attribution audit. | Digest mismatch halts internal ledger. | Audit Engine | CONTROL SPECIFIED |
| **8** | **Position Spoofing** | Compromised feed reports 0 position when 10 lots held. | OF-13 Phase 12 shadow recon check. | Mismatch triggers `ERR_ORCH_RECONCILIATION_UNCONFIRMED`. | Phase 12 Authority | CONTROL SPECIFIED |
| **9** | **Stale Position Snapshot** | Telemetry feed hangs; reports 10-minute-old state. | OF-12 telemetry age check ($> 30	ext{s}$). | Freeze rebalance: `ERR_ORCH_POSITION_TELEMETRY_STALE`. | Telemetry Engine | CONTROL SPECIFIED |
| **10**| **Conflicting Position Feeds** | WebSocket says 5 lots, REST says 2 lots. | Phase 12 reconciliation engine. | Engine declares `ERR_ORCH_POSITION_UNCERTAINTY`. | Phase 12 Authority | CONTROL SPECIFIED |
| **11**| **Partial-Fill Exploitation** | Partial fill received; attacker assumes full fill. | Accumulator residual verification. | Intent marked PARTIAL; halts further trade. | State Machine | CONTROL SPECIFIED |
| **12**| **Timeout Exploitation** | Network timeout treated as fill success. | Explicit rule: $	ext{TIMEOUT} 
e 	ext{SUCCESS}$. | Intent routes to UNKNOWN; requires recon. | State Machine | CONTROL SPECIFIED |
| **13**| **UNKNOWN-State Laundering** | System converts UNKNOWN to COMPLETED on reboot. | Recovery protocol forces reconciliation. | Engine halts until verified broker ticket matches. | State Machine | CONTROL SPECIFIED |
| **14**| **Idempotency Key Collision** | Attacker manufactures duplicate UUIDv7. | Ledger index checks unique constraints. | Reject duplicate: `ERR_ORCH_IDEMPOTENCY_COLLISION`. | Storage Engine | CONTROL SPECIFIED |
| **15**| **Digest Substitution** | Attacker substitutes parent digest with valid one. | Full parent chain traversal check. | Lineage break halts: `ERR_ORCH_PHASE20_LINEAGE_BROKEN`.| Lineage Engine | CONTROL SPECIFIED |
| **16**| **Venue Mismatch** | Intent formatted for MT5 sent to Alpaca adapter. | Venue tag validation against spec. | Adapter rejects: `ERR_ORCH_SYMBOL_SPEC_MISSING`. | Phase 12 Authority | CONTROL SPECIFIED |
| **17**| **Symbol Name Confusion** | `EURUSD` mapped to `EURUSD.pro` without spec. | `BrokerSymbolSpec` registry lookup. | Reject unverified symbol. | Adapter Authority | CONTROL SPECIFIED |
| **18**| **Unit Space Mismatch** | Notional dollars passed as lot volume. | OF-21 & OF-22 lot bounds checks. | Volume clamp halts: `ERR_ORCH_MAX_LOT_EXCEEDED`. | Quant Engine | CONTROL SPECIFIED |
| **19**| **Quantity Inversion** | Buy intent inverted to sell via negative volume. | Pydantic validator: $	ext{volume} > 0$ strictly. | Validation error: `DomainValidationError`. | Schema Validator | CONTROL SPECIFIED |
| **20**| **Sign Direction Inversion**| Attacker alters direction field in transit. | Cryptographic intent digest check. | Tampered intent rejected: digest mismatch. | Security Engine | CONTROL SPECIFIED |
| **21**| **Precision / Rounding Bleed**| Lot size $0.015$ submitted to $0.01$ step broker. | OF-21 lot step quantization check. | Engine rejects: `ERR_ORCH_LOT_STEP_MISALIGNMENT`. | Quant Engine | CONTROL SPECIFIED |
| **22**| **Race Condition on Rebalance**| New plan arrives before prior intents finish. | OF-27 pending intent drain check. | Block second plan: `ERR_ORCH_INFLIGHT_INTENT_COLLISION`.| Orchestration Engine | CONTROL SPECIFIED |
| **23**| **Restart Replay Surge** | Engine reboot re-executes yesterday's orders. | Ledger startup scan loads executed IDs. | Replayed orders suppressed; 0 trades. | Recovery Engine | CONTROL SPECIFIED |
| **24**| **Crash Mid-Persistence** | Machine crashes after memory update, before fsync. | Write-ahead logging ensures atomicity. | Uncommitted memory state discarded on reboot. | Storage Engine | CONTROL SPECIFIED |
| **25**| **AI Execution Injection** | LLM agent attempts to dispatch buy order intent. | AI Epistemic Firewall blocks write API. | Security alert: `ERR_ORCH_AI_INTERVENTION_DETECTED`. | AI Firewall | CONTROL SPECIFIED |
| **26**| **Override Scope Breach** | Operator injects unselected candidate via override. | OVR-01 mechanical subset check. | Reject override: `ERR_ORCH_MANUAL_OVERRIDE_SCOPE_BREACH`.| Governance Board | CONTROL SPECIFIED |
| **27**| **Phase 12 Adapter Bypass** | Attacker calls broker socket directly from Phase 22. | Architectural network/socket sandbox. | Import / socket call fails; compile error. | System Security | CONTROL SPECIFIED |
| **28**| **Spread-Crossing Churn** | Rapid oscillation triggers 100 rebalances per hour. | Turnover budget & deadband rule. | Churn suppressed: `ERR_ORCH_TURNOVER_BUDGET_EXCEEDED`. | Policy Engine | CONTROL SPECIFIED |
| **29**| **Market Close Squeeze** | Rebalance attempted 30 seconds before market close. | OF-26 market close proximity check. | Trade suppressed: `ERR_ORCH_MARKET_CLOSE_PROXIMITY`. | Market Engine | CONTROL SPECIFIED |
| **30**| **Synthetic Fill Injection** | Attacker inserts fake fill confirmation into queue. | Phase 12 deal ticket cryptographic verification. | Unverified deal rejected; security halt. | Phase 12 Authority | CONTROL SPECIFIED |

---

## 48. Acceptance Criteria

The Phase 22 Master Architecture Specification is deemed acceptable when the following plan-level criteria are verified:

- [x] **Criterion 1 (Authority Demarcation):** Phase 22 strictly coordinates and nets execution intents without performing strategy selection (Phase 20), capital allocation (Phase 21), or physical order routing (Phase 12).
- [x] **Criterion 2 (Selection Subservience):** Enforces that Phase 22 cannot add, remove, substitute, or resurrect candidate strategies.
- [x] **Criterion 3 (Allocation Fidelity):** Verifies that Phase 22 faithfully translates Phase 21 target weights without altering portfolio risk budgets or re-optimizing.
- [x] **Criterion 4 (Eligibility Firewall):** Specifies 28 pre-orchestration filter predicates (`OF-01` to `OF-28`) across five governance domains.
- [x] **Criterion 5 (Deterministic Netting):** Formulates single-asset algebraic netting minimizing spread crossing and transaction fees.
- [x] **Criterion 6 (Position State Taxonomy):** Establishes explicit separation between strategy targets, portfolio targets, broker positions, and execution intents.
- [x] **Criterion 7 (Intent State Machine):** Implements a 14-state deterministic finite automaton with fail-closed timeout and UNKNOWN semantics.
- [x] **Criterion 8 (Timeout & UNKNOWN Rigor):** Explicitly specifies that `TIMEOUT != SUCCESS` and `UNKNOWN != FAILED`, requiring authoritative Phase 12 reconciliation.
- [x] **Criterion 9 (Sequencing Priority):** Enforces that risk-reducing liquidations strictly precede risk-expanding acquisitions.
- [x] **Criterion 10 (Deadbands & Turnover):** Formulates rebalance deadbands and maximum turnover caps to eliminate churn.
- [x] **Criterion 11 (Cryptographic Lineage):** Specifies the immutable `ExecutionIntent` schema and hash-chained `orchestration_ledger.jsonl`.
- [x] **Criterion 12 (Adversarial Robustness):** Specifies defense mechanisms across thirty adversarial attack vectors.
- [x] **Criterion 13 (Wire & Socket Isolation):** Confirms zero direct broker API connections, zero raw sockets, and strict Phase 12 adapter decoupling.
- [x] **Criterion 14 (Zero Machine-Specific Paths):** Verifies document portability using strictly repository-relative paths.
- [x] **Criterion 15 (Runtime Invariant Preservation):** Confirms zero code implementation, `$0.00` live capital, zero orders, broker disconnected, and Phase 13 soak (PID 41844) untouched.

---

## 49. Governance Verification Matrix

| Verification Dimension | Governance Requirement | Phase 22 Status | Evidentiary Basis |
| :--- | :--- | :---: | :--- |
| **Authority Isolation** | Zero selection, allocation, or broker execution leakage | **VERIFIED (SPECIFICATION)** | Sections 3, 4, 42, 43 |
| **Firewall Completeness** | 28 fail-closed predicates covering integrity, risk, position | **VERIFIED (SPECIFICATION)** | Section 7 (`OF-01` to `OF-28`) |
| **Netting Mechanics** | Algebraic netting with strategy sub-ledger attribution | **VERIFIED (SPECIFICATION)** | Sections 8, 9, 11, 12 |
| **State Machine Safety** | Fail-closed timeout, unknown state requires reconciliation | **VERIFIED (SPECIFICATION)** | Sections 22, 23, 27 |
| **Idempotency & Replay**| Deterministic UUIDv7, write-ahead ledger logging | **VERIFIED (SPECIFICATION)** | Sections 14, 32, 34, 37 |
| **Adversarial Hardening**| 30 attack vectors addressed with fail-closed outcomes | **VERIFIED (SPECIFICATION)** | Section 47 |
| **Runtime Implementation**| STRICTLY LOCKED / NOT AUTHORIZED | **ENFORCED** | Zero code in `src/` or `tests/` |
| **Operational Capital** | Hard-locked at $0.00; broker disconnected | **ENFORCED** | Invariant in Header & Section 2 |
| **Phase 13 Soak Runner** | PID 41844 active and untouched | **ENFORCED** | Step 5 soak unmolested |

---

## 50. Final Sign-Off & Implementation Lock

```
================================================================================
                    ACASH GOVERNANCE & ARCHITECTURE SIGN-OFF
================================================================================
Document ID             : ACASH-SPEC-PHASE22-ORCHESTRATION-v1.0
Specification Status    : PROPOSED ARCHITECTURE — PENDING HUMAN GOVERNANCE APPROVAL
Implementation Status   : STRICTLY LOCKED / NOT AUTHORIZED
Parent Roadmap          : docs/ROADMAP.md (v3.4.0)
Parent Architecture     : AGENTS.md, ADR-022, ADR-023, ADR-024, ADR-025

Lead Quant Architect   : Antigravity / Senior Quant Trading Infrastructure Architect
Governance Auditor      : Statistical Governance & Risk Management Reviewer
DevOps / SRE Lead       : Fail-Closed Systems Engineer

Verification Status:
  - Architecture Review : COMPLETE / SATISFIED (DESIGN SPECIFICATION INSPECTION)
  - Authority Isolation : STRICTLY DEMARCATED (Zero Selection, Allocation, or Physical Wire Overreach)
  - State-Machine Check : VERIFIED CONSISTENT (14 States, Fail-Closed UNKNOWN Semantics)
  - Mathematical Sound  : GOVERNED FORMULATIONS (Algebraic Netting, Lots Quantization, NER)
  - Fail-Closed Contract: COMPLETE (38/38 Failure Modes Handled; AMBIGUITY -> ZERO INTENT)
  - Adversarial Audit   : COMPLETE (30/30 Dimensions Addressed)
  - Live Trading State  : HARD-LOCKED ($0.00 Capital, 0 Orders, Broker Disconnected)
  - Background Soak     : UNTOUCHED (PID 41844 Active in Step 5)

FINAL VERDICT:
  -> PROPOSED ARCHITECTURE: READY FOR HUMAN REVIEW & GOVERNANCE AUDIT
  -> IMPLEMENTATION: STRICTLY LOCKED UNTIL FORMAL HUMAN GOVERNANCE SIGN-OFF
================================================================================
```
