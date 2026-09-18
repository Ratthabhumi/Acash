# MEC-0013 Price-Only ORB — Human Governance Decision Surface: Empirical Validation Authorization (D-EMP-1)

```text
[HUMAN-RATIFIED]
[IS-ONLY EMPIRICAL SCOPE AUTHORIZED]
[R1 NOT YET AUTHORIZED]
[OOS SEALED]
[FROZEN PREREGISTRATION BINDING]
[NO EMPIRICAL EXECUTION YET]
[MEC-0013 REMAINS ARCHIVED]
```

- **Document ID:** `docs/phase14/mec_0013_empirical_validation_authorization.md`
- **Decision ID:** `D-EMP-1`
- **Governing Specification:** `docs/phase14/mec_0013_price_only_preregistration.md` (Human-Ratified & Frozen 2026-09-18)
- **Base Scaffold:** `docs/phase14/mec_0013_price_only_draft_scaffold.md`
- **Calendar Authority:** Accepted `NyseCa1Calendar` (`src/acash/data/calendar/nyse_ca1.py`)
- **Object:** Formal Human Governance Decision Record for controlled empirical In-Sample (IS) validation of the frozen price-only Opening Range Breakout (ORB) on SPY with Out-of-Sample (OOS) strictly sealed.
- **Ratification Status:** RATIFIED — OPTION A (2026-09-18 by Human Operator)
- **Date:** 2026-09-18
- **Operating Environment:** Windows 10/11 x64, Python 3.14.x (`.venv`)
- **Authority:** Strict Fail-Closed (`AGENTS.md`). Zero empirical claims, zero return calculations, zero backtests executed.

---

> [!IMPORTANT]
> ### HARD GOVERNANCE BOUNDARIES (ACTIVE & PRESERVED)
> - **Zero Empirical Execution in this Step:** No backtests are executed; no historical market data is loaded; zero returns, PnL, Sharpe, win rate, or drawdown metrics are calculated.
> - **MEC-0013:** Remains **ARCHIVED** / `NOT PROMOTED` per ratified Human Decisions `MEC-0013-D01` and `MEC-0013-D02`.
> - **HYP_003:** **NOT CREATED** (absent repository-wide).
> - **Inception Gate R1:** **NOT INVOKED** / `ResearchReInceptionGate` not run.
> - **Empirical Validation:** **CURRENTLY LOCKED** pending explicit Human selection on this decision surface.
> - **OOS Data Partition (`2023–2026`):** **STRICTLY SEALED & UNREAD**.
> - **Trading Authority:** Paper `NOT AUTHORIZED`, Live `LOCKED`, Capital `$0.00`, `NO_REAL_ORDERS=true`.

---

## 1. Decision Purpose & Architectural Context

Following the formal ratification and freeze of the Price-Only ORB Pre-Registration Specification (`docs/phase14/mec_0013_price_only_preregistration.md`) via Decision `D-PREREG-1 (Option A)`, all 14 research-design degrees of freedom, the $K=4$ hypothesis census, and data-quality boundaries are immutable.

Under ACASH scientific research operating system principles:
$$\text{Specification Freeze} \longrightarrow \text{Validation Authorization Gate} \longrightarrow \text{Controlled Execution}$$

This document establishes Human Governance Decision Point **`D-EMP-1`**, defining the terms under which empirical execution may be authorized in a controlled, partitioned, and fail-closed manner.

---

## 2. Human Governance Decision Record — D-EMP-1

```text
================================================================================
HUMAN DECISION RECORD: D-EMP-1 — EMPIRICAL VALIDATION AUTHORIZATION
================================================================================
RATIFIED SELECTION: OPTION A — AUTHORIZE CONTROLLED IS-ONLY EMPIRICAL VALIDATION
Date:               2026-09-18
Ratifying Authority: Human Operator
Status:             RATIFIED (IS-ONLY SCOPE AUTHORIZED; R1 PENDING EXPLICIT AUTH)
================================================================================
```

### Exact Ratified Scope & Meaning:
The Human Operator formally selects and ratifies **OPTION A**: Authorizing exactly **ONE** controlled empirical validation run using **ONLY** the frozen In-Sample (IS) partition (`2017-01-01` through `2022-12-31`) under the strict terms of the frozen pre-registration specification (`docs/phase14/mec_0013_price_only_preregistration.md`).

