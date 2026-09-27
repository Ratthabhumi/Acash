# R0 Correction Note 001 — Authority Fidelity Correction

## 1. Document Context & Historical Lineage
- **Document Title**: ACASH R0 Research Intake Authority Fidelity Correction (Note 001)
- **Original Intake Commit**: `575b7b2b7701ed550cb31f5a8d4abeb4e4db3809`
- **Original Base Commit**: `d9608c0a2353bd5ed41943e5fb893ef9648089d2` (Observation #0001 homelab pin)
- **Lifecycle Phase**: R0 (Cataloguing, Structural Intake & Lineage Sealing)
- **Prior Acceptance Status**: `HOLD` (Agent overreach identified during independent human audit)
- **Updated Content Status**: `R0_CONTENT_CORRECTED_PENDING_HUMAN_AUDIT`

## 2. Reason for Correction
An independent human scientific audit of commit `575b7b2b7701ed550cb31f5a8d4abeb4e4db3809` identified that while the commit lineage, base pin, 41-file structure, and source-vs-mechanism filesystem separation were successfully established, the implementation agent exceeded its authorized role. Specifically, the agent introduced unratified scientific design choices, causal explanations, data requirements, predictive horizons, specific data vendors, and mandatory methodology constraints not supplied by human research authority.

Under the ACASH research governance contract, R0 is strictly an **evidence preservation and intake seal phase**, NOT a scientific design or parameter selection phase. Where human authority did not supply an explicit specification, the correct status is `NOT_YET_DETERMINED` or `NOT_YET_PREREGISTERED`, rather than agent-invented defaults.

This corrective commit preserves the first R0 commit in Git history as lineage and performs an additive correction to restore strict fidelity to human research authority.

## 3. Detailed Audit Findings & Corrective Actions

### A. Removal of Institutional-Identity Inference (RI-10)
- **Audit Defect**: `RI-10` stated that abnormal volume "may signal genuine institutional participation" and "indicates coordinated market participation".
- **Correction**: Replaced with neutral market-activity language ("unusually elevated trading activity / participation" and "broader / more intense market participation"). Preserved the strict principle that trade volume reflects executed turnover and liquidity consumption, but does NOT reveal participant identity.

### B. OFI Epistemic & Predictive Horizon Correction (RI-03)
- **Audit Defect**: `RI-03` claimed that Cont, Kukanov, and Stoikov (2014) "prove a strong linear relationship" and froze an unauthorized predictive horizon of "100 milliseconds to 5 minutes".
- **Correction**: Reworded literature finding to "documents / finds / estimates a strong approximately linear relationship". Removed the frozen 100ms–5m horizon. Restated $H_0$ and $H_1$ in broad conceptual terms, explicitly setting the predictive horizon as `NOT_YET_PREREGISTERED`.

### C. Removal of Agent-Invented Empirical Design Choices (RI-01 through RI-15)
- **Audit Defect**: Multiple mechanism files contained agent-selected instruments (e.g., SPY, QQQ, ES, NQ), sample periods (e.g., minimum 3, 5, 10, or 20 years), timestamp precisions (microsecond / nanosecond), specific data vendors (e.g., OptionMetrics, Cboe DataShop), and specific midday placebo windows (e.g., 11:30–12:00, 13:00–13:30 ET).
- **Correction**: Replaced unauthorized specifications across all RI files with:
  - `INSTRUMENT`: `NOT_YET_DETERMINED` (any mentioned instruments marked `ILLUSTRATIVE_ONLY — NOT PREREGISTERED`)
  - `HISTORICAL_COVERAGE`: `NOT_YET_DETERMINED`
  - `PROVIDER`: `NOT_YET_DETERMINED`
  - `SIGNAL_HORIZON`: `NOT_YET_PREREGISTERED`
  - `TIMESTAMP_PRECISION`: `SUBJECT_TO_ZERO_OUTCOME_DATA_FEASIBILITY_AUDIT`

### D. Dealer Gamma & Retail GEX Framing (RI-05)
- **Audit Defect**: Wording blurred the distinction between retail model estimates and actual dealer inventory.
- **Correction**: Reaffirmed that retail GEX maps are model-dependent estimates with assumed customer signs, NOT observed dealer inventory. Set instrument scope, expiry scope, and history to `NOT_YET_DETERMINED`.

### E. Implied Volatility & Unratified Literature Removal (RI-08)
- **Audit Defect**: Agent imported unsupplied academic literature citations (Carr and Wu, Bollerslev) from model memory.
- **Correction**: Excised unsupplied citations. Preserved the illustrative volatility scaling example ($24\% / \sqrt{252} \approx 1.51\%$), the distinction between risk-neutral distributions and physical probabilities, and the classification of creator probability claims (65%, 65–75%) as `EXTERNAL_UNVERIFIED_CLAIM`.

### F. Momentum Causal Language (RI-09)
- **Audit Defect**: Stated that momentum "is driven by" specific behavioral and structural causes as settled facts.
- **Correction**: Reworded to "Proposed explanations in the broader literature may include...", reflecting that while empirical momentum is documented, its economic causes remain an active research debate. Reaffirmed `DO_NOT_RECYCLE` into CORE-002.

### G. FVG / SMC Epistemic Boundary (RI-14)
- **Audit Defect**: Used sweeping historical assertions ("originates entirely within unregulated retail...", "zero institutional standing").
- **Correction**: Restated cleanly: "No mature peer-reviewed evidence establishing the supplied FVG trading interpretation is present in the human-reviewed R0 corpus." Maintained `NEGATIVE_CONTROL_CANDIDATE` classification and bar-path ambiguity warnings.

### H. Methodology Controls De-Mandating (METHODOLOGY_CONTROLS.md)
- **Multiple Testing**: Corrected statement that DSR and White's Reality Check are FWER/FDR procedures. Clarified they are distinct tools for selection bias and data-snooping corrections. Set `MULTIPLE_TESTING_CORRECTION_METHOD = NOT_YET_PREREGISTERED`.
- **Trial Lineage**: Removed agent-invented mandate for a "sealed cryptographic ledger" implementation; stated requirement as auditable and immutable lineage once sealed, with implementation `NOT_YET_DETERMINED`.
- **Bar-Path Ambiguity**: Removed mandatory rule to "assume stop-loss triggers first". Replaced with requirement that same-bar ambiguity must not be resolved optimistically, with resolution method `NOT_YET_PREREGISTERED` (authoritative finer-resolution evidence or a separately preregistered conservative fail-closed convention).
- **Diagnostics**: Downgraded agent-mandated metrics (Calmar, VaR, CVaR 95/99, Fama-French 5-factor, Q-factor) and market impact models (Almgren-Chriss, square-root law) to `ILLUSTRATIVE_ONLY diagnostics`. Maintained `NO_SINGLE_METRIC_IS_DECISIVE`.
- **Perturbation**: Preserved the ~20% perturbation discussion from source material without freezing an arbitrary ±10% convention.

### I. Data and Provenance Technical Corrections (DATA_AND_PROVENANCE_REQUIREMENTS.md)
- **CME Schedule**: Removed incorrect statement regarding a "15-minute maintenance halt" on CME Globex. Replaced with requirement to verify canonical exchange session schedules during future data contracts.
- **Protocol Semantics**: Removed "CME ITCH" example; replaced with generic "authoritative exchange direct order-book feed".
- **Timestamp Precision**: Removed mandatory nanosecond/microsecond mandates; set to `SUBJECT_TO_MECHANISM_AND_DATA_FEASIBILITY_AUDIT`.
- **CFD Guidance**: Clarified that CFD volume semantics differ materially from centralized exchange volume without asserting unauthorized blanket bans.

### J. Bibliography Lineage Sealing (BIBLIOGRAPHY.md)
- **Audit Defect**: Agent reconstructed full bibliographic citations (journals, volumes, pages) from model memory.
- **Correction**: Stripped reconstructed metadata. Retained source family references, author groups, and known titles supplied by human authority, explicitly marking entries with `METADATA_NOT_REVALIDATED_IN_R0`.

### K. Repository Documentation Link Hygiene
- **Audit Defect**: Markdown links used machine-dependent absolute file schema URLs, violating AGENTS.md portability guidelines.
- **Correction**: Converted all internal documentation links to repository-relative paths (`./filename.md`, `../filename.md`, etc.).

## 4. Invariants Verification

- **Zero Market Data Access**: CONFIRMED.
- **Zero Backtesting**: CONFIRMED.
- **Zero Parameter Sweeps**: CONFIRMED.
- **Zero New Research Claims**: CONFIRMED.
- **CORE-001 / HYP_011 Isolated & Unchanged**: CONFIRMED.
- **Main Branch Untouched**: CONFIRMED.
- **Real Capital Authority**: Strictly `$0.00`.
- **Execution Boundary**: `NO_REAL_ORDERS = true`.
