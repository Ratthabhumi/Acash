# Atlas Event-Driven Visualization & Rendering Core

## 1. The Core Architectural Invariant
> **"Particle movement represents real information propagation, not decoration."**

The visual graph is an interactive, real-time projection of underlying verified system events. It does not generate synthetic movement.

---

## 2. Event-to-Particle Pipeline
```text
1. Atlas receives Event X
2. Event X updates Graph State
3. Event X instantiates an Event Particle
4. Particle travels from source node A → target node B along the active edge
5. Upon arrival at node B, node B displays an arrival reaction (e.g. pulse, glow, state shift)
6. If Event X contains a propagation path [A, B, C], the particle continues to node C
```

---

## 3. Renderer Decoupling
The visualization layer is strictly a projection:
```text
[ Canonical Event Pipeline & Graph State ]
                    │
                    ▼ (Observable State Bridge)
       ┌────────────────────────┐
       │   Rendering Adapter    │
       └────────────┬───────────┘
                    │
   ┌────────────────┼────────────────┐
   ▼                ▼                ▼
[ React Force ]  [ Custom Three.js ] [ WebGPU / Future Engine ]
```
* **Rule**: If the renderer crashes or is replaced, the event model, graph state, and telemetry pipelines remain completely intact.

---

## 4. Implementation Hierarchy & Priorities
1. **Priority 1**: Correct event $\to$ graph-state propagation
2. **Priority 2**: Correct particle/event identity and trajectory
3. **Priority 3**: Correct node/edge reaction semantics
4. **Priority 4**: Real-time update behavior and smooth interpolation
5. **Priority 5**: Performance (60fps under load, instanced mesh rendering)
6. **Priority 6**: Visual polish, shaders, and post-processing