#### 2. Authorized Scope:
- **Instrument:** `SPY` only.
- **Market Data Feed:** Historical consolidated 1-minute SIP aggregates (`feed=sip`, `timeframe=1Min`, `adjustment=raw`).
- **Calendar Authority:** Accepted `NyseCa1Calendar` (CA-1).
- **Session Types:** Regular 390-minute trading sessions (`[09:30, 16:00) ET`) only.
- **Data Quality Standard:** 100% complete CA-1 expected minute grid (exactly 390 bars per admitted session). Any missing, duplicate, non-monotonic, or invalid OHLC bar drops the entire session with an explicit cryptographic failure reason.
- **Mandatory Exclusions:**
  - Zero early-close sessions (all 13:00 ET sessions excluded).
  - Zero holidays or special closures.
  - Zero incomplete sessions.
  - Zero dates outside accepted CA-1 authority coverage (`2013–2026`).
- **Census Boundedness ($K=4$):**
  Only the 4 primary cells declared in the frozen pre-registration are authorized:
  1. `ORB_5M_LONG`
  2. `ORB_5M_SHORT`
  3. `ORB_15M_LONG`
  4. `ORB_15M_SHORT`
  *Zero additional primary cells or exploratory windows may be introduced.*
- **Parameter Immutability:**
  All 14 frozen parameters (close-through confirmation, next-bar open entry, symmetric directions, opposite-boundary stop, EOD flatten at 15:59, 1.6 bps round-trip transaction cost, 0.5 bps adverse slippage per side, conservative fill price conventions, 09:30 auction inclusion, 16:00 auction exclusion, 0-day embargo, 390-bar quality gate, regular-session exclusion) are **strictly immutable**.

#### 3. Strict Out-of-Sample (OOS) Sealing Mandate:
- **OOS Partition:** `2023-01-01` through `2026-12-31`.
- **Absolute Sealing Invariant:**
  - OOS data **MUST REMAIN SEALED**.
  - OOS data **MUST NOT BE LOADED** into memory during IS validation.
  - OOS data **MUST NOT BE SUMMARIZED**, sliced, or inspected.
  - OOS data **MUST NOT BE QUERIED** for strategy triggers, signals, or returns.
  - Any code path attempting to touch timestamps $\ge \text{2023-01-01T00:00:00Z}$ during IS execution must trigger an immediate fail-closed abort.

#### 4. Authorized Empirical Outputs (Per Cell):
When future execution is triggered, the engine is authorized to generate and persist the following metrics for all $K=4$ cells:
- Total eligible session count ($N_{\text{eligible}}$)
- Excluded session count categorized by cryptographic reason
- Signal count ($N_{\text{signal}}$)
- Executed trade count ($N_{\text{trade}}$)
- Stop-loss exit count vs EOD flatten exit count
- Gross return distribution (mean, median, standard deviation, IQR, min, max)
- Net return distribution (after frozen 1.6 bps transaction cost + 1.0 bps adverse slippage)
- Win rate ($\% \text{ trades with } R_{\text{net}} > 0$)
- Profit factor
- Maximum drawdown (MDD %)
- Average holding time in minutes
- Annualized Sharpe-like ratio (computed under canonical ACASH sample standards)
- Aggregate turnover
*Reporting Requirement:* Results must be reported across all 4 cells without selective omission or cherry-picking.

#### 5. Non-Negotiable Anti-HARKing Protocol:
Once In-Sample empirical results are observed by human or machine:
- Zero modification of the 14 frozen parameters.
- Zero deletion or hiding of underperforming cells.
- Zero addition of alternative opening-range windows (e.g. 10m, 30m).
- Zero addition of VWAP, volume, or volatility indicators.
- Zero recalibration of stops, profit targets, costs, or slippage.
- Zero expansion of the asset universe beyond `SPY`.
- Zero post-hoc model tuning prior to OOS exposure.
- Any subsequent adjustment requires a formal, dated research amendment with explicit lineage recorded before any affected OOS data may ever be unsealed.

