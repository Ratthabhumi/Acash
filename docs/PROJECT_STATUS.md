# ACASH — Project Status & Discovery (Phase 0 Final)

**Document:** `docs/PROJECT_STATUS.md`  
**Project Name:** ACASH (Automated Capital Allocation System)  
**Status:** Phase 0 Complete — Clean & Ready for Human Approval  
**Date:** 2026-08-27  
**Operating Environment:** Windows 10/11 (AIO workstation)  
**Runtime:** Python 3.14.6 64-bit, Git 2.55.0  

---

## 1. Executive Summary

ACASH is a scientific, research-first, evidence-driven capital allocation and portfolio management platform. ACASH is **not** an indicator collection, **not** an MT5 EA bot, and **not** an unconstrained LLM trading agent. Its primary purpose is answering:

> *"Given the current market, available opportunities, portfolio state, uncertainty, liquidity, and risk constraints, where should capital be allocated?"* (including the valid decision: **NOWHERE**).

Phase 0 discovery and architecture evaluation is complete. All architectural foundations, open-source technology evaluations, storage tiers, decoupled execution boundaries, and correctness-driven testing criteria have been defined canonically in [`docs/`](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs).

---

## 2. Workspace & Environment Inspection

| Aspect | Inspected State | Notes / Implication |
| :--- | :--- | :--- |
| **Codebase State** | Greenfield (0 bytes production code) | Clean slate; zero legacy technical debt or coupling. |
| **Primary Machine** | Single Workstation (AIO) | Adheres to Section 29 (simple infrastructure first). |
| **Secondary Hardware** | Acer Ubuntu Server, ATX Proxmox | Available for future 24/7 services and staging/testing. |
| **Python Runtime** | Python 3.14.6 64-bit | Core packages built Python-first; `.venv` environment isolation. |
| **Package Manager** | `pip` 26.1.2 available | Virtual environment creation (`venv`) and deterministic dependency management. |
| **Version Control** | Git installed (`git 2.55.0`) | Repository initialization upon Phase 1 kickoff. |

---

## 3. Storage Architecture Summary

- **Analytical / Research Data:** Partitioned Parquet files + embedded DuckDB analytical query engine. (DuckDB is strictly analytical, not a transactional DB).
- **Transactional Operational State:** SQLite local database for V1 (order states, positions, audit ledger).
- **Control Plane Persistence:** PostgreSQL is **DEFERRED** until concurrent multi-process writers, production durability, or operational requirements justify it.

---

## 4. Phase 0 Deliverables Complete in `docs/`

1. [x] [docs/TECHNOLOGY_EVALUATION.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/TECHNOLOGY_EVALUATION.md)
2. [x] [docs/ARCHITECTURE.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/ARCHITECTURE.md)
3. [x] [docs/DATA_ARCHITECTURE.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/DATA_ARCHITECTURE.md)
4. [x] [docs/EXECUTION_ARCHITECTURE.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/EXECUTION_ARCHITECTURE.md)
5. [x] [docs/PORTFOLIO_ARCHITECTURE.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/PORTFOLIO_ARCHITECTURE.md)
6. [x] [docs/RESEARCH_ARCHITECTURE.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/RESEARCH_ARCHITECTURE.md)
7. [x] [docs/DECISIONS.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/DECISIONS.md) (ADR-001 through ADR-015)
8. [x] [docs/RISKS.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/RISKS.md)
9. [x] [docs/ROADMAP.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/ROADMAP.md)
10. [x] [docs/PHASE_1_PLAN.md](file:///c:/Users/Ratthabhumi/Desktop/CO-OP_Project/Acash/docs/PHASE_1_PLAN.md)
