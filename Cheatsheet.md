# ACASH — Developer & Quant Quick Reference Cheatsheet

**Project:** ACASH (Automated Capital Allocation System)  
**Version:** 1.6.0 (Phases 0–6 Complete & Hardened)  
**Operating Philosophy:** *"DO NOT ASSUME AN EDGE. PROVE IT."*

$$\text{DATA} \to \text{EVIDENCE} \to \text{HYPOTHESIS} \to \text{RESEARCH} \to \text{ALPHA} \to \text{VALIDATION} \to \text{PORTFOLIO} \to \text{RISK} \to \text{EXECUTION} \to \text{OUTCOME} \to \text{FEEDBACK}$$

---

## 1. North Star & First Principles

1. **The North Star Question:**
   > *"Given the current market state, available opportunities, portfolio state, uncertainty, liquidity, and risk constraints, where should capital be allocated?"*
   - Valid, supported answer: **"NOWHERE"** (100% Cash Allocation).
2. **Deterministic Risk Boundary:**
   - The Risk Engine is a non-negotiable hard boundary. If AI/Strategy says `BUY` and Risk Engine says `REJECT` $\implies$ **`REJECT`** (Always).
3. **Statistical Significance $\neq$ Tradeable Alpha:**
   - Statistical significance proves non-randomness under the null hypothesis.
   - Tradeable Alpha requires positive post-friction return, flat parameter curvature, low PBO ($< 0.25$), and un-retuned out-of-sample survival ($\text{SR}_{\text{OOS}} \ge 0.50 \cdot \text{SR}_{\text{IS}}$).
4. **No Speculative AI Trading Bots:**
   - AI is strictly an analytical component, never the final execution authority.

---

## 2. 7-Layer Modular Monolith Architecture

```
                               ACASH SYSTEM CORE
                                      │
                      ┌───────────────┴───────────────┐
                      │                               │
             1. RESEARCH DATA LAYER          2. ANALYTICS & RESEARCH
           (Parquet + DuckDB + yfinance)    (pandas + NumPy + vectorbt + Plotly)
                      │                               │
                      └───────────────┬───────────────┘
                                      │
                                      ▼
                                3. ALPHA ENGINE
                         (Signals & Expected Returns)
                                      │
                                      ▼
                             4. VALIDATION ENGINE
                        (Purged CPCV & DSR/OOS Gate)
                                      │
                                      ▼
                             5. PORTFOLIO ENGINE
                     (skfolio + Baselines: EW/InvVol/Cash)
                                      │
                                      ▼
                               6. RISK ENGINE
                      (Hard Deterministic Boundary)
                                      │
                                      ▼
                             7. EXECUTION ENGINE
                             (IExecutionEngine)
                                /           \
                          MT5 Adapter      NautilusTrader Substrate
                          (Phase 12)       (Phase 5 Gate Passed)
                                │
                                ▼
                   LOCAL TRANSACTIONAL CONTROL PLANE
                      (SQLite Append-Only Ledger)
```

### Technology Decision Matrix
| Technology | Role in ACASH | Status | Architectural Invariant |
| :--- | :--- | :--- | :--- |
| **ACASH Core** | Sovereign Domain Logic | **ADOPT** | Strict Decimal finite arithmetic, immutable state transitions. |
| **Parquet + DuckDB** | Analytical Storage | **ADOPT** | Partitioned immutable parts, DuckDB Point-in-Time qualification SQL. |
| **SQLite** | Operational Control Plane | **ADOPT** | Local ACID transactional state, append-only decision audit ledger. |
| **NautilusTrader** | Simulation Substrate | **ADOPT** | Unmocked event backtest substrate, Level-2 depth sweeps, order lifecycle. |
| **skfolio** | Portfolio Optimization | **ADOPT** | HRP, ERC, CVaR evaluated strictly against Equal Weight & Cash baselines. |
| **vectorbt (OSS)** | Rapid Factor Screening | **ADAPT** | Tier-1 Numba-accelerated fast parameter sweeps and screening. |
| **Plotly** | Visualization | **ADOPT** | Interactive research tear sheets and Reality Gap visualizers. |
| **PostgreSQL** | Enterprise Control Plane| **DEFERRED**| Reconsidered only when multi-user/concurrent network needs arise. |
| **MetaTrader 5** | Execution Gateway | **ADAPT** | Thin Windows IPC broker gateway; zero strategy logic in MQL5. |

