# SR-02 — Whale Pivot / Footprint

SOURCE STATUS: EXTERNAL / UNVERIFIED
THIS FILE PRESERVES CLAIMS; IT DOES NOT ENDORSE THEM.

## 1. Source Context & Raw Claims
- **Source Medium**: Order flow trading tutorial / TradingView footprint indicator presentation.
- **Reported Rule Set & Heuristics**:
  - Utilizes a TradingView volume footprint chart displaying bid/ask traded volume at price.
  - Claims specific price levels reveal "large institutions" and "smart money".
  - volume profile Principles:
    - Balanced volume profile indicates price pinning and mean reversion.
    - Unbalanced volume profile indicates acceleration and trend initiation.
  - **whale Threshold**: Volume > 400 contracts at a single price node is claimed to signify a "whale" / institutional order (whale, 400).
  - Follow-Through Dynamics:
    - Large volume with follow-through = institutional aggression.
    - Large volume with NO follow-through = institutional absorption.
  - **delta flip**: Transition from negative to positive delta indicates aggressive buyers taking control; positive to negative delta indicates aggressive sellers taking control.
  - Uses footprint levels as trade entry targets and support/resistance maps.

## 2. Human-Reviewed Scientific Critique
- **Arbitrary Magic Constant**: The threshold "volume > 400" (whale, 400) is an `UNSUPPORTED_HEURISTIC`. Absolute volume must be normalized by time of day, instrument, prevailing volatility, and available book depth.
- **Identity Fallacy**: Footprint volume reflects executed contracts matching aggressive market orders with passive limit orders; it does NOT reveal participant identity (whale, fund, algorithm, or fragmented retail).
- **Delta Interpretation**: Cumulative delta reflects trade aggression categorization (via tick rule or quote matching), not sovereign institutional conviction.

## 3. Mapping to ACASH Research Architecture
- **Mapped Research Mechanisms**:
  - `RI-03`: Order Flow Imbalance (OFI).
  - `RI-04`: Absorption / Impact Efficiency (absorption).
- **Trial Status**: Catalogued source context. Formal normalization required before any empirical testing.
