# ACASH — Developer & Quant Quick Reference Cheatsheet

**Project:** ACASH (Automated Capital Allocation System)  
**Version:** 1.14.0 (Phase 12 Frozen | Phase 13 Step 5 Active | Phase 14 Plan Approved)  
**Test Suite:** Strict Multi-Tier Gate Discipline (Phase-specific regression suites verified at gate checkpoints) | MyPy: Strict mode clean | HEAD: `origin/main`  
**Operating Philosophy:** *"DO NOT ASSUME AN EDGE. PROVE IT."*

$$\boxed{\mathbf{Research\ (14/8.5)} \longrightarrow \mathbf{Allocation\ (8)} \longrightarrow \mathbf{Supervisor\ (10)} \longrightarrow \mathbf{Risk\ (9)} \longrightarrow \mathbf{Execution\ (12/7)} \longrightarrow \mathbf{Ledger\ (10)} \quad \Big\vert \quad \mathbf{Monitoring\ (11)} \quad \Big\vert \quad \mathbf{Soak\ (13)}}$$

---

## 1. North Star & First Principles

1. **The North Star Question:**
   > *"Given the current market state, available opportunities, portfolio state, uncertainty, liquidity, and risk constraints, where should capital be allocated?"*
   - Valid, supported answer: **"NOWHERE"** (100% Cash Allocation).
2. **Deterministic Sovereign Risk Boundary:**
   - The Risk Engine is a non-negotiable hard boundary. If AI/Strategy says `BUY` and Risk Engine says `REJECT` $\implies$ **`REJECT`** (Always, 0 orders admitted).
3. **Five-Way Sovereign Separation of Concerns:**
   $$\boxed{\mathbf{Research\ (8.5)} \neq \mathbf{Forward\ Monitoring\ (11)} \neq \mathbf{Allocation\ (8)} \neq \mathbf{Supervisor\ (10)} \neq \mathbf{Risk\ (9)} \neq \mathbf{Execution\ (7)} \neq \mathbf{Broker}}$$
4. **Historical Qualification $\neq$ Current Forward Health:**
   $$\boxed{\mathbf{AlphaQualificationDossier}_{\text{historical}} \neq \mathbf{ForwardStrategyHealth}_{\text{current}}}$$
5. **No Speculative AI Trading Bots & Zero Direct Broker Wires:**
   - AI is strictly an analytical component, never an execution authority.
   - Zero direct broker sockets in research, portfolio, supervisor, risk, or monitoring layers.

---

## 1.5 Current Governance & Operational State (2026-09-05)

- **Phase 12 (MT5 & Multi-Venue Execution Adapters):** COMPLETED & FROZEN (`1e1d154`).
- **Phase 13 (Live Small Capital / Forward Paper Validation):** ACTIVE & IN PROGRESS.
  - Steps 1–4: **PASSED** (Implementation, Code Audit, Integration, Recovery).
  - Step 5 (24-Hour Unattended Soak): **ACTIVE / IN PROGRESS** (PID `41844`, `pythonw.exe`).
  - Steps 6–9: **STRICTLY LOCKED** pending Step 5 wall-clock completion & evidence audit.
- **Phase 14 (AI Quantitative Research Layer):** PLAN APPROVED AT PLAN LEVEL (`docs/phase14/phase14_master_research_architecture_plan.md`).
  - Implementation: **STRICTLY LOCKED / NOT AUTHORIZED**.
- **Live Capital Authority:** Strictly **$0.00 (Hard-Locked)**.
- **Live Order Emission:** Strictly **0 Orders**.
- **Broker Connection:** Strictly **DISCONNECTED**.
- **Strategy Admission:** Strictly **`QUALIFICATION_BLOCKED`**.

---