---

## 3. Domain Flow & Lifecycle Hierarchy

```
        CAPITAL & PORTFOLIO STATE FLOW                DECISION & EXECUTION FLOW
        ──────────────────────────────                ─────────────────────────
                 AccountState                                   Signal
                      │                                           │
                      ▼                                           ▼
                PortfolioState                             TargetAllocation
                      │                                           │
                      ▼                                           ▼
                  Positions                                RiskAssessment
                      │                                           │
                      ▼                                           ▼
        State Transition (NEW Snapshots)                  OrderIntent / Order
        ├── NEW Position                                          │
        ├── NEW PortfolioState                                    ▼
        └── NEW AccountState                                     Fill
                                                                  │
                                            ──────────────────────┘
                      CROSS-CUTTING AUDIT LINEAGE
                      ───────────────────────────
                             DecisionRecord
                (Append-Only: never overwritten or deleted)
```

---

## 4. Mathematical & Statistical Formulas (Phases 1–6)

### 4.1 Accounting & Balance Sheet Invariants (Phase 1 & 5)
- **Balance Sheet Equity Conservation:**
  $$\text{Equity} = \text{Cash Balance} + \sum_{i} (\text{Unrealized PnL}_i)$$
- **Performance Attribution Equity:**
  $$\text{Equity}_{\text{attr}} = \text{Initial Cash} + \text{Realized PnL} + \text{Unrealized PnL} - \text{Total Fees}$$
- **Double-Entry Conservation Invariant:**
  $$|\text{Equity}_{\text{balance\_sheet}} - \text{Equity}_{\text{attribution}}| \le 10^{-10}$$
- **Contract Multiplier Scaling:**
  $$\text{Realized PnL} = (\text{Exit Price} - \text{Entry Price}) \times \text{Closed Qty} \times \text{Multiplier} - \text{Fees}$$

### 4.2 Bi-Temporal Point-in-Time Qualification (Phase 2 & 3)
- **Dual-Temporal Query Constraint:**
  $$T_{\text{event}} \le T_{\text{decision}} \quad \land \quad T_{\text{knowledge}} \le T_{\text{as\_of}}$$
- **DuckDB PIT Qualification Query:**
  ```sql
  QUALIFY ROW_NUMBER() OVER (
      PARTITION BY source_id, symbol, timeframe, event_start_utc
      ORDER BY knowledge_time_utc DESC, revision_seq DESC
  ) = 1
  ```

### 4.3 Market Microstructure & Features (Phase 3)
- **Session VWAP & Dispersion:**
  $$\text{VWAP}_t = \frac{\sum_{i=1}^t P_i \cdot V_i}{\sum_{i=1}^t V_i}, \quad \sigma_t = \sqrt{\frac{\sum_{i=1}^t V_i (P_i - \text{VWAP}_t)^2}{\sum_{i=1}^t V_i}}$$
- **Order Book Imbalance (OBI) & Micro-Price:**
  $$\text{OBI}_t = \frac{V_t^b - V_t^a}{V_t^b + V_t^a}, \quad P_t^{\text{micro}} = \frac{V_t^b \cdot P_t^a + V_t^a \cdot P_t^b}{V_t^b + V_t^a}$$

### 4.4 Alpha Econometric Inference & HAC (Phase 4)
- **Discrete Forward Return:**
  $$R(t, H) = \frac{P_{\text{close}, t+H} - P_{\text{open}, t+1}}{P_{\text{open}, t+1}}$$
- **OLS Slope & Regression Score Process:**
  $$\hat{\beta}_H = \frac{\sum (X_t - \bar{X})(Y_t - \bar{Y})}{\sum (X_t - \bar{X})^2}, \quad g_t = (X_t - \bar{X})\hat{\epsilon}_t$$
- **Andrews (1991) AR(1) Bartlett Kernel Plug-in:**
  $$S_T = \left\lfloor 1.1447 \cdot (\hat{\alpha}(1) \cdot T)^{1/3} \right\rfloor \quad \text{where} \quad \hat{\alpha}(1) = \frac{4\hat{\rho}^2}{(1 - \hat{\rho}^2)^2}$$

