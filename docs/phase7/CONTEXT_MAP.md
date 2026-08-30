# Phase 7 Progressive Context Map (`docs/phase7/CONTEXT_MAP.md`)

This navigation document implements **Progressive Disclosure of Context** for AI agents, developers, and automated systems working on **Phase 7: Live Execution, Pre-Live Risk Admission & Operational Governance**.

---

## 1. Operating Protocol for Phase 7

```text
1. Read AGENTS.md (Non-negotiable project-wide engineering principles)
2. Read docs/phase7/CONTEXT_MAP.md (This navigation map)
3. Identify Affected Subsystem from the matrix below
4. Load ONLY the specific specification document(s) required for the active task
5. Read ANTIGRAVITY_GEMINI_3.7_FLASH.md ONLY if the task touches model-risk patterns
6. Inspect existing data contracts, schemas, and invariant test suites
7. Implement changes strictly fail-closed with explicit cryptographic provenance
8. Run adversarial verification, golden reconciliation benchmarks, full test suite, and type checker
```

---

## 2. Phase 7 Subsystem Navigation Matrix

| Subsystem | Scope & Responsibilities | Canonical Specification |
| :--- | :--- | :--- |
| 🏛️ **Phase 7 Architecture** | End-to-end execution dataflow, one-way boundary from Phase 6, fail-closed policy | [`./architecture.md`](./architecture.md) |
| 📜 **Validation Certificate** | Read-only imported certificate from Phase 6, cryptographic verification, revocation | [`./certificate.md`](./certificate.md) |
| 🛡️ **Live Authorization** | Bridge from statistical validity to live capital, operational limits (notional, drawdown) | [`./live_authorization.md`](./live_authorization.md) |
| 📈 **Dynamic Risk State** | Real-time exposure, VaR/CVaR, connectivity status, state machine (NORMAL $\to$ HALTED) | [`./risk_state.md`](./risk_state.md) |
| 🔄 **Order & Position Lifecycle**| State machine (INTENT $\to$ FILLED / UNKNOWN), timeout handling, position tracking | [`./order_lifecycle.md`](./order_lifecycle.md) |
| 📦 **Execution Manifest** | Immutable manifest per execution, slippage/latency attribution, fill provenance | [`./execution_manifest.md`](./execution_manifest.md) |
| 🔀 **Execution State Machine** | Step 8 contract: authoritative transition table, `UNKNOWN` no-shortcut, terminal absorbing states | [`./execution_state_machine.md`](./execution_state_machine.md) |
| 🚨 **Kill Switch Engine** | First-class KillSwitchEvent, automated triggers (Stale data, Loss, Clock skew, Disconnect) | [`./kill_switch.md`](./kill_switch.md) |
| ⚖️ **Reconciliation Engine** | Internal vs. Broker state reconciliation, discrepancy detection, automated halt triggers | [`./reconciliation.md`](./reconciliation.md) |

---

## 3. Core Phase 7 Architectural Invariants

1. **The Authorization Invariant**:
   $$\boxed{\text{PASS\_TRADEABLE\_ALPHA} \neq \text{LIVE\_AUTHORIZATION}}$$
   - Phase 6 certifies historical statistical validity (`ValidationReport`).
   - Phase 7 authorizes live capital risk under bounded operational constraints (`LiveAuthorization`).
2. **One-Way Lineage Boundary**:
   - Phase 7 reads Phase 6 artifacts in read-only mode.
   - Phase 7 **NEVER** mutates, weakens, or rewrites Phase 6 evidence or reports.
3. **Fail-Closed Operational Safety**:
   - $\text{Unknown Risk State} \implies \text{HALT NEW ORDERS}$.
   - $\text{Reconciliation Mismatch} \implies \text{HALT NEW ORDERS + RAISE INCIDENT}$.
   - $\text{Stale Market Data} \implies \text{HALT NEW ORDERS}$.
4. **Cryptographic Lineage Chain**:
   $$\text{ValidationReport} \to \text{ValidationCertificate} \to \text{LiveAuthorization} \to \text{OrderIntent} \to \text{ExecutionManifest} \to \text{FillEvents} \to \text{ReconciliationReport}$$
