# ACASH Research Intake Corpus (v1 — R0 Sealed)

## Overview & Purpose

This directory (`docs/research_intake/v1/`) contains the foundational, pre-experimental research intake corpus for the ACASH quantitative research and execution engine.

The primary objective of this repository subtree is **evidence preservation, lineage locking, and scientific intake sealing**. It establishes an immutable boundary separating unverified external claims (from creators, social media, trading courses, and discretionary practices) from human-reviewed scientific restatements suitable for subsequent quantitative investigation.

## Two-Layer Architectural Boundary

To prevent accidental parameter leakage, cherry-picking, and data-snooping contamination, this corpus enforces a strict filesystem-level separation between two distinct layers:

```
docs/research_intake/v1/
├── mechanisms/       <-- LAYER B: Human-reviewed scientific mechanism restatements
└── source_notes/     <-- LAYER A: Preserved external source claims & raw heuristics
```

### Layer A: Source Notes (`source_notes/`)
Preserves what external creators, videos, and social-media materials claimed in their original form.
- Contains specific indicator parameters (e.g., EMA 12, EMA 8/21, EMA 9/21/50, SMA 25).
- Contains arbitrary heuristics (e.g., "whale volume > 400", "65% rebound probability", "65–75% reversal zone", "2.5x volume spike").
- Contains reported commercial performance metrics (e.g., "982% return", "PF 1.49", "57% win rate").
- **Classification**: All source parameters and reported metrics are strictly classified as `EXTERNAL_UNVERIFIED_CLAIM` or `UNSUPPORTED_HEURISTIC`. They carry **zero** authority in ACASH.

### Layer B: Research Mechanisms (`mechanisms/`)
Translates empirical phenomena into rigorous, falsifiable market-microstructure or economic mechanisms.
- Strips all marketing, discretionary jargon, and unverified fixed parameters.
- Replaces magic numbers with parameterized, testable hypotheses (e.g., replacing "volume > 400" with normalized Order Flow Imbalance and liquidity absorption metrics).
- Establishes explicit Null Hypotheses ($H_0$), Alternative Hypotheses ($H_1$), required negative controls, and data provenance requirements.
- **Parameters**: Every mechanism explicitly declares `PARAMETERS_NOT_PREREGISTERED`.

## Non-Negotiable Governance Invariants

1. **SOURCE NOTE != HYPOTHESIS**: External claims are catalogued historical context, not ACASH hypotheses.
2. **RESEARCH INTAKE != BACKTEST AUTHORIZATION**: Inclusion in this corpus does **not** authorize empirical backtesting, parameter scanning, or data mining.
3. **RESEARCH INTAKE != CORE-002**: No candidate in this directory is promoted to the CORE portfolio.
4. **RESEARCH INTAKE != PAPER/LIVE AUTHORITY**: Zero trading authority is granted. Real capital authority remains strictly `$0.00` and `NO_REAL_ORDERS = true`.
5. **ISOLATION FROM CORE-001 / HYP_011**: The active baseline (CORE-001 / HYP_011) remains completely separate, untouched, and sealed under its own governance boundary. No mechanism here may be used to alter, retune, or rescue HYP_011.

## Directory Manifest & Navigation

- [R0_GOVERNANCE.md](file:///docs/research_intake/v1/R0_GOVERNANCE.md): Research intake governance charter, status declarations, and permitted lifecycle transitions.
- [METHODOLOGY_CONTROLS.md](file:///docs/research_intake/v1/METHODOLOGY_CONTROLS.md): Quantitative controls, multiple-testing corrections, bar-path ambiguity rules, and friction accounting.
- [DATA_AND_PROVENANCE_REQUIREMENTS.md](file:///docs/research_intake/v1/DATA_AND_PROVENANCE_REQUIREMENTS.md): Data schema, vendor semantics, and timestamp requirements across asset classes.
- [SOURCE_TO_MECHANISM_MAP.md](file:///docs/research_intake/v1/SOURCE_TO_MECHANISM_MAP.md): Many-to-many traceability mapping linking source notes (`SR-xx`) to mechanisms (`RI-xx`).
- [BIBLIOGRAPHY.md](file:///docs/research_intake/v1/BIBLIOGRAPHY.md): Curated academic and industry literature references supporting the intake mechanisms.
- [RESEARCH_INTAKE_V1_MANIFEST.json](file:///docs/research_intake/v1/RESEARCH_INTAKE_V1_MANIFEST.json): Cryptographic SHA-256 seal of all documents in this intake release.