### 4.5 Reality Gap Decomposition (Phase 5)
$$\text{Reality Gap} = \text{Analytical Edge} - \text{Simulated Realized Return}$$
$$\text{Reality Gap} = \Delta_{\text{spread}} + \Delta_{\text{slippage}} + \Delta_{\text{latency}} + \Delta_{\text{fee}} + \Delta_{\text{maker\_adverse\_selection}} + \text{Unmodelled Residual}$$

### 4.6 Statistical Validation & Overfitting Controls (Phase 6)
- **Combinatorial Purged Cross-Validation (CPCV):**
  - $N$ groups, $k$ test groups $\implies C = \binom{N}{k}$ combinations.
  - Generates $\phi = \frac{k}{N}\binom{N}{k}$ continuous, non-overlapping pseudo-OOS backtest paths.
  - Purging: Training $t$ purged if $(t+1 < g_{\text{end}}) \land (t+H \ge g_{\text{start}})$.
  - Embargoing: Training $t$ embargoed if $g_{\text{end}} \le t < g_{\text{end}} + \text{embargo\_bars}$.
- **Deflated Sharpe Ratio (DSR):**
  $$DSR = \Phi \left( \frac{(\widehat{SR} - SR_0)\sqrt{T-1}}{\sqrt{1 - g_1 \widehat{SR} + \frac{g_2 - 1}{4}\widehat{SR}^2}} \right)$$
  - Expected maximum null Sharpe ($SR_0$) for $K$ trials with Euler-Mascheroni constant $\gamma_E \approx 0.5772$:
    $$SR_0 = \sqrt{V} \left( (1 - \gamma_E) Z^{-1}\left(1 - \frac{1}{K}\right) + \gamma_E Z^{-1}\left(1 - \frac{1}{K \cdot e}\right) \right)$$
  - Minimum Track Record Length (MinTRL):
    $$\text{MinTRL} = 1 + \left(1 - g_1 \widehat{SR} + \frac{g_2 - 1}{4}\widehat{SR}^2\right) \left(\frac{Z_\alpha}{\widehat{SR} - SR_0}\right)^2$$
- **Multiple Testing Corrections:**
  - Holm-Bonferroni (FWER): $p_{\text{adj},(i)} = \min(1.0, \max(p_{\text{adj},(i-1)}, (K - i + 1) p_{(i)}))$.
  - Harvey-Liu-Zhu Haircut Sharpe: $\text{Haircut\_SR} = \max\left(0, \widehat{SR} - \frac{\sqrt{2 \ln K}}{\sqrt{T}}\right)$.
- **Probability of Backtest Overfitting (PBO):**
  - Mid-Rank Relative OOS Score: $\omega_k = \frac{\text{MidRank}(x_k)}{M + 1} \implies \lambda = \ln\left(\frac{\omega}{1-\omega}\right) \implies \text{PBO} = \mathbb{P}(\lambda < 0)$.
- **Parameter Sensitivity Curvature:**
  - Evaluated on strict $[\theta_0 \cdot 0.75, \theta_0, \theta_0 \cdot 1.25]$ grid:
    $$\kappa = \left| \frac{SR(1.25\theta_0) - 2SR(\theta_0) + SR(0.75\theta_0)}{(0.25\theta_0)^2} \right|, \quad \text{Degradation} \le 30\%$$

---

## 5. Completed Quality Gates Matrix (Phases 0–6)

