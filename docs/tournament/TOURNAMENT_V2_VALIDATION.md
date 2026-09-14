# ACASH Shadow Tournament — V2 10-Slot Validation

> [!CAUTION]
> **This document is TEST EVIDENCE RECORD ONLY — it is not a qualification
> certificate, not run authorization, and not research admission.**

> **Branch context:** `feat/tournament-v2-risk-remediation-10slot`
> (base `main` `9a58ced5011e15c7bcf3975f0e83acf339fa53ce`).
> **Status:** local suite verified at the design commit set below.

---

## 1. Test Inventory (unit + integration, paper/tournament scope)

| Test file | Coverage | Status |
|---|---|---|
| `tests/unit/paper/test_risk_remediation_v2.py` | Defects A & E — `MAX_NOTIONAL` gate, `TerminalReason` preservation | 9 passed |
| `tests/unit/paper/test_tournament.py` | N-slot fanout `A..Z` (1..26), slot validation, 10-slot layout, auto-mount, catalog, **10-slot state isolation** (distinct journals / hashes / portfolios, no cross-slot sharing) | 17 passed |
| `tests/unit/paper/test_v2_policy_seams.py` | Funding policies, negative-debt contract error, kill-switch preserve / flatten / operator-policy, payload fields, `RISK_HALTED`/`FEED_HALTED`/`STOPPED` aggregate states, one-hot metrics | 14 passed |
| `tests/integration/test_shadow_tournament_runtime.py` | HTTP API endpoints exercised under `num_slots=3`, `auto_mount_infra_candidates=False` namespaces | 4 passed |
| **Total (paper scope)** | | **229 passed** |

Mypy (strict, `src/acash/paper/`): **Success — no issues in 24 source files**.

Dashboard contract (TypeScript): `npm run typecheck` clean; shadow contract
node tests 25/25 (`dashboard/test/shadow_contract.test.mjs`).

## 2. What the Tests Prove

1. **D1 fix:** `MAX_NOTIONAL` gate rejects simulated orders whose notional
   would exceed the configured limit; rejection reason and trigger type are
   journaled (fail-closed, no soft cap).
2. **D5 fix:** terminal reason is propagated and preserved through the
   supervisor halt path (no silent `NORMAL_SHUTDOWN` rewrite of a causal halt).
3. **D2 contract:** `EXPLICIT_BOUNDED_LEVERAGE` rejects non-negative-required
   debt limits with `DataContractError`; `CASH_CONSTRAINED_SPOT` rejects
   negative-cash fills. No `max(1e-12, …)` floors anywhere.
4. **D3 contract:** `HALT_AND_FORCE_SIMULATED_FLATTEN` flattens at mark and
   fails closed on a missing mark; `HALT_AND_REQUIRE_OPERATOR_RESOLUTION`
   surfaces `operatorResolutionRequired` in slot + API JSON.
5. **D4 fix:** slot status transitions `RUNNING → RISK_HALTED` on kill-switch
   trigger and `→ FEED_HALTED` on feed failure; aggregate state precedence
   verified; one-hot metric gauges carry the true state.
6. **V2 fanout:** `slot_ids_for_count` is deterministic, tie-symmetric, and
   contract-bounded (`DataContractError` outside `[1, 26]`); 10-slot layout
   mounts only Slot A by default with the rest `UNASSIGNED`; the infrastructure
   catalog holds 10 distinct INFRA_TEST candidates; auto-mount is opt-in only.
7. **V2 isolation:** in a fully auto-mounted 10-slot layout, all 10 slots own
   distinct journal files, distinct session IDs, distinct config hashes, and
   distinct (non-shared) portfolio objects; one bar is delivered to every slot;
   manifests are sealed per slot with distinct config hashes after halt.

## 3. Evidence Trail (commits)

| Commit | Change |
|---|---|
| `260d32b` | fix(paper): enforce `MAX_NOTIONAL` + preserve terminal reason (D1, D5) |
| `c4651ac` | feat(paper): funding + kill-switch position policies and granular execution states (D2, D3, D4) |
| `24d5607` | feat(paper): parameterize slot fanout for N-slot tournament (A..Z, 1..26) |
| `b169d27` | feat(paper): 10-slot infrastructure candidate catalog with explicit auto-mount opt-in |
| `139ac62` | feat(dashboard): align V2 10-slot contract, granular execution states, `SHADOW_RUNTIME` data source |
| `56160de` | test(paper): prove 10-slot layout state isolation |

## 4. Explicit Non-Claims (what this does NOT prove)

- No strategy alpha, no statistical qualification, no backtesting result.
- No run of 24h continuity has been performed on this branch (H01 Attempt 1
  remains the last run; it did NOT achieve 24h).
- No production deployment, no live feed soak, no operator-recovery drill
  on the V2 layout. D4/D5 observability is verified at the Python/unit level;
  container-level behavior remains operator-verified at deployment.
- Paper/Live remain NOT AUTHORIZED; canonical capital stays $0.00.

---

### Verification Ledger
- Implementation Status: COMPLETE (design commit set)
- Contract Enforcement: STRICT FAIL-CLOSED
- Mathematical Authority: N/A (config/observability changes; accounting contract tests)
- Local Test Suite: VERIFIED (229 passed — paper unit + integration)
- Type Checker (MyPy): VERIFIED (24 source files clean, `src/acash/paper/`)
- Remote CI Status: NOT AVAILABLE
- Methodological Caveats:
  - Dashboard evidence (`npm run typecheck`, node contract tests) is a separate
    toolchain; counts reported from local run
  - Full-repository `uv run pytest` beyond the paper scope was not the gate for
    this branch; paper/tournament scope is the audit boundary