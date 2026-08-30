# Atlas Market Microstructure & Order-Flow Event Taxonomy

## 1. Domain Overview
Atlas models market microstructure phenomena (DOM, footprint, volume profile, liquidity pulls, and absorptions) as structured semantic events within the knowledge graph.

---

## 2. Epistemic Separation & Rule Provenance
To avoid ungrounded model outputs or freeform assertions, every order-flow event candidate must carry explicit mathematical provenance:

```json
{
  "event_type": "ABSORPTION_CANDIDATE",
  "epistemic_level": "INFERRED",
  "rule_id": "OF_ABSORPTION_V1",
  "evidence": [
    "aggressive_sell_volume_exceeds_threshold",
    "price_response_variance_below_epsilon",
    "resting_liquidity_absorption_ratio"
  ],
  "confidence": 0.87,
  "parameters": {
    "vol_threshold": 200,
    "delta_threshold": -150,
    "max_tick_movement": 1
  }
}
```

---

## 3. Order-Flow Event Taxonomies

### 1. `ABSORPTION_CANDIDATE`
- **Definition**: High aggressive market volume at a specific price level with negligible or zero directional price advance.
- **Rule Signature**: $\Delta V_{\text{aggressive}} \gg 0 \land |\Delta P| \le \epsilon$.

### 2. `LIQUIDITY_PULLED`
- **Definition**: Significant resting limit order depth placed and subsequently canceled as market price approaches without fill execution.
- **Rule Signature**: $\text{Depth}_{\text{resting}}(t_0) > D_{\text{thresh}} \land \text{Depth}_{\text{resting}}(t_1) \to 0 \land \text{Fills} = 0$.

### 3. `LEVEL_INTERACTION_AND_REJECTION`
- **Definition**: Price tests a declared structural high/low (e.g. Previous Day High, Volume Point of Control) followed by aggressive delta reversal.
- **Rule Signature**: $|P - P_{\text{level}}| \le \delta \land \operatorname{sgn}(\text{Delta}_{\text{post}}) = -\operatorname{sgn}(\text{Delta}_{\text{pre}})$.

---

## 4. Discretionary vs. Verified Stance
* Concepts from external order-flow tools (e.g. ATAS, Footprint charts) serve as **Domain Inspiration and Event Taxonomies**.
* They must NEVER be treated as unexamined mathematical ground truth or hardcoded predictive guarantees.