| Phase | Subsystem | Key Output | Verification Metric | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0** | Discovery & Architecture | ADR-001 to ADR-019 | 17 technologies evaluated | ✅ **PASSED** |
| **Phase 1** | Foundation & Domain Core | Domain entities, pure state transitions | 27/27 unit tests, mypy clean | ✅ **GATE 1** |
| **Phase 2** | Ingestion & Storage Engine | Arrow schema, Parquet parts, DuckDB PIT | 57/57 unit tests, mypy clean | ✅ **GATE 2** |
| **Phase 3** | Microstructure & Features | Trades, L2/L3 Book, VWAP, OBI, Footprint | 122/122 unit tests, mypy clean | ✅ **GATE 3** |
| **Phase 4** | Alpha Engine & Hypotheses | Pre-registered hypotheses, HAC $\hat{\beta}_H$, Blind OOS | 139/139 unit tests, mypy clean | ✅ **GATE 4** |
| **Phase 5** | Backtesting & Simulation | Nautilus substrate, Reality Gap drag telemetry | 200/200 unit tests, mypy clean | ✅ **GATE 5** |
| **Phase 6** | Statistical Validation Gate | CPCV, DSR, MinTRL, PBO, Search Ledger | 252/252 unit tests, mypy clean | ✅ **GATE 6** |
| **Phase 7** | Execution & Broker Mapping | BMAP E-reviewed (01–10 E, 11 E*, 12 D), paper credential boundary, R0/R1 harness, local vault launcher | 588/588 unit tests, scoped mypy clean (5 pre-existing) | 🟡 **IN PROGRESS — E only, P = 0** |











---

## 6. Quant Research & Engineering Rules of Engagement

1. **Append-Only Immutability:** Historical `DecisionRecord` and `ProvenanceManifest` records are immutable. Never update or mutate past records to attach future execution outcomes.
2. **Search Intensity Invariance:** Every parameter variation, feature candidate, and model exploration MUST be recorded in the `SearchTrialLedger` ($K_{\text{ledger}} \equiv K_{\text{DSR}} \equiv K_{\text{Holm}} \equiv K_{\text{BH}}$).
3. **Fail-Closed Out-of-Sample Gate:** No strategy can be marked `PASS_TRADEABLE_ALPHA` without verified Out-of-Sample execution data ($\text{SR}_{\text{OOS}} \ge 0.50 \cdot \text{SR}_{\text{IS}}$).
4. **Dual Cryptographic Lineage:**
   - `evidence_digest`: Hash of underlying mathematical return series and computed statistics.
   - `decision_digest`: Hash of evidence digest + governance verdict + gating thresholds.
   - `created_timestamp_utc`: Preserved strictly as auxiliary runtime metadata.

---

## 7. Core Engineering Execution Loop

$$\text{INSPECT} \to \text{UNDERSTAND} \to \text{PLAN} \to \text{APPROVE} \to \text{IMPLEMENT} \to \text{TEST} \to \text{SELF-REVIEW} \to \text{DOCUMENT}$$

---

## 8. CURRENT STATUS / NEXT STEP — Phase 7 / R1 Paper Exercise

**Checkpoint as of HEAD `61233ad` (pushed to `origin/main`).** This is the authoritative resume point for the current session.

### 8.1 Branch & Checkpoint Status
- `main` == `origin/main` at `61233ad` (`docs(phase7): add Phase 7 design proposal and evolution specification with navigation links`).
- **Key Phase 7 Commits Trail:**
  - `7e3a154`: Transport & credential abstraction
  - `aa44c91`: Concrete `PaperHttpAlpacaTransport`
  - `f2e42a0`: Concrete `AlpacaPaperAdapter`
  - `483e744`: BMAP-07 fail-closed canceled event mapping
  - `62b790f`: Paper credential boundary enforcement (`ALPACA_PAPER`)
  - `424070c`: R0 read-only paper exercise harness
  - `22b6a28`: R1 order-lifecycle exercise harness (`run_order_exercise_verification`)
  - `f1ac319`: R1 preparation & contract lock
  - `4a92348`: Defect fix: `transport.connect()` before submit in R1 entry point
  - `8e92188`: Defect fix: strict `PaperHttpAlpacaTransport` injection guard
  - `f9c10bc`: Track R1 operational runbook & `.omc` exclusion
  - `794d9e9` / `537643f`: Architecture & historical proposals documentation restructuring
  - `61233ad`: Active Phase 7 high-level proposal & evolution spec (`docs/phase7/phase_7_proposal.md`)
- **Untracked / Protected:** `.omc/` (internal IDE state, never track/stage/commit). `docs/phase7/r1_paper_run_runbook.md` is tracked as **DRAFT / NOT AUTHORIZED** runbook.

