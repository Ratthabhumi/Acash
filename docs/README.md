# ACASH Documentation Hub (`docs/README.md`)

Welcome to the canonical documentation center for the **ACASH Quantitative Research & Execution Engine** and **Project Atlas**.

---

## 🗺️ Progressive Subsystem Navigation

```
                                  ACASH DOCUMENTATION TREE
                                             │
      ┌──────────────────┬───────────────────┼───────────────────┬──────────────────┐
      ▼                  ▼                   ▼                   ▼                  ▼
🏛️ ARCHITECTURE    📜 PROPOSALS       🛡️ VALIDATION       ⚡ PHASE 7         🌐 ATLAS
 (Core System)      (Phases 1-6)        (Phase 6 Stat)      (Execution)        (Knowledge)
```

| Section | Focus Area | Canonical Documents |
| :--- | :--- | :--- |
| 🧭 **System Management & Governance** | System status, roadmap, architectural decisions, risks | [`docs/ROADMAP.md`](./ROADMAP.md) • [`docs/PROJECT_STATUS.md`](./PROJECT_STATUS.md) • [`docs/DECISIONS.md`](./DECISIONS.md) • [`docs/RISKS.md`](./RISKS.md) |
| 🏛️ **System Architecture** | 7-layer modular monolith, bi-temporal data, storage, portfolio, research | [`docs/architecture/system_architecture.md`](./architecture/system_architecture.md) • [`docs/architecture/data_architecture.md`](./architecture/data_architecture.md) • [`docs/architecture/data_contract.md`](./architecture/data_contract.md) • [`docs/architecture/execution_architecture.md`](./architecture/execution_architecture.md) • [`docs/architecture/portfolio_architecture.md`](./architecture/portfolio_architecture.md) • [`docs/architecture/research_architecture.md`](./architecture/research_architecture.md) • [`docs/architecture/technology_evaluation.md`](./architecture/technology_evaluation.md) |
| 📜 **Design Proposals & Plans** | Detailed implementation specifications & phase plans (Phases 1–6) | [`docs/proposals/phase_1_foundation.md`](./proposals/phase_1_foundation.md) • [`docs/proposals/phase_3_microstructure.md`](./proposals/phase_3_microstructure.md) • [`docs/proposals/phase_3b_orderbook.md`](./proposals/phase_3b_orderbook.md) • [`docs/proposals/phase_3c_feature_engine.md`](./proposals/phase_3c_feature_engine.md) • [`docs/proposals/phase_4_alpha_engine.md`](./proposals/phase_4_alpha_engine.md) • [`docs/proposals/phase_5_simulation.md`](./proposals/phase_5_simulation.md) • [`docs/proposals/phase_6_validation.md`](./proposals/phase_6_validation.md) |
| 🛡️ **Phase 6: Statistical Governance** | Deflated Sharpe (DSR), MinTRL, Balanced CSCV PBO, Holm FWER, Haircut Sharpe, DGP Benchmarks | [`docs/validation/methodology_contract.md`](./validation/methodology_contract.md) • [`docs/validation/phase6_methodology_dgp_report.md`](./validation/phase6_methodology_dgp_report.md) |
| ⚡ **Phase 7: Live Execution & Risk** | Pre-Live Risk Admission, Live Authorization, Broker Semantic Mapping (BMAP), Kill Switch, Reconciliation | [`docs/phase7/phase_7_proposal.md`](./phase7/phase_7_proposal.md) • [`docs/phase7/CONTEXT_MAP.md`](./phase7/CONTEXT_MAP.md) • [`docs/phase7/alpaca_bmap.md`](./phase7/alpaca_bmap.md) • [`docs/phase7/r1_paper_run_runbook.md`](./phase7/r1_paper_run_runbook.md) • [`docs/phase7/execution_state_machine.md`](./phase7/execution_state_machine.md) |
| 🌐 **Project Atlas (Knowledge Graph)** | Event-Driven Graph, Particle Propagation, Market Microstructure Taxonomy | [`docs/atlas/CONTEXT_MAP.md`](./atlas/CONTEXT_MAP.md) • [`docs/atlas/graph/architecture.md`](./atlas/graph/architecture.md) • [`docs/atlas/market/microstructure.md`](./atlas/market/microstructure.md) |

---

## 📜 Global Engineering Principles & Guardrails
* **Project-Wide Engineering Operating System**: [`AGENTS.md`](../AGENTS.md)
* **Developer & Quant Quick Reference**: [`Cheatsheet.md`](../Cheatsheet.md)
* **Model-Specific Lessons & Behavioral Guardrails**: [`ANTIGRAVITY_GEMINI_3.7_FLASH.md`](../ANTIGRAVITY_GEMINI_3.7_FLASH.md)
