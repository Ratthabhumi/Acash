# Atlas Epistemic & Causal Reasoning Model

## 1. The Epistemic Separation Invariant
$$\boxed{\text{Raw Observation} \neq \text{Interpretation} \neq \text{Causal Conclusion}}$$

Atlas maintains strict epistemic hygiene across its knowledge graph, explicitly tagging every assertion with its confidence and validation tier.

---

## 2. The 5 Epistemic Levels

```text
┌──────────────────────────────────────────────────────────┐
│ 1. OBSERVED : Direct, unmanipulated raw data stream     │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│ 2. DERIVED  : Deterministic mathematical transformation  │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│ 3. INFERRED : Probabilistic pattern from multiple events│
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│ 4. CONFIRMED: Independently validated / Out-of-sample   │
└──────────────────────────────────────────────────────────┘
                             │
            [ If evidence is weak or contradictory ]
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│ 5. UNCERTAIN: Plausible hypothesis lacking proof         │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Evidence Envelope Contract
Every node transition, edge formation, or inference summary must encapsulate an evidence envelope:

```json
{
  "inference_id": "inf_849201",
  "target_node": "MARKET_REGIME_COMPRESSION",
  "epistemic_level": "INFERRED",
  "confidence": 0.82,
  "evidence_chain": [
    {
      "step": 1,
      "event_id": "evt_absorption_1",
      "epistemic_level": "OBSERVED",
      "timestamp": "2026-08-30T12:00:00Z"
    },
    {
      "step": 2,
      "rule_applied": "OF_ABSORPTION_V1",
      "epistemic_level": "DERIVED",
      "confidence": 0.90
    }
  ]
}
```
