# Atlas Graph Architecture Specification

## 1. Overview & Core Invariants
The Atlas Knowledge Graph represents entities, relationships, and state transitions derived canonically from real-world market, computational, or quantitative events.

### Core Invariants
1. **Graph State as Durable Canonical Data**:
   - The graph state is an authoritative, durable memory store.
   - It is completely independent of the rendering technology (Three.js, WebGL, WebGPU, React Force Graph).
2. **Deterministic Mutation**:
   - Graph state mutations only occur in response to validated, normalized events.
   - Every mutation is idempotent and replayable from the raw event stream.

---

## 2. Node & Edge Data Contracts

### Node Contract
```typescript
interface AtlasNode {
  id: string;                    // Unique deterministic entity ID (e.g. "LEVEL_4250.25")
  type: string;                  // Entity class (e.g. "PRICE_LEVEL", "MARKET", "STRATEGY")
  label: string;                 // Human-readable identifier
  properties: Record<string, any>; // Arbitrary typed attributes
  created_at: string;            // ISO timestamp
  last_updated: string;          // ISO timestamp
  epistemic_level: EpistemicLevel; // OBSERVED | DERIVED | INFERRED | CONFIRMED
  evidence_refs: string[];       // Cryptographic hashes of supporting events
}
```

### Edge Contract
```typescript
interface AtlasEdge {
  id: string;                    // Deterministic edge ID (e.g. "EDGE_STRAT_HYP_102")
  source: string;                // Source Node ID
  target: string;                // Target Node ID
  relation: string;              // Semantic relationship (e.g. "INTERACTS_WITH", "MENTIONS", "TRIGGERS")
  weight: number;                // Interaction strength / confidence [0.0, 1.0]
  created_at: string;
  evidence_refs: string[];
}
```

---

## 3. Separation from Projections
```text
Canonical Graph State
         │
         ├──► 3D Layout Projection (Force coordinates x, y, z)
         ├──► Search Index (Full-text / Node labels)
         ├──► Vector Embedding Projections
         └──► Visualization Styles (Colors, particle speeds, emissive materials)
```
Projections can be torn down and rebuilt at any time without data loss.
