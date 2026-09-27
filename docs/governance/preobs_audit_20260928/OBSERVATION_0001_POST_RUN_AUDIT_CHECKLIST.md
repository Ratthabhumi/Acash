# ACASH CORE-001 / HYP_011 Observation #0001 Post-Run Audit Checklist

**Document:** `docs/governance/preobs_audit_20260928/OBSERVATION_0001_POST_RUN_AUDIT_CHECKLIST.md`
**Evaluation Scope:** Read-Only Audit Specification for Prospective Shadow Observation #0001
**Target Core:** `CORE-001`
**Target Hypothesis:** `HYP_011`
**Working Title:** `Global 80/20 Strategic Allocation Core`
**Strategy Family:** `STATIC_GLOBAL_EQUITY_BOND_STRATEGIC_ASSET_ALLOCATION`
**Frozen Portfolio Target Weights:**
- `ACWI` = 80.0% (iShares MSCI ACWI ETF — Global Equity)
- `AGG` = 20.0% (iShares Core U.S. Aggregate Bond ETF — US Investment Grade Bonds)
- Residual simulated cash from whole-share sizing only (no fractional shares, zero margin, zero leverage)
**Benchmark Configuration:**
- Primary Benchmark: `SPY` (SPDR S&P 500 ETF Trust) — **BENCHMARK ONLY**, evaluated on an independent accounting path, **NOT** a portfolio holding.
**Explicitly Excluded Assets:** `QQQ`, `GLD`, `VNQ`, `TLT`, `HYG` (not part of HYP_011 universe).
**Scheduled Execution Session:** `2026-09-28` (NYSE Regular Trading Day)
**Eligibility Boundary:** Strictly after `20:00:00 UTC` on `2026-09-28`
**Canonical Main SHA Pin:** `d9608c0a2353bd5ed41943e5fb893ef9648089d2`
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda)

---

> [!CAUTION]
> **MANDATORY EXECUTION DIRECTIVE:**
> **DO NOT RUN THIS AUDIT BEFORE THE OBSERVATION SERVICE HAS COMPLETED.**
> This checklist is an audit protocol, not an execution launcher. It must be executed strictly **after** the automated systemd timer fires, the service completes, and all output artifacts are sealed on disk. Zero manual service invocation, zero retry, zero backfill.

---

## 1. Canonical Homelab Infrastructure Identifiers

Verification must assert identity against canonical systemd unit and filesystem paths:
- **Timer Unit:** `acash-hyp011-observation-0001.timer`
- **Service Unit:** `acash-hyp011-observation-0001.service`
- **Wrapper Executable:** `/usr/local/sbin/acash-hyp011-observation-0001`
- **Execution Log:** `/var/log/acash/hyp011-observation-0001.log`
- **Environment Configuration:** `/etc/acash/hyp011.env` (never reveal secrets)

---

## 2. Audit Execution Protocol & Evidence Verification Ledger

When executing the post-run audit, the auditing operator or agent must verify each item against raw disk artifacts and system logs, recording either `VERIFIED`, `FAIL`, or `BLOCKED`.

---

### Section A: Timer & Service Execution Evidence
- [ ] **A.1 Automated Timer Trigger:** Verify via system journal (`journalctl -u acash-hyp011-observation-0001.timer`) that the service was dispatched automatically by the monotonic/calendar timer.
- [ ] **A.2 Zero Manual Invocations:** Confirm from execution audit logs that the command line was not manually triggered by an operator prior to timer dispatch.
- [ ] **A.3 Normal Service Completion:** Confirm systemd service (`systemctl status acash-hyp011-observation-0001.service`) exited cleanly with `Status=0/SUCCESS` and no unhandled exceptions.
- [ ] **A.4 Zero Retries / Zero Loops:** Verify that the service ran exactly once. Restart count must be `RestartCount=0`.

---

### Section B: Repository & Runtime Identity Verification
- [ ] **B.1 Deployed Commit SHA:** Verify `git rev-parse HEAD` on the execution host matches canonical pin:
  ```text
  EXPECTED_SHA = d9608c0a2353bd5ed41943e5fb893ef9648089d2
  ```
