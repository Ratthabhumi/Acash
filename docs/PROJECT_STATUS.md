# ACASH — Project Status & Implementation Progress

> **NOTE (2026-09-28, branch `governance/core001-staged-evidence-v1-preobs`):**
> Sections 1–5 below are the preserved 2026-09-04 snapshot (history, not
> current state). The current snapshot is §0. Canonical staged-evidence
> governance: `docs/CORE_001_STAGED_EVIDENCE_FRAMEWORK_V1.md`.

---

## 0. Current Snapshot — CORE-001 / HYP_011 PRE-S1 (2026-09-28)

- Hypothesis: HYP_011 Global 80/20 (ACWI 80% / AGG 20%; SPY benchmark).
  Historical: CORRECTED SUPPORTED (100000 → 218852.857740; return
  1.1885285774; Sharpe 0.7082199886; MDD 0.27068044647; authority
  `77f5610ce63015f014c5283980a01a48536f5841`).
- Stage: **PRE-S1 / awaiting Observation #0001**. Observed = 0.
  Rebalances = 0. Observation #0001 scheduled (session 2026-09-28;
  homelab timer 2026-09-28 20:10 UTC = 2026-09-29 03:10 ICT) but
  **NOT observed**.
- 2026-09-25: `MISSED_UNOBSERVED_DUE_TO_AUTHORIZATION_LOCK` (no backfill).
- Main pin: `d9608c0a2353bd5ed41943e5fb893ef9648089d2` (MUST NOT move
  before Observation #0001). Runtime Python 3.14.7; timer enabled/waiting;
  dry-run verified (`NETWORK_REQUESTS = 0`).
- Staged Evidence Framework v1: RATIFIED (structure + S2 guardrails MDD
  < 25% / cumret > -20% / every daily > -10%, predeclared pre-Observation).
- Authorities: paper NOT authorized; live LOCKED; real capital $0.00;
  `NO_REAL_ORDERS=true`.
- Next immediate event: Observation #0001. Next governance work: post-Obs-#1
  audit; merge decision for this branch; Observation #0002 automation. No
  prospective results were used for any threshold.

---

> **Document:** `docs/PROJECT_STATUS.md`  
> **Project Name:** ACASH (Automated Capital Allocation System)  
> **Status:** Phases 0–12 Complete & Frozen (`1e1d154`); Phase 13 Slice 1 (Gate A Pre-Live Certification) In Progress (`2f01841`)  
> **Date:** 2026-09-04  
> **Operating Environment:** Windows 10/11 x64  
> **Runtime:** Python 3.14.3/3.14.6 64-bit (`.venv`), Git 2.55.0  
> **Baseline Verification:** 1251 collected tests (11/11 Phase 13 Slice 1 Gate A Layer A passed; 1251 passed, 0 failed, 3 skipped optional); MyPy clean across 264 source files  

---

## 1. Executive Summary

ACASH is a scientific, research-first, evidence-driven capital allocation and quantitative execution platform. ACASH is **not** an indicator collection, **not** an MT5 EA bot, and **not** an unconstrained LLM trading agent. Its primary purpose is answering:

> *"Given the current market, available opportunities, portfolio state, uncertainty, liquidity, and risk constraints, where should capital be allocated?"* (including the valid governed decision: **NOWHERE**).

Phases 0 through 10 are completely implemented, verified, and frozen. Phase 11 Contract Specification v1.1 and Red-Team Review are locked. The pre-phase-11 architectural hygiene audit has synchronized source-of-truth documentation, locked dual-clock determinism guarantees, and established precision and hashing authority tiers.

---

## 2. Workspace & Environment Inspection

| Aspect | Inspected State | Notes / Implication |
| :--- | :--- | :--- |
| **Codebase State** | Phases 0–12 Fully Implemented & Frozen | ~19,000+ lines of production and test code across 263 source files. |
| **Primary Machine** | Single Workstation (AIO) | Adheres to Section 29 (simple infrastructure first). |
| **Secondary Hardware** | Acer Ubuntu Server, ATX Proxmox | Available for future 24/7 services and staging/testing. |
| **Python Runtime** | Python 3.14.6 64-bit | Core packages built Python-first; `.venv` environment isolation. |
| **Test Suite Baseline** | 1240 collected tests (1158 unit + 82 integration; 1240 passed, 0 failed) | 3 tests skipped cleanly due to optional dependency gating (`skfolio`, `cvxpy`). 0 failures. |
| **Version Control** | Git (`main == origin/main`) | Clean working tree; Phase 12 frozen commit: `1e1d154`. |

---

## 3. Storage Architecture Summary

- **Analytical / Research Data Plane:** Partitioned Parquet files + embedded DuckDB analytical query engine with bi-temporal Point-In-Time (PIT) indexing. (DuckDB is strictly analytical, not a transactional DB).
- **Transactional Operational State:** SQLite local database for order states and positions; append-only JSON Lines ledger (`OperationalLedger`) with cryptographic SHA-256 hash chaining for runtime cycle events and sovereign kill-switch persistence.
- **Control Plane Persistence:** PostgreSQL is **DEFERRED** until concurrent multi-process writers, production durability, or operational requirements justify it.

---

## 4. Phase Implementation Inventory & Sovereign Baselines

| Phase | Description | Status | Verification Gate |
| :--- | :--- | :---: | :--- |
| **Phase 0** | Architecture Evaluation, ADRs, & Contracts | **FROZEN** | ADR-001 through ADR-019 locked. |
| **Phase 1** | Core Domain Models & Invariant State Transitions | **FROZEN** | Pure state transitions, absorbing terminal states. |
| **Phase 2** | Data Ingestion & Storage Architecture | **FROZEN** | Parquet + DuckDB analytical query engine. |
| **Phase 3** | Market Data Microstructure & PIT Anti-Leakage | **FROZEN** | Strict point-in-time bi-temporal indexing. |
| **Phase 4** | Quantitative Research & Alpha Prototyping | **FROZEN** | Factor screening & signal evaluation. |
| **Phase 5** | Event-Driven Backtest Substrate Evaluation | **FROZEN** | NautilusTrader bridge & reality gap analysis. |
| **Phase 6** | Statistical Validation & Multiple Testing Correction | **FROZEN** | Purged CPCV, Deflated Sharpe Engine, Haircut SR. |
| **Phase 7** | Live Execution Reality & Broker Adapter | **FROZEN** | Alpaca Paper adapter, execution coordinator. |
| **Phase 8** | Portfolio Model Selection Tournament | **FROZEN** | Native HRP, ERC, baselines, OOS tournament. Commit: `e6f1d04`. |
| **Phase 8.5** | Alpha Research Qualification & Lineage DTOs | **FROZEN** | Immutable `AlphaQualificationDossier`. Commit: `9ce1365`. |
| **Phase 9** | Sovereign Deterministic Risk Engine & Kill Switch | **FROZEN** | Boundary veto, derisking, kill switch. Commit: `6bd40d8`. |
| **Phase 10** | Runtime Orchestration & Continuous Paper Operations | **FROZEN** | 5-stage supervisor, dual-clock scheduler, ledger. Commit: `3955bf6`. |
| **Phase 11** | Forward Drift Detection & Execution Attribution | **FROZEN** | 107 unit + 26 red-team + 9 integration tests. Commit: `86bff0d` → `092a2b1`. |
| **Phase 12** | MT5 & Venue Execution Adapters | **FROZEN** | 6-D RECON, `MT5BrokerAdapter`, Gate 6 Two-Phase Routing, intent_id routing. Commit: `1e1d154`. Closeout: `docs/phase12/closeout_report.md`. |
| **Phase 13** | Live Small Capital Deployment (Gate B Governance Repair Rev 10) | **IN PROGRESS** | Gate A Certified; Gate B Rev 10 Step 2 Implementation & B1–B23 Adversarial Verification COMPLETE. Step 3 Ceremony & Step 4 Activation LOCKED. Live Capital: $0.00, Orders: 0. |

---

## 5. Architectural Invariants Enforced

1. **Five-Way Sovereign Separation:**
   $$\boxed{\mathbf{Research\ (8.5)} \neq \mathbf{Allocation\ (8)} \neq \mathbf{Supervisor\ (10)} \neq \mathbf{Risk\ (9)} \neq \mathbf{Execution\ (7)} \neq \mathbf{Forward\ (11)} \neq \mathbf{Broker}}$$
2. **Dual-Clock Determinism Discipline:**
   $$\boxed{\mathbf{Deterministic\ Domain\ Calculation} \implies \text{MUST receive explicit } \mathbf{as\_of\_utc}}$$
   Supervisor cycle always supplies explicit `as_of_utc`; ambient clock fallbacks are reserved strictly for standalone/test use.
3. **Numeric Precision Boundary:**
   $$\boxed{\mathbf{Phase\ 11\ Evidence\ Generation} \implies \text{Zero } \mathbf{Decimal \longrightarrow float \longrightarrow Decimal} \text{ in Identity Paths}}$$
4. **Cryptographic Hashing Hierarchy:**
   - **Tier 1 (Canonical Identity):** `CanonicalConfigSerializer` (authoritative evidence, policy, and lineage identity).
   - **Tier 2 (Event Chaining):** `OperationalLedger` SHA-256 event chaining.
   - **Tier 3 (Local Convenience):** Component-local hashes (strictly non-lineage, non-trust-bearing).
