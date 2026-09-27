# R0 Research Intake Governance Charter

## 1. Document Authority & Intake Status

- **Corpus Title**: ACASH Scientific Research Intake Corpus v1
- **Lifecycle Phase**: R0 (Cataloguing, Structural Intake & Lineage Sealing)
- **Base Authority Status**: `R0_INTAKE_SEALED_NO_EMPIRICAL_AUTHORIZATION`
- **Current Content Status**: `R0_CONTENT_CORRECTED_002_PENDING_HUMAN_AUDIT`
- **Base Commit Pin**: `d9608c0a2353bd5ed41943e5fb893ef9648089d2` (Observation #0001 homelab pin)
- **Lineage Amendments**: Scientific acceptance of the corpus is contingent on the additive authority-fidelity amendments:
  - [R0_CORRECTION_001_AUTHORITY_FIDELITY.md](./R0_CORRECTION_001_AUTHORITY_FIDELITY.md)
  - [R0_CORRECTION_002_FINAL_FIDELITY.md](./R0_CORRECTION_002_FINAL_FIDELITY.md)
- **Active Hypothesis Impact**: NONE. HYP_011 and CORE-001 remain completely isolated, unchanged, and frozen.

## 2. Research Shortlist & Candidate Taxonomy

The human research authority has reviewed 15 intake mechanisms (`RI-01` through `RI-15`) and approved a preliminary research shortlist for future exploratory prioritization:

### Approved Exploratory Shortlist:
1. **Shortlist A — Opening-State Information**: [RI_01_OPENING_STATE_INTRADAY_MOMENTUM.md](./mechanisms/RI_01_OPENING_STATE_INTRADAY_MOMENTUM.md)
2. **Shortlist B — Order Flow Imbalance & Absorption**: [RI_03_ORDER_FLOW_IMBALANCE.md](./mechanisms/RI_03_ORDER_FLOW_IMBALANCE.md) and [RI_04_ABSORPTION_IMPACT_EFFICIENCY.md](./mechanisms/RI_04_ABSORPTION_IMPACT_EFFICIENCY.md)
3. **Shortlist C — Option Positioning & Gamma Regime**: [RI_05_DEALER_GAMMA_GEX_REGIME.md](./mechanisms/RI_05_DEALER_GAMMA_GEX_REGIME.md), [RI_06_OPTION_OPEN_INTEREST_CHANGES.md](./mechanisms/RI_06_OPTION_OPEN_INTEREST_CHANGES.md), and [RI_08_IV_EXPECTED_MOVE_REGIME.md](./mechanisms/RI_08_IV_EXPECTED_MOVE_REGIME.md)

### Non-Shortlisted / Restricted Categories:
- **Baseline / Controls**: [RI_09_TIME_SERIES_MOMENTUM.md](./mechanisms/RI_09_TIME_SERIES_MOMENTUM.md) (`DO_NOT_RECYCLE` into CORE-002 due to high contamination with HYP_009/HYP_010).
- **Negative Control Candidates**: [RI_14_FVG_SMC.md](./mechanisms/RI_14_FVG_SMC.md) (placebo comparator for geometric price patterns).
- **Feature Only**: [RI_15_EMA_CHART_CANDLESTICK_FEATURES.md](./mechanisms/RI_15_EMA_CHART_CANDLESTICK_FEATURES.md) (not authorized as a standalone thesis).
- **Advanced Sleeve / On Hold**: [RI_02](./mechanisms/RI_02_OPENING_RANGE_BREAKOUT.md), [RI_07](./mechanisms/RI_07_INTRADAY_OPTION_FLOW.md), [RI_10](./mechanisms/RI_10_VOLUME_SPIKE_BREAKOUT.md), [RI_11](./mechanisms/RI_11_MEAN_REVERSION_OVERREACTION.md), [RI_12](./mechanisms/RI_12_CALENDAR_WEEKDAY_SEASONALITY.md), [RI_13](./mechanisms/RI_13_RELATIVE_VALUE_PAIRS.md).

## 3. Strict Boundary Prohibitions (Fail-Closed Contract)

Under R0 status, the following boundaries are non-negotiable:
- **NO PROMOTION TO CORE-002**: Zero mechanisms are promoted to candidate or core portfolio status.
- **NO CORE-001 RETUNING / RESCUE**: No data, mechanism, or finding from this intake may be transferred to rescue or alter HYP_011.
- **NO EMPIRICAL BACKTESTS**: No historical backtests, simulations, or trial runs are authorized.
- **NO PARAMETER SWEEPS / SEARCHES**: No grid searches, optimization runs, or parameter tuning are permitted.
- **NO MARKET DATA ACCESS**: No querying of Alpaca, CME, Cboe, or external market data feeds for empirical observations.
- **NO BROKER / ACCOUNT ACCESS**: No broker connections, paper trading, or live execution.
- **CAPITAL AUTHORITY**: Strictly `$0.00`.
- **EXECUTION POLICY**: `NO_REAL_ORDERS = true`.

## 4. Next Permitted Action: Zero-Outcome Data Feasibility Audit

The only permitted future technical step for candidates in Shortlists A, B, and C is a **Zero-Outcome Data Feasibility Audit**, which requires explicit, separate human authorization.

### Definition of "Zero-Outcome":
A zero-outcome audit is strictly limited to data engineering contracts:
- **Permitted**:
  - Inspecting vendor data dictionaries, API schemas, and historical availability.
  - Verifying timestamp granularity and quote/trade semantics.
  - Assessing cost, licensing, entitlement constraints, and survivorship/restatement policies.
  - Evaluating delivery mechanisms (flat files, S3, WebSocket, FIX).
- **Strictly Prohibited**:
  - Computing strategy returns, Sharpe ratios, or trade PnL.
  - Evaluating conditional forward returns or hit rates of candidate signals.
  - Running screening scripts that evaluate signal performance before formal pre-registration.
  - Viewing out-of-sample data distributions to select indicator parameters.