- [ ] **B.2 Clean Working Tree:** Verify `git status --porcelain` on the execution host has zero uncommitted runtime changes.
- [ ] **B.3 Python Environment:** Verify execution was performed using the pinned `.venv` with Python 3.14+ without uncommitted monkeypatches.

---

### Section C: Session Identity & Timing Boundaries
- [ ] **C.1 Session Date:** Confirm target session is `2026-09-28` (NYSE regular calendar session).
- [ ] **C.2 Eligibility Boundary Enforced:** Confirm execution timestamp $t_{\text{exec}} > \text{close\_utc}$ (`2026-09-28T20:00:00Z`).
- [ ] **C.3 Daily Bar Finality:** Confirm market bars fetched represent final, post-close official closing prices, not mid-day or provisional bars.

---

### Section D: Observation Integrity & Ordinal Sequence
- [ ] **D.1 Ordinal Counter:** Verify `ordinal == 1`.
- [ ] **D.2 Zero Duplicate Records:** Confirm that no prior record exists for `2026-09-28`.
- [ ] **D.3 Zero Backfill:** Confirm that the locked unobserved session `2026-09-25` was **not** backfilled and remains recorded as `MISSED_UNOBSERVED_DUE_TO_AUTHORIZATION_LOCK`.
- [ ] **D.4 Zero Synthetic Fabrication:** Verify that no simulated or synthetic bars were substituted for missing market feeds.

---

### Section E: Data Contract & Six Required Series
The observation data contract requires exactly **six canonical series** (3 symbols $\times$ 2 lineages), not six assets:
- [ ] **E.1 ACWI Split Series:** `ACWI` adjusted for splits.
- [ ] **E.2 ACWI Raw Series:** `ACWI` unadjusted raw close.
- [ ] **E.3 AGG Split Series:** `AGG` adjusted for splits.
- [ ] **E.4 AGG Raw Series:** `AGG` unadjusted raw close.
- [ ] **E.5 SPY Split Series:** `SPY` adjusted for splits (benchmark only).
- [ ] **E.6 SPY Raw Series:** `SPY` unadjusted raw close (benchmark only).
- [ ] **E.7 Raw Artifacts Stored:** Verify raw response payloads are written to the observation directory with valid SHA-256 digests.
- [ ] **E.8 Provider Lineage Bound:** Verify data was acquired via authorized qualified provider endpoints without ad-hoc scrapers.

---

### Section F: Corporate Actions & Distribution Handling
- [ ] **F.1 Distribution Sponsor Authorities:**
  - Portfolio distributions (`ACWI`, `AGG`): Bound to `BLACKROCK_ISHARES_OFFICIAL` (`ishares.com`).
  - Benchmark distributions (`SPY`): Bound to `STATE_STREET_SPDR_OFFICIAL` (`ssga.com`).
- [ ] **F.2 Session #1 Economic Classification:**
  - Confirm corporate action reconciliation records the canonical classification:
    ```json
    {"status": "CA_NOT_ECONOMICALLY_REQUIRED_NO_PRIOR_HOLDINGS"}
    ```
  - *Context:* Because this is the initial inception session with zero pre-existing holdings prior to market close, corporate action economics (ex-dividend entitlement, cash receivables) are not required for prior positions. This does **not** assert that no dividends exist, does not set dividends to zero, and does not waive future sponsor verification.
- [ ] **F.3 Split Precedence:** Verify zero unannounced split adjustments occurred across the 3 symbols on `2026-09-28`.

---

### Section G: Allocation, Accounting & Simulated Capital
- [ ] **G.1 Target Allocation:** Confirm initial target portfolio allocation enforces:
  - `ACWI`: 80.0% of starting AUM
  - `AGG`: 20.0% of starting AUM
  - Whole shares sizing only; remaining funds stored as simulated cash.
