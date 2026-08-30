# Atlas Event Model & Pipeline Specification

## 1. Overview & Pipeline Lifecycle
The Atlas Event Pipeline ingests raw telemetry, validates structure, normalizes records into canonical events, and dispatches them to state managers and visualization particle emitters.

```text
[ Raw Telemetry / Feeds ]
           │
           ▼
[ Ingestion & Schema Validation ] (Fail-closed)
           │
           ▼
[ Canonical Event Normalization ] (Deterministic ID & Timestamp)
           │
           ├──► [ Graph State Reducer ] (State Mutation)
           │
           └──► [ Visualization Dispatcher ] (Particle Emission)
```

---

## 2. Canonical Event Schema

```json
{
  "event_id": "evt_20260830_849204",
  "timestamp": "2026-08-30T12:00:00.124Z",
  "source_entity": "FEED_ORDERBOOK_L2",
  "target_entity": "LEVEL_4250.25",
  "event_type": "ABSORPTION_CANDIDATE",
  "payload": {
    "price": 4250.25,
    "aggressive_volume": 250,
    "delta": -250,
    "resting_depth": 15
  },
  "propagation_path": ["FEED_ORDERBOOK_L2", "LEVEL_4250.25", "MARKET_REGIME_RANGE"],
  "epistemic_level": "INFERRED",
  "provenance": {
    "rule_id": "OF_ABSORPTION_V1",
    "evidence_refs": ["sha256_tick_l2_84920"],
    "confidence": 0.87
  }
}
```

---

## 3. Pipeline Invariants
1. **Immutable Event Records**: Events once emitted are append-only; they cannot be updated or deleted in place.
2. **Deterministic IDs**: Event ID must be derived deterministically from timestamp, source, target, and payload hash.
3. **Fail-Closed Normalization**: Invalid payload types, missing timestamps, or non-finite values are rejected immediately.
