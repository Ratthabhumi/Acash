# R0 Correction Note 002 — Final Authority Fidelity Cleanup

## 1. Document Context & Historical Lineage
- **Document Title**: ACASH R0 Research Intake Final Authority Fidelity Cleanup (Note 002)
- **Corrects Commit**: `adfdfc9a5fe42303248ff56c2ab5bd9b30eea51a` (Correction 001)
- **Original Intake Commit**: `575b7b2b7701ed550cb31f5a8d4abeb4e4db3809`
- **Original Base Commit**: `d9608c0a2353bd5ed41943e5fb893ef9648089d2` (Observation #0001 homelab pin)
- **Lifecycle Phase**: R0 (Cataloguing, Structural Intake & Lineage Sealing)
- **Prior Acceptance Status**: `HOLD` (Secondary audit findings on remaining metadata and phrasing)
- **Updated Content Status**: `R0_CONTENT_CORRECTED_002_PENDING_HUMAN_AUDIT`

## 2. Reason for Correction
Following the successful application of Correction 001 (`adfdfc9a5fe42303248ff56c2ab5bd9b30eea51a`), an independent human scientific audit confirmed that core overreaches were resolved (commit lineage, parent pin, RI-10 identity inference removal, RI-03 horizon freeze removal, multiple testing unfrozen, bar-path unfrozen, and link hygiene).
However, a secondary review identified remaining areas where agent choices or memory persisted:
1. Bibliography metadata retained year, volume, issue, page range, and full author lists from model memory rather than pure human-source bound metadata.
2. Data contract requirements contained operational facts (FX session clock hours, universal SPX settlement framing, SOFR/Treasury rate models, specific pricing formulas) that are premature at R0.
3. Multiple mechanism files retained instrument-specific timezones (`America/New_York`) and specific feed requirements despite instrument universe remaining `NOT_YET_DETERMINED`.
4. Epistemic wording in RI-14 and RI-10 retained broad claims exceeding the human-reviewed R0 corpus.

This additive corrective commit performs the final authority-fidelity cleanup to ensure zero model-memory leakage and 100% adherence to human research governance prior to final R0 acceptance.

## 3. Detailed Audit Findings & Corrective Actions

### A. Bibliography Lineage & Metadata Hygiene (BIBLIOGRAPHY.md)
- **Audit Finding**: Bibliography entries still contained exact publication years, volumes, issue numbers, page spans, and reconstructed co-author strings from model memory.
- **Correction**: Stripped all reconstructed metadata (years, volumes, issue numbers, page ranges, full author lists) across all entries. Retained only the core author group, paper title, publication venue, and explicit tag `STATUS: METADATA_NOT_REVALIDATED_IN_R0`. Preserved zero external additions.

### B. Data-Contract Generality (DATA_AND_PROVENANCE_REQUIREMENTS.md)
- **Audit Finding**: Contained unnecessary operational specifics (e.g. hardcoded FX trading sessions, universal SPX AM cash settlement vs SPY PM physical settlement, specific rate curves, specific option pricing algorithms).
- **Correction**:
  - Replaced specific session hours with `EXACT_SESSION_HOURS: VERIFY_AT_FUTURE_DATA_CONTRACT_STAGE`.
  - Replaced universal SPX settlement framing with `SETTLEMENT_STYLE: VERIFY_PER_INSTRUMENT_AND_SERIES` (noting that SPX options have varying settlement conventions across series and expiries).
  - Explicitly set `RATE_MODEL: NOT_YET_DETERMINED`.
  - Explicitly set `PRICING_MODEL: NOT_YET_DETERMINED` (pricing model examples marked `ILLUSTRATIVE_ONLY — NOT PREREGISTERED`).
  - Set `TIMESTAMP_PRECISION: SUBJECT_TO_ZERO_OUTCOME_DATA_FEASIBILITY_AUDIT`.
  - Marked all feed/provider examples as `ILLUSTRATIVE_ONLY — NOT PREREGISTERED`.

### C. Mechanism Data Requirements Consistency (RI-01 through RI-15)
- **Audit Finding**: When `INSTRUMENT = NOT_YET_DETERMINED`, mechanism files still specified `Time Zone: America/New_York (UTC storage)`.
- **Correction**: Replaced across all 15 mechanism files with:
  - `CANONICAL_MARKET_TIMEZONE: NOT_YET_DETERMINED_BY_INSTRUMENT`
  - `UTC_STORAGE: REQUIRED`
  - Conceptualized data classes as generic observation tiers ("price observations", "quotes where execution semantics require them", "option chain fields where mechanism requires them") without freezing unnecessary feeds.

### D. Epistemic Wording Precision (RI-14 and RI-10)
- **RI-14 (FVG / SMC)**:
  - Replaced broad claim ("Scientific evidence does NOT support the claim that FVGs represent institutional balance sheets...") with corpus-bounded phrasing:
    *"The human-reviewed R0 corpus does not establish that FVGs represent institutional balance sheets, institutional identity, or guaranteed support/resistance."*
- **RI-10 (Volume Spike Breakout)**:
  - Replaced causal statement ("sufficient to absorb resting liquidity at local extremes") with epistemically neutral phrasing:
    *"High observed volume indicates elevated executed trading activity. Whether that activity contains incremental predictive information is unresolved at R0. When volume is abnormally elevated relative to historical baseline expectations, it reflects broader / more intense market participation rather than low-liquidity slippage. Trade volume does NOT identify participant identity (whale, institution, or retail)."*

## 4. Preservation of Invariants

- **Zero Backtest / Empirical Execution**: CONFIRMED.
- **Zero Market Data Ingested**: CONFIRMED.
- **Zero Parameter Sweeps**: CONFIRMED.
- **Zero CORE-002 Promotion**: CONFIRMED.
- **CORE-001 / HYP_011 Isolated & Unchanged**: CONFIRMED.
- **Main Branch Untouched**: CONFIRMED.
- **Real Capital Authority**: Strictly `$0.00`.
- **Execution Boundary**: `NO_REAL_ORDERS = true`.
- **Updated Status**: `R0_CONTENT_CORRECTED_002_PENDING_HUMAN_AUDIT`.
