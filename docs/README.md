# ACASH Documentation Hub (`docs/README.md`)

Welcome to the canonical documentation center for the **ACASH Quantitative Research & Execution Engine** and **Project Atlas**.

---

## 🗺️ Progressive Subsystem Navigation

```
                                  ACASH DOCUMENTATION TREE
                                             │
      ┌──────────────────┬───────────────────┼───────────────────┬──────────────────┐
      ▼                  ▼                   ▼                   ▼                  ▼
🏛️ ARCHITECTURE    📜 PROPOSALS       🛡️ VALIDATION       ⚡ EXECUTION       🌐 ATLAS
 (Core System)      (Phases 1-6)        (Phase 6 Stat)      (Phase 7/12/13)    (Knowledge)
                                                                 │
                                                                 ▼
                                                         🤖 AI RESEARCH
                                                            (Phase 14)
```

| Section | Focus Area | Canonical Documents |
| :--- | :--- | :--- |
| 🧭 **System Management & Governance** | System status, roadmap, architectural decisions, risks | [`docs/ROADMAP.md`](./ROADMAP.md) • [`docs/PROJECT_STATUS.md`](./PROJECT_STATUS.md) • [`docs/DECISIONS.md`](./DECISIONS.md) • [`docs/RISKS.md`](./RISKS.md) |
| 🏛️ **System Architecture** | 7-layer modular monolith, bi-temporal data, storage, portfolio, research | [`docs/architecture/system_architecture.md`](./architecture/system_architecture.md) • [`docs/architecture/data_architecture.md`](./architecture/data_architecture.md) • [`docs/architecture/data_contract.md`](./architecture/data_contract.md) • [`docs/architecture/execution_architecture.md`](./architecture/execution_architecture.md) • [`docs/architecture/portfolio_architecture.md`](./architecture/portfolio_architecture.md) • [`docs/architecture/research_architecture.md`](./architecture/research_architecture.md) • [`docs/architecture/technology_evaluation.md`](./architecture/technology_evaluation.md) • [`docs/architecture/multi_broker_multi_asset_decision.md`](./architecture/multi_broker_multi_asset_decision.md) |
| 📜 **Design Proposals & Plans** | Detailed implementation specifications & phase plans (Phases 1–6) | [`docs/proposals/phase_1_foundation.md`](./proposals/phase_1_foundation.md) • [`docs/proposals/phase_3_microstructure.md`](./proposals/phase_3_microstructure.md) • [`docs/proposals/phase_3b_orderbook.md`](./proposals/phase_3b_orderbook.md) • [`docs/proposals/phase_3c_feature_engine.md`](./proposals/phase_3c_feature_engine.md) • [`docs/proposals/phase_4_alpha_engine.md`](./proposals/phase_4_alpha_engine.md) • [`docs/proposals/phase_5_simulation.md`](./proposals/phase_5_simulation.md) • [`docs/proposals/phase_6_validation.md`](./proposals/phase_6_validation.md) |
| 🔬 **Phase 8.5: Alpha Research & Evidence** | Research lineage, hypothesis pre-registration, search census, terminal falsification | [`docs/phase8.5/phase8_5_hyp_tsmom_eurusd_002_terminal_falsification_dossier.md`](./phase8.5/phase8_5_hyp_tsmom_eurusd_002_terminal_falsification_dossier.md) • [`docs/phase8.5/phase8_5_r3_search_trial_census_audit_HYP_002.md`](./phase8.5/phase8_5_r3_search_trial_census_audit_HYP_002.md) • [`docs/phase8.5/phase8_5_hyp_tsmom_eurusd_001_terminal_falsification_dossier.md`](./phase8.5/phase8_5_hyp_tsmom_eurusd_001_terminal_falsification_dossier.md) • [`docs/phase8.5/phase8_5_r3_search_trial_census_audit.md`](./phase8.5/phase8_5_r3_search_trial_census_audit.md) |
| 🛡️ **Phase 6: Statistical Governance** | Deflated Sharpe (DSR), MinTRL, Balanced CSCV PBO, Holm FWER, Haircut Sharpe, DGP Benchmarks | [`docs/validation/methodology_contract.md`](./validation/methodology_contract.md) • [`docs/validation/phase6_methodology_dgp_report.md`](./validation/phase6_methodology_dgp_report.md) |
| ⚡ **Phase 7: Live Execution & Broker Mapping** | Pre-Live Risk Admission, Live Authorization, BMAP, Kill Switch, Reconciliation, P-001 | [`docs/phase7/phase_7_proposal.md`](./phase7/phase_7_proposal.md) • [`docs/phase7/CONTEXT_MAP.md`](./phase7/CONTEXT_MAP.md) • [`docs/phase7/alpaca_bmap.md`](./phase7/alpaca_bmap.md) • [`docs/phase7/r1_paper_run_runbook.md`](./phase7/r1_paper_run_runbook.md) • [`docs/phase7/execution_state_machine.md`](./phase7/execution_state_machine.md) |
| 🔌 **Phase 12: MT5 & Venue Adapters** | Thin MT5 broker driver, volume quantization, tick-grid alignment, 6-D reconciliation | [`docs/phase12/closeout_report.md`](./phase12/closeout_report.md) • [`docs/architecture/multi_broker_multi_asset_decision.md`](./architecture/multi_broker_multi_asset_decision.md) |
| 🧪 **Phase 13: Live Small Capital & Soak** | Gate A certification, 24-hour unattended soak, full forensic audit, paper readiness | [`docs/phase13/PHASE13-LIVE-SMALL-CAPITAL-PLAN-REV3.md`](./phase13/PHASE13-LIVE-SMALL-CAPITAL-PLAN-REV3.md) • [`docs/phase13/consolidated_gate_a_audit.md`](./phase13/consolidated_gate_a_audit.md) • [`docs/phase13/phase13_step6_full_audit_report.md`](./phase13/phase13_step6_full_audit_report.md) • [`docs/phase13/phase13_step7_paper_readiness_review.md`](./phase13/phase13_step7_paper_readiness_review.md) |
| 🤖 **Phase 14: AI Quantitative Research** | Master Research Architecture, hypothesis assistant, Section 33 reporting, causal AST | [`docs/phase14/phase14_master_research_architecture_plan.md`](./phase14/phase14_master_research_architecture_plan.md) • [`docs/phase14/phase14_architecture_and_governance_plan.md`](./phase14/phase14_architecture_and_governance_plan.md) |
| 🌐 **Project Atlas (Knowledge Graph)** | Event-Driven Graph, Particle Propagation, Market Microstructure Taxonomy | [`docs/atlas/CONTEXT_MAP.md`](./atlas/CONTEXT_MAP.md) • [`docs/atlas/graph/architecture.md`](./atlas/graph/architecture.md) • [`docs/atlas/market/microstructure.md`](./atlas/market/microstructure.md) |

