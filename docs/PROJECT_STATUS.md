# ACASH — Project Status & Implementation Progress

> **Document:** `docs/PROJECT_STATUS.md`  
> **Project Name:** ACASH (Automated Capital Allocation System)  
> **Status:** Phases 0–10 Complete & Frozen (`3955bf6`); Phase 11 Contract Specification & Red-Team Review v1.1 Locked (`86bff0d`); Pre-Phase-11 Architecture Hygiene Complete  
> **Date:** 2026-09-02  
> **Operating Environment:** Windows 10/11 (AIO workstation)  
> **Runtime:** Python 3.14.6 64-bit, Git 2.55.0  
> **Baseline Verification:** 904 collected tests (901 passed, 3 skipped optional, 0 failed in 16.76s); MyPy clean across active modules  

---

## 1. Executive Summary

ACASH is a scientific, research-first, evidence-driven capital allocation and quantitative execution platform. ACASH is **not** an indicator collection, **not** an MT5 EA bot, and **not** an unconstrained LLM trading agent. Its primary purpose is answering:

> *"Given the current market, available opportunities, portfolio state, uncertainty, liquidity, and risk constraints, where should capital be allocated?"* (including the valid governed decision: **NOWHERE**).

Phases 0 through 10 are completely implemented, verified, and frozen. Phase 11 Contract Specification v1.1 and Red-Team Review are locked. The pre-phase-11 architectural hygiene audit has synchronized source-of-truth documentation, locked dual-clock determinism guarantees, and established precision and hashing authority tiers.

---

## 2. Workspace & Environment Inspection

| Aspect | Inspected State | Notes / Implication |
| :--- | :--- | :--- |
| **Codebase State** | Phases 0–10 Fully Implemented & Frozen | ~13,400+ lines of production and test code across 230 source files. Zero Phase 11 code authored. |
| **Primary Machine** | Single Workstation (AIO) | Adheres to Section 29 (simple infrastructure first). |
| **Secondary Hardware** | Acer Ubuntu Server, ATX Proxmox | Available for future 24/7 services and staging/testing. |
| **Python Runtime** | Python 3.14.6 64-bit | Core packages built Python-first; `.venv` environment isolation. |
| **Test Suite Baseline** | 904 collected tests (901 passed, 3 skipped) | 3 tests skipped cleanly due to optional dependency gating (`skfolio`, `cvxpy`). 0 failures. |
| **Version Control** | Git (`main == origin/main`) | Clean working tree; canonical commit: `86bff0d`. |

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
| **Phase 11** | Forward Drift Detection & Execution Attribution | **CONTRACT LOCKED (v1.1)** | Spec & Red-Team Review locked. Commit: `86bff0d`. |

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