#### 6. Audit & Evidence Lineage Requirements:
Any future authorized IS run must generate and seal a verifiable evidence package containing:
- Exact Git commit SHA of the execution codebase.
- Cryptographic SHA-256 digest of `docs/phase14/mec_0013_price_only_preregistration.md`.
- Cryptographic reference to the accepted `NyseCa1Calendar` implementation.
- Data-source manifest documenting Alpaca SIP provider parameters (`feed=sip`, `adjustment=raw`).
- Complete enumerated lists of included regular sessions and excluded sessions (with exact failure codes).
- Exact specification digests for all $K=4$ cells.
- Deterministic run identifier and code/config execution hash.
- Output metrics in machine-readable JSON and human-readable Markdown summary.
- Zero secret, credential, or machine-specific absolute path leakage.
- Raw market data remains local and git-ignored.

#### 7. Strict Fail-Closed Execution Invariants:
The empirical validation execution engine must abort immediately with a non-zero exit code if:
1. `docs/phase14/mec_0013_price_only_preregistration.md` differs in any byte or hash from the frozen record.
2. The execution pipeline attempts to query, load, or process dates $\ge 2023-01-01$ (OOS breach).
3. CA-1 calendar authority is missing, out-of-range, or emits unverified sessions.
4. Any session violates the 390/390 minute completeness rule and is not formally logged and excluded.
5. The data source schema or adjustments differ from raw unadjusted SIP specifications.
6. The active primary hypothesis grid cardinality $K \ne 4$.
7. Any of the 14 frozen parameters are modified or parameterized dynamically.
8. The repository working tree contains uncommitted modifications to strategy or data-qualification logic.
9. `HYP_003` is implicitly registered or synthesized without separate governance authorization.
10. Paper or Live trading modules or broker order dispatchers are imported or invoked.

---

### OPTION B — KEEP EMPIRICAL VALIDATION STRICTLY LOCKED

#### 1. Core Meaning:
Rejects immediate empirical validation. No market data is loaded, no backtests are authorized, and the research remains in a pure pre-registration holding state.

#### 2. Scope & Status Under Option B:
- In-Sample (IS) partition remains **SEALED**.
- Out-of-Sample (OOS) partition remains **SEALED**.
- `ResearchReInceptionGate` / Step R1 remains **NOT INVOKED**.
- Empirical backtesting engine remains **STRICTLY LOCKED**.
- MEC-0013 remains **ARCHIVED**.

---

## 3. Institutional Governance Analysis: Relationship with Step R1

A core mandate of ACASH governance is respecting the canonical research lifecycle and distinguishing research pre-registration from sovereign hypothesis inception.

### 3.1 Repository Governance Lineage
1. **Canonical Lifecycle Map (`docs/phase14/phase14_human_approval_readiness_review.md` §4):**
   The documented institutional research pipeline explicitly dictates:
   ```text
   Step 3: Human Quant Decision
     │
     ▼
   Step 4: Research Re-Inception Gate (src/acash/research/reinception.py)
     │   - Asserts candidate is NOT in TERMINAL_HYPOTHESIS_REGISTRY
     │   - Enforces Cross-Hypothesis Data Quarantine (Disjoint)
     │   - Enforces fail-closed validation of proposed window
     │   - Emits InceptionAuthorizationToken
     ▼
   Step 5: Step R1 Formal Pre-Registration
         - Creates sealed HypothesisSpecification (e.g. HYP_003.json)
         - Cryptographic hash sealed into execution manifest
   ```
2. **Pre-Registration Entry Contract (`docs/governance/research_reinception_gate.md` §1 & §2):**
   `ResearchReInceptionGate` is the machine-enforced governance control for Step R1 pre-registration. It validates:
   - Invariant 1: New immutable ID (`HYP_003`).
   - Invariant 2: Search cardinality equality ($K = \prod |Grid| = 4$).
   - Invariant 3: Declarative window and quarantine protection.
   - Invariant 4: Completeness of rationale, horizons, cost model.
   - Invariant 5: Decoupled readiness (`capital = $0.00`, `is_strategy_qualified = False`).
3. **Step R1 Authority Requirement (`docs/phase8.5/hypotheses/HYP_TSMOM_EURUSD_HTF_001_design.md` §6.3):**
   "Human operator sign-off required to submit the proposal to `ResearchReInceptionGate`, emit `InceptionAuthorizationToken`, and generate sealed hypothesis record."
4. **Non-Negotiable Rule (`AGENTS.md` §4):**
   "New operating instructions cannot create HYP_003, start R1, unlock backtests, grant trading authority, or amend acceptance criteria. Record a separately authorized amendment with its lineage rather than silently rewriting history."