## 2. Decoupled Sovereign System Architecture

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
                          (Signals & Hypothesis Specification)
                                       │
                                       ▼
                                4. VALIDATION ENGINE
                             (Purged CPCV & DSR Gate)
                                       │
                                       ▼
                              5. ALPHA QUALIFICATION
                       (Phase 8.5 Dossiers & Economic Lineage)
                                       │
                                       ▼
                               6. PORTFOLIO ENGINE
                      (Phase 8 Tournament vs Baselines: EW/InvVol/Cash)
                                       │
                                       ▼
                              7. RUNTIME SUPERVISOR
                     (Phase 10 5-Stage Orchestrator & Dual-Clock)
                                       │
                                       ▼
                                8. SOVEREIGN RISK
                     (Phase 9 Deterministic Veto & Kill Switch)
                                       │
                                       ▼
                               9. EXECUTION ENGINE
                      (Phase 7 Coordinator & Alpaca Paper)
                                       │
                                       ▼
                    10. APPEND-ONLY OPERATIONAL LEDGER
                      (Phase 10 SHA-256 Chained Disk Events)
                                        │
                                        ▼
                    11. FORWARD MONITORING & REALITY GAP
                     (Phase 11 Strategy Drift & Drag Attribution)
                                        │
                                        ▼
                    12. VENUE EXECUTION ADAPTERS
                     (Phase 12 MT5 BMAP & 6-D Reconciliation)
                                        │
                                        ▼
                    13. FORWARD PAPER VALIDATION
                     (Phase 13 Small Capital & Soak Harness)
                                        │
                                        ▼
                    14. AI RESEARCH & EVIDENCE LAYER
                     (Phase 14 Plan Approved — Impl Locked)
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

---

## 9. Phase 8 & 8.5: Portfolio Tournament & Alpha Qualification

### 9.1 Phase 8.5 Alpha Research & Qualification DTOs
- **`AlphaQualificationDossier`:** Canonical qualification certificate certifying historical econometric edge.
- **Economic Invariant:** $\text{Net Trading Alpha} = \text{Gross PnL} - \text{Spread/Slippage} - \text{Commissions}$. Maker rebates cannot alter Net Alpha.
- **Capital Boundary:** $CapitalAuthorityUSD \equiv 0.00$ for all Phase 8.5 states.

### 9.2 Phase 8 Portfolio Tournament
- **Baseline Allocators:** Equal Weight (1/N), Inverse Volatility (1/$\sigma$), 100% Cash (`CashAllocator`).
- **Tournament Rule:** Zero-leakage out-of-sample evaluation (`AllocationTournamentRunner`).
- **Governance Gate:** If expected net portfolio return fails risk-free rate + hurdle, sovereignly allocate 100% Cash (`GOVERNANCE_FALLBACK`).

---

## 10. Phase 9: Deterministic Sovereign Risk Engine & Kill Switch

### 10.1 Deterministic Risk Engine (`IRiskEngine`)
- **Hard Boundaries:** Gross leverage limit, asset concentration limit, mandatory cash floor (min 5%), daily loss limit, max drawdown.
- **Derisking:** Proven monotonic scaling (`EXACT_SCALE_DOWN`) and `BINARY_REJECT`.
- **Sovereign Veto:** $\text{Risk REJECTED} \implies 0\text{ Orders Transmitted}$.

### 10.2 Sovereign Kill Switch Controller
- **Append-Only Disk Persistence:** `kill_switch_state.jsonl` with SHA-256 event chaining.
- **Fail-Closed Restart:** Crash/restart in `TRIPPED` state recovers into `PERSISTENTLY_BLOCKED`.
- **Quorum Reset:** Requires $M$-of-$N$ signed `Ed25519` authorizations from `Ed25519TrustStore`.
- **Emergency Flatten:** Emits zero-target intents ($\Delta q_i = -q_i$); completion confirmed strictly via Phase 7 broker reconciliation.

---

## 11. Phase 10: Runtime Orchestration & Continuous Paper Operations

