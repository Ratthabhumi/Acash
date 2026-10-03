# HYP_011 Observation #2 Readiness & Hard Gate Checklist

**Applicable Window**: Post-Observation #1 Verification and Prior to Observation #2 Dispatch (Target Session: 2026-10-01)  
**Classification**: Mandatory Research & Operational Stop Gate  
**Reference Findings**: F01, F02, F09, F10

---

## 1. Hard Gate Invariant

> [!WARNING]
> Observation #1 achieving `COMMITTED_AND_RECONCILED` ($S_1 = 1/20$) is a **necessary but insufficient** condition for continuing to Observation #2.  
> Automatic scheduling or unverified progression to Observation #2 is strictly prohibited. Continuation requires:
> 1. Formal closure of runtime integrity gaps F01, F02, and F09.
> 2. Operational resolution of Corporate Actions (CA) acquisition pipeline (F10).
> 3. Explicit human continuation authority.

---

## 2. Mandatory Pre-Conditions for Observation #2

### Gate 1: Observation #1 Independent Ratification
- [x] Observation #1 classified as `COMMITTED_AND_RECONCILED` per `docs/audit/OBSERVATION_0001_POST_RUN_CHECKLIST.md` (record: `docs/audit/OBSERVATION_0001_COMMITTED_RECONCILED_20260930.md`).
- [x] $S_1$ progress officially recorded at $1/20$.
- [x] Zero manual backfills or retries invoked.

---

### Gate 2: Implementation & Verification of Runtime Repairs (F01, F02, F09)
Apply and verify the patches documented in `docs/audit/F01_F02_F09_RUNTIME_REPAIR_PROPOSAL.md`:
- [x] **F01**: `verify_chain()` cross-reconciles state portfolio cash/equity/holdings with terminal observation artifact (implemented on repair branch; Obs #1 backward-compatible).
- [x] **F02**: `verify_chain()` orphan detection moved prior to state file existence check (implemented; pristine-empty still valid).
- [x] **F09**: `load_stage_c_recovery_authority()` strictly enforces `locks` dictionary (implemented; 12 fields; production manifest loads, bytes preserved).
- [x] `tests/unit/research/test_hyp011_audit_reproductions.py` updated to verify strict fail-closed enforcement (all acceptance tests passing under repaired contracts).
- [ ] Full HYP_011 unit suite passes cleanly.
- [ ] Runtime repair PR merged to canonical `main`.

---

### Gate 3: Corporate Actions (CA) Provenance & Acquisition Operationalized (F10)
Starting at Session #2 ($T \ge 2$), the runner executes `_check_split_continuity()` and dividend accounting across target symbols (`SPY`, `ACWI`, `AGG`):
- [ ] Corporate Action determination ingest workflow operationalized.
- [ ] Dual-source or canonical exchange authority established for splits, dividends, and ticker changes.
- [ ] SHA-256 determination ledger bound to observation dispatch.
- [ ] Verify runner does not fall back to unverified silent assumptions if CA feed is unavailable.

---

### Gate 4: Homelab Environment Preparation & Synchronization
- [ ] Homelab host pulls canonical merge commit containing runtime repairs.
- [ ] Preflight verification confirms observation #1 and state files are untouched and pass repaired `verify_chain()`.
- [ ] Observation #2 dispatch service configured for 2026-10-01 at `20:20:00Z` (`16:20:00 ET`).
- [ ] Capital locks re-verified: `capital_authority_usd == "0.00"`, `no_real_orders == true`.

---

### Gate 5: Explicit Human Continuation Authority
- [ ] Lead quantitative researcher reviews Observation #1 evidence pack.
- [ ] Lead quantitative researcher signs off on F10 corporate action pipeline readiness.
- [ ] Explicit ratification command / authorization recorded in governance ledger.

---

## 3. Observation #2 Readiness Signoff Ledger

```markdown
### Observation #2 Readiness Verification Ledger
- Gate 1 (Observation #1 Ratification): [PASS / BLOCKED]
- Gate 2 (F01/F02/F09 Runtime Repair): [MERGED & VERIFIED / PENDING]
- Gate 3 (F10 Corporate Actions Pipeline): [OPERATIONAL / BLOCKED]
- Gate 4 (Homelab Synchronization): [SYNCED / PENDING]
- Gate 5 (Human Continuation Authority): [GRANTED / WITHHELD]
- Overall Status: [AUTHORIZED_FOR_DISPATCH / BLOCKED]
- Approving Authority: 
- Approval Timestamp UTC: 
```