- [ ] **G.2 Simulated Capital Only:** Base portfolio starting AUM is normalized to **$100,000.00** simulated accounting capital. Real capital remains strictly **$0.00**.
- [ ] **G.3 Rebalance Accounting Invariant:**
  - Initial allocation is the inception portfolio creation; it does **not** count as a completed scheduled annual rebalance.
  - Expected counters post-observation:
    ```text
    observed_sessions = 1
    completed_scheduled_annual_rebalances = 0
    ```

---

### Section H: State Progression & Cryptographic Sealing
- [ ] **H.1 Atomic Write:** Verify that the session write was atomic (`.tmp` write followed by atomic rename).
- [ ] **H.2 Cryptographic Seal:** Verify observation artifact SHA-256 seal is computed and appended to the prospective state chain.
- [ ] **H.3 State Chain Progression:** Confirm `observed_sessions == 1` and preceding hash pointer links to Genesis state.

---

### Section I: Authority Separation & Execution Safety
- [ ] **I.1 Paper Trading Authority:** Verify `PAPER_AUTHORIZED == false`.
- [ ] **I.2 Live Trading Authority:** Verify `LIVE_AUTHORIZED == false`.
- [ ] **I.3 Real Capital Authority:** Verify `REAL_CAPITAL_AUTHORITY == $0.00`.
- [ ] **I.4 Order Suppression:** Verify `NO_REAL_ORDERS == true`.
- [ ] **I.5 Broker State:** Confirm zero orders, zero fills, and zero connection attempts to any live or paper broker endpoint.

---

### Section J: Fail-Closed Classification & Reporting Standards

The audit verdict must strictly follow fail-closed governance:

1. **`HYP_011_OBSERVATION_0001 = VALID_OBSERVED`:**
   Issued **only** if every single check in Sections A through I is verified with explicit cryptographic and log evidence.
   - Stage S1 Progress: `S1_PROGRESS = 1/20`
   - Rebalance Progress: `completed_scheduled_annual_rebalances = 0/2`
2. **`HYP_011_OBSERVATION_0001 = INVALID_EVIDENCE`:**
   Issued if any file, hash, timing window, or data contract is invalid, truncated, or drifted.
3. **`HYP_011_OBSERVATION_0001 = BLOCKED`:**
   Issued if the service failed to fire, was manually aborted, or encountered unhandled environment errors.

> [!IMPORTANT]
> **STATISTICAL BOUNDARY WARNING:**
> A successful `VALID_OBSERVED` verdict proves **only** that Observation #0001 was executed cleanly and recorded with mathematical fidelity. It does **NOT** prove strategy profitability, alpha, statistical edge, or qualification for paper/live trading. Never extrapolate empirical success from a single observation.

---

## 3. Post-Audit Handoff Template

Upon completing the audit, produce a post-run audit report summarizing:
```text
OBSERVATION_0001_AUDIT_REPORT
=============================
Session Date:              2026-09-28
Execution Time (UTC):      [TIMESTAMP]
Timer Unit:                acash-hyp011-observation-0001.timer (AUTOMATIC_VERIFIED)
Service Unit:              acash-hyp011-observation-0001.service (EXIT_0)
Canonical SHA:             d9608c0a2353bd5ed41943e5fb893ef9648089d2
Deployed SHA:              d9608c0a2353bd5ed41943e5fb893ef9648089d2
Observed Ordinal:          1
Observed Sessions Total:   1
Scheduled Annual Rebal:    0 (Completed: 0/2)
Stage S1 Progress:         1/20
Artifact Digest:           [SHA256]
Data Contract:             6/6 REQUIRED SERIES PRESENT (ACWI split/raw, AGG split/raw, SPY split/raw)
Corporate Actions:         CA_NOT_ECONOMICALLY_REQUIRED_NO_PRIOR_HOLDINGS
Holdings:                  ACWI (~80%), AGG (~20%), Cash residual
Benchmark:                 SPY (Independent tracking, not holding)
Simulated Equity:          $[AMOUNT]
Real Orders Emitted:       0
Real Capital Authority:    $0.00
Integrity Classification:  [VALID_OBSERVED / INVALID_EVIDENCE / BLOCKED]
```
