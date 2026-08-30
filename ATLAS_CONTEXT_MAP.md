# ATLAS Progressive Context Map (ATLAS_CONTEXT_MAP.md)

This navigation document implements **Progressive Disclosure of Context** for AI agents, developers, and automated systems working on the **Atlas Event-Driven Knowledge Graph & Microstructure Engine**.

---

## 1. Operating Protocol for Agents

```text
1. Read AGENTS.md (Non-negotiable project-wide engineering principles)
2. Read ATLAS_CONTEXT_MAP.md (This navigation map)
3. Identify Affected Subsystem from the navigation matrix below
4. Load ONLY the specific subsystem document(s) required for the active task
5. Read ANTIGRAVITY_GEMINI_3.7_FLASH.md ONLY if the task involves model-risk failure modes or behavioral remediation
6. Inspect existing source code, schemas, and test suites
7. Implement changes strictly fail-closed with explicit provenance
8. Run adversarial verification, golden benchmarks, full test suite, and type checker
```

---

## 2. Subsystem Navigation Matrix

| Subsystem | Scope & Responsibilities | Canonical Specification |
| :--- | :--- | :--- |
| 🌐 **Graph Architecture** | Node/Edge schemas, graph state invariants, canonical state storage | [`docs/atlas/graph/architecture.md`](docs/atlas/graph/architecture.md) |
| ⚡ **Event Pipeline** | Ingestion, normalization, event lifecycle, and dispatcher | [`docs/atlas/events/event_model.md`](docs/atlas/events/event_model.md) |
| 🎨 **Visualization Core** | Event-driven particle propagation, node reaction semantics, renderer decoupling | [`docs/atlas/visualization/event_driven_rendering.md`](docs/atlas/visualization/event_driven_rendering.md) |
| 📊 **Market Microstructure** | Order-flow event taxonomies (DOM, Footprint, Absorption), rule provenance | [`docs/atlas/market/microstructure.md`](docs/atlas/market/microstructure.md) |
| 🧠 **AI Reasoning & Epistemics** | Epistemic levels (`OBSERVED` $\to$ `CONFIRMED`), evidence envelopes, causal chains | [`docs/atlas/reasoning/epistemic_model.md`](docs/atlas/reasoning/epistemic_model.md) |
| ⚙️ **Infrastructure & Runtime** | Storage layer, IPC, event streams, performance benchmarks | [`docs/atlas/infrastructure/runtime.md`](docs/atlas/infrastructure/runtime.md) |

---

## 3. Core Architectural Invariants

1. **Durable Truth vs. Rebuildable Projections**:
   - `Canonical Event` + `Canonical Graph State` + `Canonical Evidence` = **Durable Core (Must never be lost)**.
   - 3D renderers, vector embeddings, layout coordinates, and search indices = **Disposable Projections (Can always be deterministically rebuilt)**.
2. **The Particle Invariant**:
   - *"Particle movement represents real information propagation, not decoration."*
3. **The Epistemic Separation Invariant**:
   - $\text{Raw Observation} \neq \text{Interpretation} \neq \text{Causal Conclusion}$.
4. **Rule Provenance Invariant**:
   - Inferred events must carry explicit `rule_id`, `epistemic_level`, `evidence`, and `confidence`. Never generate freeform ungrounded classification strings.