### 11.1 5-Stage Authoritative Pipeline (`RuntimeSupervisor`)
$$\text{Stage 1: Data Check} \longrightarrow \text{Stage 2: Strategy Census} \longrightarrow \text{Stage 3: Tournament} \longrightarrow \text{Stage 4: Risk Gate} \longrightarrow \text{Stage 5: Admission}$$
- **Zero God Object:** Orchestrates without computing alphas, allocations, or risk rules.
- **Health State Machine:** `RUNTIME_HEALTHY`, `RUNTIME_DEGRADED`, `RUNTIME_PAUSED`, `RUNTIME_HALTED`.
- **Health vs Risk Separation:** $\boxed{\mathbf{RuntimeHealthStatus} \neq \mathbf{KillSwitchState}}$.

### 11.2 Dual-Clock & Event Ledger Discipline
- **Dual-Clock:** $\boxed{\mathbf{as\_of\_utc} \neq \mathbf{wall\_clock\_utc}}$ (Decision time vs System NTP time).
- **Append-Only Ledger (`OperationalLedger`):** $\text{Event}[n].\text{prev} \equiv \text{Event}[n-1].\text{curr}$, fail-closed on disk tampering.
- **Paper Daemon:** `ContinuousPaperDaemon` has **0 broker wire authority** ($0 live capital authorization).

---

## 12. Phase 11: Forward Monitoring, Strategy Drift & Execution Reality Attribution [COMPLETED & FROZEN]

### 12.1 Track A: Strategy Forward Drift & Decay Monitor
- **Forward Health State:** `INSUFFICIENT_EVIDENCE` $\to$ `HEALTHY` $\longleftrightarrow$ `DEGRADED` $\to$ `STRUCTURAL_BREAK` (Absorbing).
- **Core Invariant:** $\boxed{\mathbf{Historical\ Qualification\ (8.5)} \neq \mathbf{Current\ Forward\ Health\ (11)}}$.
- **Metrics Tracked:** Rolling Sharpe, Rolling Vol, Drawdown (Multiplicative Compounding), Hit Rate, $t$-stat Decay.
- **Fail-Closed Mathematics:** Discrete Simple Period Returns ($R > -1.0$); zero sample variance strictly raises `DataContractError`.
- **Anti-Whipsaw Hysteresis:** Degradation Persistence ($N=3$), Recovery Persistence ($M=10$), Recovery Cooldown ($T=5$).
- **Decoupled Telemetry:** `MONITORING_BLOCKED` freezes counters and does NOT penalize strategy performance (`No Evidence != Negative Evidence`).
- **Output:** Emits `StrategyForwardDriftEvidence` (Tier 1 SHA-256 Digest) as advisory recommendation for Stage 2 Census.

### 12.2 Track B: Execution Reality Attribution Engine
- **Drag Decomposition (in bps):** 7 exact components: $\text{Net Realized Cost} = \text{Spread} + \text{Timing} + \text{Slippage} + \text{Commission} - \text{Rebate}$.
- **Taker-Only Scope Guard:** Phase 11 v1 is strictly scoped to aggressive/taker execution (arrival quote benchmark). Passive/maker fills are strictly rejected fail-closed.
- **Coverage Denominator Guard:** Requires authoritative execution manifest census; coverage $< 0.80$ strictly fails closed with `DataContractError`.
- **Phase 8 Seam Invariant:** $\boxed{\mathbf{ExecutionCostEvidence} \nRightarrow \text{Direct Phase 8 Overwrite}}$ (frozen DTOs).
- **Output:** Emits empirical friction distributions (`ExecutionCostEvidence`) with robust median, mean, p95, and confidence intervals.