### 8.2 Phase 7 Status & Subsystem Readiness
- **Core Architecture & Contracts:** Admission/Authorization Gate, Step 8 Contract, 8B State Machine, 8C Broker Event Normalizer, 8D Mock Broker, 8E Coordinator & Reconciliation, Operational Restriction Engine, Real Broker Contract, and Vendor-Agnostic BMAP Framework: **LOCKED**.
- **Implementation & Local Test Verification:** **588/588 unit tests passing** (100% clean).
- **Broker Semantic Evidence (BMAP):** E-reviewed against official broker API documentation (`BMAP 01–10 = E`, `BMAP 11 = E*`, `BMAP 12 = D`).
- **Concrete Execution Components:** `PaperHttpAlpacaTransport`, `AlpacaPaperAdapter`, Paper Credential Boundary (`ALPACA_PAPER`), R0 Read-Only Harness, R1 Order-Lifecycle Harness, and Local Windows DPAPI Vault Launcher: **Complete & fully tested**.
- **Empirical Execution:** **P = 0.** No real Paper order has reached the wire or produced valid runtime telemetry.
- **Live Readiness:** **Live trading is NOT READY and hard-locked.**

### 8.3 Evidence Model ($\text{Unit Tests} \neq E \neq P$)
- **`Local Unit Tests`:** Automated invariant verification and code regression protection (588 tests).
- **`D` (Design-Conformant):** Specification and data structures match the canonical schema.
- **`E` (Broker Semantic Review):** Broker semantic mapping verified against official vendor API documentation (`01–10 E`, `11 E*`, `12 D`).
- **`E*` (Partially Bounded):** Bounded behavior with known vendor API caveats (e.g. BMAP-11 SSE replay gaps).
- **`P` (Empirically Proven):** Real execution observed against live Paper venue satisfying full cryptographic lineage ($P = 0$).

$$\boxed{\text{588 Unit Tests} \neq E \text{ (Broker Semantic Review)} \neq P \text{ (Empirical Paper Execution)}}$$

### 8.4 The Conjunctive P Evidence Acceptance Rule
$$\boxed{\text{P is valid ONLY when: } \text{TerminalVerified} \land \text{EvidenceLineageComplete} \land \text{ReconciliationVerified} \land \text{NoDispute}}$$

- **`TerminalVerified`:** Order reached an absorbing terminal state (`FILLED` or `CANCELLED`) authorized strictly by `transition_order()`.
- **`EvidenceLineageComplete`:** Full cryptographic lineage exists (`OrderIntent` $\to$ `ExecutionManifest` $\to$ `BrokerRawEvent` $\to$ `ReconciliationReport`).
- **`ReconciliationVerified`:** Broker REST snapshot matches ACASH internal accounting within exact tolerance ($|\Delta_{\text{qty}}| = 0, |\Delta_{\text{price}}| \le 10^{-10}$).
- **`NoDispute`:** Zero unhandled exceptions, zero clock-skew violations ($> 5.0\text{s}$), and zero state machine rejection flags.

> **CRITICAL:** An HTTP `200 OK` response is NOT P. An `accepted` order is NOT P. A `FILLED` state alone is NOT P. Unit/mock tests are NOT P.

### 8.5 Safe Credential Architecture & Handling
- **Environment Isolation:** Credentials belong strictly in the operator's process environment (`ACASH_ALPACA_API_KEY_ID` / `ACASH_ALPACA_API_SECRET` or `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY`), NEVER in `.env.example`, `.env`, source code, or Git commits.
- **Zero Leakage:** **Never** read, print, echo, log, or commit credential values.
- **Venue Pinning:** `paper_credential_provider()` binds strictly to venue `ALPACA_PAPER` (`https://paper-api.alpaca.markets/v2`). Any configuration pointing to live production endpoints is rejected fail-closed.

