# ACASH — Execution Architecture & Adapters Specification

**Document:** `docs/architecture/execution_architecture.md`  
**Version:** 3.1.0 (Micro-Corrections Applied)  
**Date:** 2026-08-27  

---

## 1. Core Execution Philosophy & Phase Boundaries

In ACASH, **execution is an operational gateway, not the brain**:
1. **Sovereign Boundaries:** All alpha generation, portfolio optimization, and risk checks occur strictly within ACASH prior to order dispatch.
2. **Phase 1 Boundary:** **Phase 1 MUST NOT implement live Nautilus execution.** Phase 1 defines `IBacktestEngine`, `IExecutionEngine`, and in-memory mock adapters for unit and integration testing.
3. **Pluggable Adapter Model:**
   $$\text{ACASH Core Interfaces} \to \text{Venue Adapter} \to \text{Broker / Matching Engine}$$
4. **NautilusTrader PoC Boundary:** NautilusTrader integration remains a future Phase 5 PoC. ACASH will not install or tightly couple to NautilusTrader during Phase 1.

---

## 2. Execution Subsystem Architecture

```
                               ┌─────────────────────────────┐
                               │       PORTFOLIO ENGINE      │
                               │  (Target Portfolio Weights) │
                               └──────────────┬──────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────────┐
                               │   RISK ENGINE (HARD GATE)   │
                               │  (Approve / Reduce / Reject)│
                               └──────────────┬──────────────┘
                                              │
                                              ▼ (Approved Target Allocation)
                               ┌─────────────────────────────┐
                               │      ORDER MANAGER          │
                               │ (Target Weights -> Orders)  │
                               │ (Reconciliation & Throttling│
                               └──────────────┬──────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
     ┌─────────────────────────────┐┌───────────────────┐┌─────────────────────────────┐
     │   MOCK / PAPER ADAPTER      ││   MT5 ADAPTER     ││  NAUTILUS TRADER ADAPTER    │
     │   (Phase 1 In-Memory &      ││ (Future Broker    ││ (Future Tier-2 Event Sim    │
     │    Phase 11 Live Paper)     ││  Gateway on Win)  ││  Candidate - Phase 5 PoC)   │
     └──────────────┬──────────────┘└─────────┬─────────┘└──────────────┬──────────────┘
                    │                         │                         │
                    └─────────────────────────┼─────────────────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────────┐
                               │  TRANSACTIONAL AUDIT STORE  │
                               │    (SQLite Local DB in V1)  │
                               └─────────────────────────────┘
```

---

## 3. Execution Adapters Breakdown & Roadmap

### 3.1 MockExecutionAdapter (Phase 1 Deliverable)
- **Role:** In-memory deterministic execution engine for Phase 1 unit testing and interface contract validation.

### 3.2 PaperExecutionAdapter (Phase 11 Deliverable)
- **Role:** Real-time simulated execution against live feeds without financial capital.

### 3.3 MT5Adapter (Phase 12 Deliverable)
- **Role:** Retail broker execution gateway via the Windows MetaTrader 5 terminal IPC. Zero strategy logic in MQL5.

### 3.4 NautilusTraderAdapter (Phase 5 PoC Candidate)
- **Role:** **Tier-2 event-driven simulation and future execution candidate.** Evaluated during Phase 5 PoC. Replaced if acceptance criteria are not met.