### 12.3 Track C: Stream Ingestion & Forensic Ledger Persistence
- **Decoupled Planes:** Stream Integrity Plane (`VALID` $\leftrightarrow$ `BLOCKED`) vs Strategy Health Plane.
- **Fail-Closed Gap Defense:** Any sequence gap or temporal non-monotonicity transitions stream to `BLOCKED`.
- **Explicit Epoch Recovery (`reinitialize_stream`):** Advances `epoch_index += 1`, restarts sequence at 0; strictly forbids backfilling or synthesizing gap observations.
- **Forensic Ledger Adapter:** `MonitoringEvidenceLedger` wraps Phase 10 `OperationalLedger`, preserving Tier 1 evidence digests within Tier 2 chained `OperationalCycleEvent`s.

### 12.4 Red-Team & Authority Verification
- **26/26 Attack Vectors Verified:** Full adversarial test coverage (`tests/unit/monitoring/test_phase11_red_team_adversarial.py`).
- **Authority Invariants:** Phase 11 $\neq$ Phase 10 Census $\neq$ Phase 8 Friction $\neq$ Phase 8.5 Dossier. Zero live trading or broker connectivity.

---

## 13. Phase 12: MT5 & Multi-Venue Execution Adapters [COMPLETED & FROZEN]
- **Thin Broker Connectivity:** `NativeMT5Transport` Windows Local IPC driver with strict Decimal volume quantization and tick-grid price alignment.
- **Authoritative 6-D Reconciliation:** `MT5BrokerAdapter` enforces fail-closed order lifecycle, UNKNOWN reconciliation, and recovery idempotency.
- **Two-Phase Preflight Routing:** Exclusive `intent_id` routing key with duplicate prevention. Commit: `1e1d154`.

---

## 14. Phase 13: Live Small Capital Deployment [ACTIVE — STEP 5 SOAK IN PROGRESS]
- **Execution Envelope:** Micro-capital live execution validation with micro-lots under strict $0.00 capital authority.
- **Current Step Progress:**
  - Steps 1–4: **PASSED** (Implementation, Code Audit, Integration, Recovery).
  - Step 5: **ACTIVE / IN PROGRESS** (24-hour unattended soak runner under PID `41844`, Local Simulator).
  - Steps 6–9: **STRICTLY LOCKED** pending Step 5 wall-clock completion and evidence audit.
- **Strict Invariant:** Zero live capital authority ($0.00), zero live orders, broker disconnected, strategy blocked.

---

## 15. Phase 14: AI Quantitative Research & Evidence Layer [PLAN APPROVED — IMPL LOCKED]
- **Governing Specification:** [`docs/phase14/phase14_master_research_architecture_plan.md`](docs/phase14/phase14_master_research_architecture_plan.md) (Revision 1.2 — Approved at Plan Level).
- **Core Invariant:** $\boxed{\text{AI Output} \equiv \text{Unvalidated Proposal}}$ (Never trading authority, never alpha qualification).
- **Sequential Pipeline:** AI Proposal $\to$ Phase 4 Pre-Registration $\to$ Phase 5 Backtest $\to$ Phase 6 ValidationGate $\to$ Phase 8.5 Alpha Dossier.
- **Type-Level Evidence Firewall:** $\boxed{\text{ExternalBackendResult} \not\equiv \text{ValidationReport}}$ (VectorBT/HFTBacktest results cannot masquerade as canonical validation).
- **Causal AST Validation:** Causal inspection of all proposed feature expressions; 100% rejection of lookahead/lead operators.
- **Status:** **Implementation is strictly locked / not authorized** until Phase 13 Steps 5–9 are certified.

---

## 16. Canonical Developer Commands

```powershell
# 1. Run Targeted Phase Test Suites (uv runner)
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v

# 2. Run Static Type Checker (MyPy - strict mode)
uv run mypy src/ tests/

# 3. Check Phase 13 Step 5 Soak Status
powershell.exe -ExecutionPolicy Bypass -File .\scripts\status_phase13_soak.ps1

# 4. Check Git Status & Lineage
git status --short
git branch -vv
git log -3 --oneline --decorate
```
