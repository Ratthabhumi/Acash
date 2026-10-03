# Runtime Repair Proposal: F01, F02, and F09

**Status**: PROPOSAL ONLY — STRICTLY UNIMPLEMENTED  
**Date Context**: 2026-09-30  
**Target Files**: `src/acash/research/hyp_011/shadow_ops.py`, `src/acash/research/hyp_011/shadow.py`  
**Execution Condition**: After Observation #1 Attempt #2 execution (post-03:20 ICT / 20:20Z) and before Observation #2 activation.

---

## 1. Governance Boundary & Operational Invariant

> [!CRITICAL]
> **DO NOT APPLY THIS PATCH BEFORE ATTEMPT #2 COMPLETES.**  
> Attempt #2 is an armed, frozen experiment pinned to canonical commit `becec27f5eacf283dcb191cf72d0858682d8e055`. Mutating runtime code in `src/**` prior to Attempt #2 invalidates pre-registered operational lineage.  
> Furthermore, the homelab wrapper `/usr/local/sbin/acash-hyp011-observation-0001-attempt-0002` already contains preflight mitigations enforcing that both `state.json` and `observations/2026-09-30.json` are strictly absent prior to dispatch.

---

## 2. Proposed Defect Repairs

### Repair 1 (F01): State Economic Reconciled with Terminal Observation
- **Target File**: `src/acash/research/hyp_011/shadow_ops.py`
- **Defect Description**: Lines 601–602 deserialize `ShadowPortfolio.from_dict` and `ShadowBenchmark.from_dict` to check schema validity, but never cross-verify that the accumulated economic balances in `state.json` match the terminal observation artifact.
- **Proposed Code Change**:
```python
    if observed:
        for field in (
            "strategy", "benchmark", "last_closes_raw", "last_closes_split",
            "completed_annual_rebalances",
        ):
            if field not in state_doc:
                raise DataContractError(f"BLOCK_SHADOW_STATE_INTEGRITY: missing {field}.")
        
        # Deserialization check
        portfolio_state = ShadowPortfolio.from_dict(state_doc["strategy"])
        benchmark_state = ShadowBenchmark.from_dict(state_doc["benchmark"])

        # [REPAIR F01]: Cross-document economic reconciliation with terminal observation
        last_obs_path = obs_dir / f"{observed[-1]}.json"
        last_obs_doc = json.loads(last_obs_path.read_text(encoding="utf-8"))
        
        last_strat = last_obs_doc.get("strategy", {})
        last_bench = last_obs_doc.get("benchmark", {})
        
        # Reconcile strategy balances
        if Decimal(str(portfolio_state.cash)) != Decimal(str(last_strat.get("cash", "NaN"))):
            raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: state cash diverges from terminal observation.")
        if Decimal(str(portfolio_state.prev_equity)) != Decimal(str(last_strat.get("equity", "NaN"))):
            raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: state equity diverges from terminal observation.")
        if portfolio_state.holdings != last_strat.get("holdings"):
            raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: state holdings diverge from terminal observation.")
            
        # Reconcile benchmark balances
        if Decimal(str(benchmark_state.cash)) != Decimal(str(last_bench.get("cash", "NaN"))):
            raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: benchmark cash diverges from terminal observation.")
        if Decimal(str(benchmark_state.prev_equity)) != Decimal(str(last_bench.get("equity", "NaN"))):
            raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: benchmark equity diverges from terminal observation.")
        if benchmark_state.shares != last_bench.get("shares"):
            raise DataContractError("BLOCK_SHADOW_STATE_INTEGRITY: benchmark shares diverge from terminal observation.")
```

---

### Repair 2 (F02): Orphan Inspection Precedes Initial State Generation
- **Target File**: `src/acash/research/hyp_011/shadow_ops.py`
- **Defect Description**: If `state.json` is missing, `verify_chain()` returns `build_initial_state(...)` at line 496 before reaching the orphan inspection logic at line 604. If orphaned observation files exist on disk, they are silently ignored instead of triggering a fail-closed integrity block.
- **Proposed Code Change**:
```python
def verify_chain(
    state_dir: Path,
    expected_activation: Optional[date] = None,
    expected_recovery_authority: Optional[StageCRecoveryAuthority] = None,
) -> Dict[str, Any]:
    state_path = state_dir / "state.json"
    obs_dir = state_dir / "observations"
    
    # [REPAIR F02]: Orphan check on disk before returning initial state
    on_disk_all = sorted(
        p.stem for p in obs_dir.glob("*.json") if p.is_file()
    ) if obs_dir.exists() else []

    if not state_path.exists():
        if on_disk_all:
            raise DataContractError(
                f"BLOCK_SHADOW_STATE_INTEGRITY: orphan observation files {on_disk_all} exist without state.json."
            )
        return build_initial_state(expected_activation)
```

---

### Repair 3 (F09): Strict Validation of `locks` in Stage C-B Loader
- **Target File**: `src/acash/research/hyp_011/shadow.py`
- **Defect Description**: `load_stage_c_recovery_authority()` verifies 11 top-level keys but fails to validate the `locks` sub-dictionary. A corrupt manifest permitting paper trading or capital authorization would be accepted.
- **Proposed Code Change**:
```python
    locks = data.get("locks")
    if not isinstance(locks, dict):
        raise DataContractError("SHADOW_RECOVERY_BINDING_LOCKS_MISSING: locks dictionary required.")
    
    if locks.get("paper_trading") is not False:
        raise DataContractError("SHADOW_RECOVERY_BINDING_LOCKS_INVALID: paper_trading must be false.")
    if locks.get("live_trading") is not False:
        raise DataContractError("SHADOW_RECOVERY_BINDING_LOCKS_INVALID: live_trading must be false.")
    if str(locks.get("real_capital_authority_usd")) != "0.00":
        raise DataContractError("SHADOW_RECOVERY_BINDING_LOCKS_INVALID: real_capital_authority_usd must be 0.00.")
    if locks.get("no_real_orders") is not True:
        raise DataContractError("SHADOW_RECOVERY_BINDING_LOCKS_INVALID: no_real_orders must be true.")
```

---

## 3. Verification Plan Post-Implementation

1. Execute offline reproduction tests in `tests/unit/research/test_hyp011_audit_reproductions.py`:
   - `test_reproduce_f01_economic_state_not_reconciled_with_terminal_observation` must transition to expecting `DataContractError("...diverges from terminal observation...")`.
   - `test_reproduce_f02_orphan_detection_bypassed_when_state_json_absent` must transition to expecting `DataContractError("...orphan observation files...")`.
   - `test_reproduce_f09_stage_c_b_loader_ignores_locks` must transition to expecting `DataContractError("SHADOW_RECOVERY_BINDING_LOCKS_INVALID")`.
2. Run full HYP_011 test suite: `uv run pytest tests/unit/research/test_phase14_hyp_011_*.py`.
3. Note: `PASSING_REPRODUCTION_TEST != DEFECT_REPAIRED`. Until runtime repairs are implemented in `src/**` after Attempt #2, contract enforcement remains:
   `CONTRACT_ENFORCEMENT = PARTIAL_FAIL_CLOSED_WITH_KNOWN_INTEGRITY_GAPS_F01_F02_F09`
   `RUNTIME_REPAIR_STATUS = PROPOSED_NOT_IMPLEMENTED`