### 8.6 Phase 7 Milestone Progress & Forensic Findings
- **Historical Milestones:**
  1. R0 Read-Only Harness & R1 Lifecycle Harness (`22b6a28`, `4a92348`, `8e92188`).
  2. Local Windows DPAPI User Vault & Secure Launcher (`scripts/setup_paper_credentials.ps1`, `scripts/run_paper.ps1`).
  3. **R1 Paper Incident Discovery (`3dd9f25`):** Discovered that legacy harness simulated synthetic ACK/FILL lifecycle transitions locally rather than observing real broker responses ($\text{Real Submission} \ne \text{Real Fill} \ne \text{Synthetic Event}$).
  4. **R1-REAL Driver Architecture (`4faa81a`):** Created sovereign `R1RealOrderExerciseDriver` with dual-channel broker observation (SSE Primary + REST Polling Recovery), fail-closed timeout to `UNKNOWN`, strict BMAP-07 cancellation reconciliation, and zero synthetic event injections.
  5. **Provenance Hardening:** Eliminated artificial benchmark price fallbacks, enforced broker terminal timestamps for `closed_at`, classified reconciliation identities (`LOCAL-REC-*`), and verified canonical schema commission defaults (`Decimal("0.0")`).
- **Paper Order Exercise Reality:**
  - Order 001 (`acash-r1-paper-20260831-001`): Submitted to Alpaca Paper, rested in `accepted`, and was verified `CANCELED` via REST ($P = 0$).
  - Order 002 (`acash-r1-paper-20260831-002`): Submitted to Alpaca Paper, resting in `new` with `filled_qty = 0` ($P = 0$).
  - Stream Exception Hardening finding: `_HttpEventStream` requires wrapping `httpx.TimeoutException` to `AlpacaTransportTimeoutError` for seamless fallback to REST polling.

### 8.7 Approved Paper-Run Parameters & Idempotency Rules
| Parameter | Current Specification |
| :--- | :--- |
| **Symbol** | `SPY` |
| **Quantity** | `1` share (Market Order / Day) |
| **Client Order ID** | `acash-r1-paper-20260831-002` (Verified Fresh & Unique on Alpaca REST) |
| **Benchmark Mid Price** | `769.295` (Derived directly from real-time market quote) |
| **Target Venue** | `ALPACA_PAPER` (`https://paper-api.alpaca.markets/v2`) |
| **Driver Authority** | `R1RealOrderExerciseDriver` ([`src/acash/execution/alpaca/real_driver.py`](src/acash/execution/alpaca/real_driver.py)) |

### 8.8 Local Windows Credential Vault & Launcher Workflow
1. **One-Time Interactive Registration (Local Windows User Vault):**
   ```powershell
   .\scripts\setup_paper_credentials.ps1
   ```
   - Interactively prompts for **Paper API Key ID** and **Paper API Secret Key**.
   - Encrypted with **Windows DPAPI** (`CurrentUser` scope) and saved strictly outside the repository at `$env:USERPROFILE\.acash\paper_credentials.dpapi`.
   - Zero secrets stored in Git, `.env`, or plaintext files.

2. **Safe Preflight Verification (Zero Secret Exposure):**
   ```powershell
   .\scripts\run_paper.ps1 -PreflightOnly
   ```
   - Injects credentials into the local child process scope for verification.
   - Enforces venue `ALPACA_PAPER` and endpoint `https://paper-api.alpaca.markets/v2`.
   - Cleans up process environment immediately upon completion.

3. **Running ACASH Commands with Paper Credentials:**
   ```powershell
   .\scripts\run_paper.ps1 uv run pytest tests/unit/execution/test_alpaca_real_driver.py
   ```

### 8.9 Safe Operator Commands
```powershell
# 1. Safe Preflight Check via Launcher
.\scripts\run_paper.ps1 -PreflightOnly

# 2. Run Full Offline Test Suite (598 tests collected)
uv run pytest -q

# 3. Run Targeted Driver & Exercise Test Suite (37 tests)
uv run pytest -q tests/unit/execution/test_alpaca_real_driver.py tests/unit/execution/test_alpaca_order_exercise.py

# 4. Verify Clean Git Status
git status --short
```

### 8.10 Current Phase 7 Invariants
- $\boxed{\text{No synthetic lifecycle event in R1-REAL runtime path}}$
- $\boxed{\text{REST aggregate evidence} \neq \text{SSE per-fill evidence}}$
- $\boxed{\text{Timeout / Ambiguity} \longrightarrow \text{CONNECTION\_LOST} \longrightarrow \text{UNKNOWN} \longrightarrow \text{Reconciliation Required}}$
- $\boxed{\text{Real Paper Submission} \neq \text{Real Broker Fill} \implies P = 0}$
- $\boxed{\text{Live Trading} \equiv \text{HARD-LOCKED}}$