---

## 🏛️ Current Governance & Runtime State (2026-09-07)
- **Phase 8.5 Track B (Research Lineage):** RESEARCH STANDING BY / ALL HYPOTHESES TERMINALLY FALSIFIED
  - `HYP_TSMOM_EURUSD_001` (M5 Intraday): TERMINALLY FALSIFIED in-sample (0/9 trials passed; R4–R7 early-terminated; 2026 M5 holdout QUARANTINED / PRISTINE).
  - `HYP_TSMOM_EURUSD_HTF_002` (H4 Session): TERMINALLY FALSIFIED in-sample (0/12 trials passed; R4–R7 early-terminated; H4 validation & OOS partitions QUARANTINED / PRISTINE / NOT REUSABLE FOR HYP_003 BY DEFAULT).
  - `HYP_003`: NOT CREATED (Awaiting formal new R1 pre-registration and clean independent data window).
- **Phase 12 (Execution Adapters):** COMPLETED & FROZEN (`1e1d154`).
- **Phase 13 (Live Small Capital / Soak):** INFRASTRUCTURE READY / STRATEGY BLOCKED.
  - Steps 1–4: **PASSED**.
  - Step 5 (24-Hour Soak): **VERIFIED COMPLETED** (86,400.21s runtime, 86,085 events, zero errors).
  - Step 6 (Full Forensic Audit): **PASSED** (Ledger SHA-256 integrity clean, zero gaps >15s, RSS peak 175.29 MB).
  - Step 7 (Continuous Paper Readiness): **CONDITIONALLY SATISFIED** (Infrastructure operational; strategy qualification blocked; B23.2 deferred).
  - Step 8 (Human GO Checkpoint): **STRICTLY LOCKED** (Awaiting qualified strategy and operator sign-off).
  - Step 9 (90-Day Continuous Paper Run): **STRICTLY NOT AUTHORIZED** (Clock not started).
- **Phase 14 (AI Research Layer):** PLAN APPROVED AT PLAN LEVEL ([`docs/phase14/phase14_master_research_architecture_plan.md`](./phase14/phase14_master_research_architecture_plan.md)).
  - Implementation: **STRICTLY LOCKED / NOT AUTHORIZED**.
- **Live Capital Authority:** Strictly **$0.00 (Hard-Locked)**.
- **Live Order Emission:** Strictly **0 Orders**.
- **Broker Connection:** Strictly **DISCONNECTED**.
- **Strategy Admission:** Strictly **`NOT QUALIFIED / TERMINALLY FALSIFIED`** (`STRAT-MOM-MULTI-HORIZON-V1`, `STRAT-MOM-HTF-H4-V1`).

---

## 📜 Global Engineering Principles & Guardrails
* **Project-Wide Engineering Operating System**: [`AGENTS.md`](../AGENTS.md)
* **Developer & Quant Quick Reference**: [`Cheatsheet.md`](../Cheatsheet.md)
* **Model-Specific Lessons & Behavioral Guardrails**: [`ANTIGRAVITY_GEMINI_3.7_FLASH.md`](../ANTIGRAVITY_GEMINI_3.7_FLASH.md)