### 3.2 Epistemic Finding: Does D-EMP-1 Authorize R1 or Require a Separate Gate?
- **Finding:** Under existing repository architecture, empirical backtesting across a formal hypothesis census historically consumes a sealed `HypothesisSpecification` emitted by `ResearchReInceptionGate` (Step R1).
- **Governance Classification:**
  - **D-EMP-1** authorizes the *substantive empirical scope and boundaries* (IS-only, SPY, 14 parameters, K=4, OOS sealed).
  - However, because `AGENTS.md` §4 strictly forbids AI agents from spontaneously creating `HYP_003` or invoking R1 without explicit human authorization, **D-EMP-1 cannot silently or implicitly invoke `ResearchReInceptionGate`**.
- **Fail-Closed Resolution:**
  To preserve 100% adherence to repository governance and avoid ambiguous authority boundaries:
  - **D-EMP-1 Option A** serves as the Human decision ratifying the empirical validation boundaries.
  - Before executing the backtest script, a dedicated proposal submission step must formally submit the `ResearchInceptionProposal` to `ResearchReInceptionGate` to emit the `InceptionAuthorizationToken` and seal `HYP_003.json`, **OR** the Human Operator must explicitly authorize D-EMP-1 to encompass the formal invocation of `ResearchReInceptionGate.evaluate_reinception_proposal()` as Step R1.
  - **Fail-closed mandate:** Until such explicit authority is recorded, `ResearchReInceptionGate` remains **NOT INVOKED** and `HYP_003` remains **NOT CREATED**.

---

## 4. Resulting Governance State & Non-Escalation Contract

Following ratification of Decision `D-EMP-1 (Option A)`, the precise governance state is:

| Boundary Dimension | Ratified Governance State | Authority Source |
|---|---|---|
| **D-EMP-1 Status** | `RATIFIED — OPTION A` | Human Decision `D-EMP-1` (2026-09-18) |
| **IS-Only Validation Scope** | `AUTHORIZED IN PRINCIPLE` (2017–2022 IS only) | Human Decision `D-EMP-1` |
| **Step R1 Inception Gate** | `NOT INVOKED` (Requires separate explicit Human authorization) | `AGENTS.md` §4, `ResearchReInceptionGate` |
| **Hypothesis Registry** | `HYP_003` **NOT CREATED** | Absent repository-wide |
| **Empirical Execution** | `BLOCKED` (Pending explicit Step R1 authorization & sealing) | Strict fail-closed boundary |
| **OOS Partition (`2023–2026`)** | **STRICTLY SEALED & UNREAD** | Frozen Pre-Registration Contract |
| **MEC-0013 Status** | Remains `ARCHIVED` / `NOT PROMOTED` | Decisions `MEC-0013-D01`, `MEC-0013-D02` |
| **Paper Execution** | **NOT AUTHORIZED** | Gate 4 clearance required |
| **Live Execution** | **STRICTLY LOCKED** | `capital = $0.00`, `NO_REAL_ORDERS=true` |

Regardless of the empirical outcome of the future authorized In-Sample run:
1. **MEC-0013 Status:** Remains **ARCHIVED** / `NOT PROMOTED`.
2. **Hypothesis Registry:** `HYP_003` does not automatically become an admitted trading candidate.
3. **OOS Sealing:** Out-of-Sample data (`2023–2026`) is **NOT** automatically unsealed. Unsealing OOS requires an independent, subsequent Human decision following formal review of the IS evidence package.
4. **Trading Authority:** Paper trading remains **NOT AUTHORIZED**; Live trading remains **LOCKED**; Capital authority remains **$0.00**; `NO_REAL_ORDERS=true`.

---

### Verification Ledger
- Implementation Status: COMPLETE (Decision D-EMP-1 formally ratified Option A; IS validation scope authorized in principle; R1 pending)
- Contract Enforcement: STRICT FAIL-CLOSED (Zero empirical data loaded; zero backtests executed; OOS strictly sealed; R1 uninvoked)
- Mathematical Authority: CANONICAL GOVERNANCE CONTRACT (Pre-registration binding)
- Local Test Suite: NOT REQUIRED (Pure governance documentation)
- Type Checker (MyPy): NOT APPLICABLE
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: IS empirical scope authorized in principle; execution remains strictly blocked pending explicit Step R1 authorization.
